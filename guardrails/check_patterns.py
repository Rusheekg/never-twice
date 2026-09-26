"""
guardrails/check_patterns.py

Scans Python source files for the three bug patterns learned from past
incidents.  Uses Python's ast module for structural analysis where possible
and falls back to line-level inspection for patterns that are hard to
express purely in the AST.

Usage:
    python guardrails/check_patterns.py [path ...]

    If no paths are given, scans the app/ directory relative to the
    project root (the directory containing this script's parent).

Exit code:
    0 — no issues found
    1 — one or more issues found
"""

import ast
import os
import sys
import textwrap
from typing import List, Tuple

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

Issue = Tuple[str, str, int, str, str]  # (file, function, line, pattern, detail)


def _load(path: str):
    with open(path, encoding="utf-8") as fh:
        source = fh.read()
    tree = ast.parse(source, filename=path)
    return source, tree


def _function_name(node: ast.AST) -> str:
    """Walk up to find the enclosing function name, or '<module>'."""
    return getattr(node, "_enclosing_function", "<module>")


def _annotate_functions(tree: ast.AST) -> None:
    """Attach '_enclosing_function' to every node in the tree."""
    current: List[str] = []

    class Visitor(ast.NodeVisitor):
        def visit_FunctionDef(self, node):
            current.append(node.name)
            for child in ast.walk(node):
                child._enclosing_function = node.name  # type: ignore[attr-defined]
            self.generic_visit(node)
            current.pop()

        visit_AsyncFunctionDef = visit_FunctionDef

    Visitor().visit(tree)


# ---------------------------------------------------------------------------
# Pattern 1 — dict.get() result used without a None check  (PM-001)
#
# Heuristic (AST-based):
#   Find Assign nodes of the form  `x = something.get(...)`.
#   Then check whether the next sibling statement (or any statement before
#   the next `if x is None` / `if x:` / `raise`) directly subscripts or
#   attribute-accesses `x`.
#
# This is intentionally conservative: it only flags the most obvious case
# (subscript on the very next statement) to avoid false positives.
# ---------------------------------------------------------------------------

def check_dict_get_no_none_guard(path: str, tree: ast.AST) -> List[Issue]:
    issues: List[Issue] = []
    _annotate_functions(tree)

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        stmts = node.body
        for i, stmt in enumerate(stmts):
            # Look for:  var = <expr>.get(<args>)
            if not isinstance(stmt, ast.Assign):
                continue
            if len(stmt.targets) != 1:
                continue
            target = stmt.targets[0]
            if not isinstance(target, ast.Name):
                continue
            var_name = target.id

            value = stmt.value
            if not (isinstance(value, ast.Call) and
                    isinstance(value.func, ast.Attribute) and
                    value.func.attr == "get"):
                continue

            # Found `var = something.get(...)`.
            # Now scan subsequent statements for a None-guard before any use.
            guarded = False
            for j in range(i + 1, len(stmts)):
                next_stmt = stmts[j]

                # Acceptable guards:
                #   if var is None: ...
                #   if var is not None: ...
                #   if var: ...
                #   if not var: ...
                if isinstance(next_stmt, ast.If):
                    test = next_stmt.test
                    # `if var is None` or `if var is not None`
                    if isinstance(test, ast.Compare) and len(test.ops) == 1:
                        if (isinstance(test.left, ast.Name) and
                                test.left.id == var_name and
                                isinstance(test.ops[0], (ast.Is, ast.IsNot))):
                            guarded = True
                            break
                    # `if var:` or `if not var:`
                    if isinstance(test, ast.Name) and test.id == var_name:
                        guarded = True
                        break
                    if (isinstance(test, ast.UnaryOp) and
                            isinstance(test.op, ast.Not) and
                            isinstance(test.operand, ast.Name) and
                            test.operand.id == var_name):
                        guarded = True
                        break

                # Raise directly after the get — also a guard
                if isinstance(next_stmt, ast.Raise):
                    guarded = True
                    break

                # Check if the variable is subscripted or attribute-accessed
                # in this statement — that is the dangerous use.
                for sub in ast.walk(next_stmt):
                    if isinstance(sub, ast.Subscript):
                        slv = sub.value
                        if isinstance(slv, ast.Name) and slv.id == var_name:
                            issues.append((
                                path,
                                node.name,
                                stmt.lineno,
                                "PM-001: Missing None-guard after dict.get()",
                                f"'{var_name}' assigned via .get() at line {stmt.lineno}; "
                                f"subscripted at line {next_stmt.lineno} without a None check",
                            ))
                            guarded = True  # stop scanning for this var
                            break
                    if isinstance(sub, ast.Attribute):
                        if isinstance(sub.value, ast.Name) and sub.value.id == var_name:
                            issues.append((
                                path,
                                node.name,
                                stmt.lineno,
                                "PM-001: Missing None-guard after dict.get()",
                                f"'{var_name}' assigned via .get() at line {stmt.lineno}; "
                                f"attribute-accessed at line {next_stmt.lineno} without a None check",
                            ))
                            guarded = True
                            break
                if guarded:
                    break

    return issues


# ---------------------------------------------------------------------------
# Pattern 2 — requests.post/get without timeout  (PM-002)
#
# AST-based: find Call nodes whose func is an Attribute named post/get/put/
# patch/delete on any object, and whose keywords do not include 'timeout'.
# ---------------------------------------------------------------------------

# HTTP method names that are *only* meaningful on a requests-like object,
# not on a plain dict (dicts have .get but not .post/.put/.delete etc.)
HTTP_WRITE_METHODS = {"post", "put", "patch", "delete", "request"}


def check_http_no_timeout(path: str, tree: ast.AST) -> List[Issue]:
    """Flag requests.post/put/patch/delete/request calls without a timeout=.

    We deliberately exclude .get() because Python dicts also have .get(), which
    leads to massive false positives.  The critical write-path methods are the
    ones that block workers under gateway failure.
    """
    issues: List[Issue] = []
    _annotate_functions(tree)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr in HTTP_WRITE_METHODS):
            continue
        # Must look like  http.post / requests.post / session.post  — i.e. the
        # object is a plain Name, not a subscript or chained call.
        if not isinstance(func.value, ast.Name):
            continue
        # Exclude calls whose receiver is a local dict-like variable.
        # Heuristic: known dict-like variable name prefixes.
        receiver = func.value.id
        dict_like_prefixes = ("data", "payload", "params", "kwargs",
                              "gateway_data", "response_data", "result")
        if any(receiver.startswith(p) for p in dict_like_prefixes):
            continue

        keyword_names = {kw.arg for kw in node.keywords}
        if "timeout" not in keyword_names:
            fn_name = getattr(node, "_enclosing_function", "<module>")
            issues.append((
                path,
                fn_name,
                node.lineno,
                "PM-002: Outbound HTTP call without timeout",
                f"{receiver}.{func.attr}() at line {node.lineno} "
                f"has no timeout= parameter",
            ))

    return issues


# ---------------------------------------------------------------------------
# Pattern 3 — naive/aware datetime mismatch  (PM-003)
#
# AST-based: find datetime.strptime() calls that are NOT immediately
# followed by .replace(tzinfo=...) or .astimezone(...).
# Flag them if they appear in the same function as datetime.now(tz).
# ---------------------------------------------------------------------------

def check_naive_aware_mismatch(path: str, tree: ast.AST) -> List[Issue]:
    issues: List[Issue] = []
    _annotate_functions(tree)

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        # Does this function contain datetime.now with a tz argument?
        has_aware_now = False
        for child in ast.walk(node):
            if (isinstance(child, ast.Call) and
                    isinstance(child.func, ast.Attribute) and
                    child.func.attr == "now" and
                    child.args):
                has_aware_now = True
                break

        if not has_aware_now:
            continue

        # Find datetime.strptime() calls NOT chained with .replace/.astimezone
        for child in ast.walk(node):
            if not isinstance(child, ast.Call):
                continue
            func = child.func
            # Match datetime.strptime(...) or just strptime(...)
            is_strptime = (
                (isinstance(func, ast.Attribute) and func.attr == "strptime") or
                (isinstance(func, ast.Name) and func.id == "strptime")
            )
            if not is_strptime:
                continue

            # Check whether this Call is itself the value of an Attribute access
            # like  datetime.strptime(...).replace(...)
            # We do this by checking the parent of child in the tree.
            # ast does not track parents natively, so we use a simple walk trick:
            # look at the enclosing expression for a chained call.
            parent_call = _find_parent_chained_call(node, child)
            if parent_call is not None:
                chained_attr = parent_call.func
                if (isinstance(chained_attr, ast.Attribute) and
                        chained_attr.attr in ("replace", "astimezone")):
                    continue  # safe — tzinfo is attached

            issues.append((
                path,
                node.name,
                child.lineno,
                "PM-003: Naive datetime mixed with aware datetime",
                f"datetime.strptime() at line {child.lineno} is not "
                f"chained with .replace(tzinfo=...) or .astimezone(), "
                f"but this function also constructs a timezone-aware datetime",
            ))

    return issues


def _find_parent_chained_call(root: ast.AST, target: ast.Call):
    """Return the outer Call node if target is the inner call in a chain like
    target.method(...).  Otherwise return None."""
    for node in ast.walk(root):
        if isinstance(node, ast.Call):
            func = node.func
            if (isinstance(func, ast.Attribute) and
                    isinstance(func.value, ast.Call) and
                    func.value is target):
                return node
    return None


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def scan_file(path: str) -> List[Issue]:
    try:
        source, tree = _load(path)
    except SyntaxError as exc:
        print(f"  [SKIP] {path}: syntax error — {exc}", file=sys.stderr)
        return []

    issues: List[Issue] = []
    issues.extend(check_dict_get_no_none_guard(path, tree))
    issues.extend(check_http_no_timeout(path, tree))
    issues.extend(check_naive_aware_mismatch(path, tree))
    return issues


def collect_python_files(paths: List[str]) -> List[str]:
    result = []
    for p in paths:
        if os.path.isfile(p) and p.endswith(".py"):
            result.append(p)
        elif os.path.isdir(p):
            for root, _dirs, files in os.walk(p):
                for fname in sorted(files):
                    if fname.endswith(".py"):
                        result.append(os.path.join(root, fname))
    return result


def main(argv: List[str]) -> int:
    if argv:
        targets = argv
    else:
        here = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(here)
        targets = [os.path.join(project_root, "app")]

    files = collect_python_files(targets)
    if not files:
        print("No Python files found.", file=sys.stderr)
        return 1

    all_issues: List[Issue] = []
    for fpath in files:
        all_issues.extend(scan_file(fpath))

    if not all_issues:
        print("check_patterns: no issues found.")
        return 0

    print(f"check_patterns: {len(all_issues)} issue(s) found\n")
    for fpath, func, line, pattern, detail in all_issues:
        rel = os.path.relpath(fpath)
        print(f"  FILE     : {rel}")
        print(f"  FUNCTION : {func}")
        print(f"  LINE     : {line}")
        print(f"  PATTERN  : {pattern}")
        print(f"  DETAIL   : {detail}")
        print()

    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
