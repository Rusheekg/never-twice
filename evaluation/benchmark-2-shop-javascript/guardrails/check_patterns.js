#!/usr/bin/env node
/**
 * Never Twice — guardrail script
 * Scans source files for the three patterns from postmortems PM-201, PM-202, PM-203.
 *
 * Usage:  node guardrails/check_patterns.js [source-folder]
 *         Default source folder: src
 *
 * Exit 0  → no issues found
 * Exit 1  → one or more issues found
 */

'use strict';

const fs = require('fs');
const path = require('path');
const acorn = require('acorn');
const walk = require('acorn-walk');

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------
const SOURCE_FOLDER = process.argv[2] || 'src';

// Folders and file-name fragments to skip
const SKIP_DIR_NAMES = new Set([
  'node_modules', 'venv', '.venv', 'env', '__pycache__', 'site-packages',
  'target', 'dist', 'build', '.gradle', 'vendor',
]);
const SKIP_NAME_FRAGMENTS = ['mock', 'fake', 'stub', 'test'];

// notify function names the project actually uses
const NOTIFY_METHOD_NAMES = new Set([
  'sendOrderConfirmation',
  'sendOrderCancellationNotice',
  'sendShippingUpdate',
  'sendEmailChangeAlert',
  'sendCartCheckoutReminder',
]);

// Variable names that hold the notify module (require('./notify') or passed as param)
const NOTIFY_BINDING_NAMES = new Set(['notify']);

// ---------------------------------------------------------------------------
// File collection
// ---------------------------------------------------------------------------
function shouldSkipDir(name) {
  if (SKIP_DIR_NAMES.has(name)) return true;
  const lower = name.toLowerCase();
  return SKIP_NAME_FRAGMENTS.some(f => lower.includes(f));
}

function shouldSkipFile(name) {
  const lower = name.toLowerCase();
  return SKIP_NAME_FRAGMENTS.some(f => lower.includes(f));
}

function collectFiles(dir) {
  const results = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.isDirectory()) {
      if (!shouldSkipDir(entry.name)) {
        results.push(...collectFiles(path.join(dir, entry.name)));
      }
    } else if (entry.isFile() && entry.name.endsWith('.js')) {
      if (!shouldSkipFile(entry.name)) {
        results.push(path.join(dir, entry.name));
      }
    }
  }
  return results;
}

// ---------------------------------------------------------------------------
// AST helpers
// ---------------------------------------------------------------------------
function parse(src) {
  return acorn.parse(src, { ecmaVersion: 2022, sourceType: 'module' });
}

function lineOf(src, pos) {
  return src.slice(0, pos).split('\n').length;
}

function enclosingFunctionName(ancestors) {
  // Walk backwards; stop at the first node that both (a) names a function and
  // (b) whose body contains the current position.  VariableDeclarators are
  // only counted when their init is a function expression/arrow.
  for (let i = ancestors.length - 1; i >= 0; i--) {
    const n = ancestors[i];
    if (n.type === 'FunctionDeclaration' && n.id) return n.id.name;
    if (
      n.type === 'VariableDeclarator' &&
      n.id &&
      n.init &&
      (n.init.type === 'FunctionExpression' ||
       n.init.type === 'ArrowFunctionExpression')
    ) {
      return n.id.name;
    }
    if (n.type === 'Property' && n.key &&
        n.value &&
        (n.value.type === 'FunctionExpression' ||
         n.value.type === 'ArrowFunctionExpression')) {
      return n.key.name || n.key.value || '(anonymous)';
    }
    if (n.type === 'AssignmentExpression' && n.left &&
        n.right &&
        (n.right.type === 'FunctionExpression' ||
         n.right.type === 'ArrowFunctionExpression')) {
      if (n.left.type === 'MemberExpression') {
        return n.left.property.name || '(anonymous)';
      }
      if (n.left.type === 'Identifier') return n.left.name;
    }
  }
  return '(anonymous)';
}

// ---------------------------------------------------------------------------
// Pattern checkers
// ---------------------------------------------------------------------------

/**
 * PM-201 — loose-id-comparison
 * Flag any BinaryExpression using == (loose equality) where at least one
 * operand looks like an ID identifier (name contains "id", case-insensitive).
 *
 * Only == is flagged, not !=.  Rationale: the concrete wrong-result pattern
 * is `==` used when *storing* an ID — it coerces a string "1" to match
 * numeric 1 during a find(), so the item is stored under the raw-string key,
 * and later strict-equality lookups miss it.  `!=` on integer-vs-string IDs
 * coerces symmetrically and produces no wrong output at runtime (JS loose
 * inequality treats 2 and "2" as equal), so it does not constitute a
 * confirmed runtime bug under the mode's binary classification.
 *
 * Exception: intentional null guards (x == null) are never flagged.
 */
function checkLooseIdComparison(src, ast, filePath, issues) {
  walk.ancestor(ast, {
    BinaryExpression(node, ancestors) {
      if (node.operator !== '==') return;

      const { left, right } = node;

      // Allow intentional null/undefined guards: x == null, null == x, etc.
      const isNullLike = n =>
        (n.type === 'Literal' && n.value === null) ||
        (n.type === 'Identifier' && n.name === 'undefined');
      if (isNullLike(left) || isNullLike(right)) return;

      // Check whether an operand is an identifier or member-expression property
      // whose name contains "id" (case-insensitive).
      function looksLikeId(n) {
        if (n.type === 'Identifier') {
          return n.name.toLowerCase().includes('id');
        }
        if (n.type === 'MemberExpression' && n.property) {
          const propName = n.property.name || '';
          return propName.toLowerCase().includes('id');
        }
        return false;
      }

      if (!looksLikeId(left) && !looksLikeId(right)) return;

      const line = lineOf(src, node.start);
      const fnName = enclosingFunctionName(ancestors);
      issues.push({
        file: filePath,
        fn: fnName,
        line,
        pattern: 'loose-id-comparison (PM-201)',
        detail: `Loose operator "${node.operator}" used in an ID comparison`,
      });
    },
  });
}

/**
 * PM-202 — unawaited-notify-call
 * Flag any CallExpression that calls a known notify method where:
 *   - the callee is notify.METHOD_NAME (MemberExpression)
 *   - the call is NOT the argument to an AwaitExpression
 *   - the call is NOT directly chained with .catch() or .then()
 *
 * We walk ancestors: if the immediate parent of the CallExpression is an
 * AwaitExpression, it is awaited. If the immediate parent is a MemberExpression
 * (i.e. the call is used as the object of a .catch() / .then() chain), it is
 * explicitly handled.
 */
function checkUnawaitedNotifyCall(src, ast, filePath, issues) {
  walk.ancestor(ast, {
    CallExpression(node, ancestors) {
      const { callee } = node;
      if (callee.type !== 'MemberExpression') return;

      // Resolve the object name: it must be a known notify binding
      const objName = callee.object.type === 'Identifier' ? callee.object.name : null;
      if (!objName || !NOTIFY_BINDING_NAMES.has(objName)) return;

      const methodName = callee.property.name || callee.property.value;
      if (!NOTIFY_METHOD_NAMES.has(methodName)) return;

      // Walk up the ancestor chain to determine whether this call is safe.
      // NOTE: In acorn-walk's ancestor callback, the ancestors array INCLUDES
      // the current node as the last element.  So ancestors[length-1] is this
      // node itself; ancestors[length-2] is the immediate parent.
      const parent      = ancestors[ancestors.length - 2];
      const grandparent = ancestors[ancestors.length - 3];

      // Case 1: directly awaited — safe
      if (parent && parent.type === 'AwaitExpression') return;

      // Case 2: used as the object of a .catch() or .then() chain — safe (explicit handling)
      // Shape: notify.sendXxx(...).catch(() => {})
      // The CallExpression is the .object of a MemberExpression (".catch"),
      // which is the .callee of another CallExpression.
      if (parent && parent.type === 'MemberExpression' && parent.object === node) {
        if (
          grandparent &&
          grandparent.type === 'CallExpression' &&
          grandparent.callee === parent
        ) {
          const chainMethod = parent.property.name;
          if (chainMethod === 'catch' || chainMethod === 'then') return;
        }
      }

      // Anything else is a silent fire-and-forget — flag it
      const line = lineOf(src, node.start);
      const fnName = enclosingFunctionName(ancestors);
      issues.push({
        file: filePath,
        fn: fnName,
        line,
        pattern: 'unawaited-notify-call (PM-202)',
        detail: `notify.${methodName}() is called without await and without .catch()`,
      });
    },
  });
}

/**
 * PM-203 — find-no-null-guard
 *
 * For each function body in the file, independently check whether any variable
 * assigned from Array.prototype.find() is used without a prior null guard.
 *
 * Two unsafe usage patterns:
 *   1. Object.assign({}, findVar)  — silently returns {} when findVar is undefined
 *   2. findVar.property            — throws TypeError when findVar is undefined
 *
 * Analysis is scoped per function so that variables with the same name in
 * different functions do not interfere with each other.
 */
function checkFindNoNullGuard(src, ast, filePath, issues) {
  // Collect all top-level function bodies (FunctionDeclaration / FunctionExpression
  // / ArrowFunctionExpression) at any nesting level.
  const functionBodies = [];
  walk.ancestor(ast, {
    FunctionDeclaration(node, ancestors) {
      functionBodies.push({ node, ancestors: ancestors.slice() });
    },
    FunctionExpression(node, ancestors) {
      functionBodies.push({ node, ancestors: ancestors.slice() });
    },
    ArrowFunctionExpression(node, ancestors) {
      // Only include arrow functions whose body is a block (has statements),
      // not those that are inline expressions used as .find() predicates.
      if (node.body.type === 'BlockStatement') {
        functionBodies.push({ node, ancestors: ancestors.slice() });
      }
    },
  });

  for (const { node: fnNode, ancestors: fnAncestors } of functionBodies) {
    const body = fnNode.body;
    if (!body || body.type !== 'BlockStatement') continue;

    const fnName = enclosingFunctionName([...fnAncestors, fnNode]);

    // Step 1: collect find-variables declared in this function body
    // Map: varName -> { declLine }
    const findVarsInFn = new Map();
    walk.simple(body, {
      VariableDeclarator(vd) {
        if (!vd.init) return;
        const init = vd.init;
        if (
          init.type === 'CallExpression' &&
          init.callee.type === 'MemberExpression' &&
          init.callee.property.name === 'find'
        ) {
          const varName = vd.id && vd.id.name;
          if (varName) {
            findVarsInFn.set(varName, { declLine: lineOf(src, vd.start) });
          }
        }
      },
    });

    if (findVarsInFn.size === 0) continue;

    // Step 2: collect guarded variable names within this function body
    // A variable is "guarded" if there is an if/conditional/logical that
    // tests it for truthiness before it is used.
    const guardedInFn = new Set();
    walk.simple(body, {
      IfStatement(ifNode) {
        const t = ifNode.test;
        const name = extractGuardedName(t);
        if (name && findVarsInFn.has(name)) guardedInFn.add(name);
      },
      ConditionalExpression(condNode) {
        const name = extractGuardedName(condNode.test);
        if (name && findVarsInFn.has(name)) guardedInFn.add(name);
      },
      LogicalExpression(logNode) {
        // x || fallback
        if (logNode.left.type === 'Identifier' && findVarsInFn.has(logNode.left.name)) {
          guardedInFn.add(logNode.left.name);
        }
      },
    });

    // Step 3: look for unsafe uses of un-guarded find variables.
    // reportedInFn prevents duplicate issues for the same variable within one function.
    const reportedInFn = new Set();

    walk.ancestor(body, {
      // Object.assign({}, findVar) — masking pattern
      CallExpression(callNode) {
        if (
          callNode.callee.type === 'MemberExpression' &&
          callNode.callee.object.type === 'Identifier' &&
          callNode.callee.object.name === 'Object' &&
          callNode.callee.property.name === 'assign'
        ) {
          for (let i = 1; i < callNode.arguments.length; i++) {
            const arg = callNode.arguments[i];
            if (
              arg.type === 'Identifier' &&
              findVarsInFn.has(arg.name) &&
              !guardedInFn.has(arg.name) &&
              !reportedInFn.has(arg.name)
            ) {
              reportedInFn.add(arg.name);
              issues.push({
                file: filePath,
                fn: fnName,
                line: lineOf(src, callNode.start),
                pattern: 'find-no-null-guard (PM-203)',
                detail: `"${arg.name}" from .find() is passed to Object.assign() without a prior null guard — returns {} silently when not found`,
              });
            }
          }
        }
      },

      // findVar.prop — property access without guard
      MemberExpression(memNode, memAncestors) {
        if (memNode.object.type !== 'Identifier') return;
        const varName = memNode.object.name;
        if (!findVarsInFn.has(varName)) return;
        if (guardedInFn.has(varName)) return;
        if (reportedInFn.has(varName)) return;  // already reported once

        // Skip if this MemberExpression is itself the test of an IfStatement
        // (the guard being established right here)
        const parent = memAncestors[memAncestors.length - 2];
        if (parent && parent.type === 'IfStatement' && parent.test === memNode) return;

        reportedInFn.add(varName);
        issues.push({
          file: filePath,
          fn: fnName,
          line: lineOf(src, memNode.start),
          pattern: 'find-no-null-guard (PM-203)',
          detail: `"${varName}" from .find() has property ".${memNode.property.name || '?'}" accessed without a prior null guard — throws TypeError when not found`,
        });
      },
    });
  }
}

/** Extract the identifier name being tested in a guard expression */
function extractGuardedName(t) {
  if (!t) return null;
  if (t.type === 'Identifier') return t.name;
  if (t.type === 'UnaryExpression' && t.operator === '!' && t.argument.type === 'Identifier') {
    return t.argument.name;
  }
  if (t.type === 'BinaryExpression') {
    // x == null, x === null, x === undefined, null == x …
    const lNull = t.left.type === 'Literal' && t.left.value === null;
    const rNull = t.right.type === 'Literal' && t.right.value === null;
    const lUndef = t.left.type === 'Identifier' && t.left.name === 'undefined';
    const rUndef = t.right.type === 'Identifier' && t.right.name === 'undefined';
    if (lNull || lUndef) return t.right.type === 'Identifier' ? t.right.name : null;
    if (rNull || rUndef) return t.left.type === 'Identifier' ? t.left.name : null;
  }
  return null;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------
function main() {
  // Resolve source folder relative to project root (where this script is run from)
  const srcDir = path.resolve(SOURCE_FOLDER);
  if (!fs.existsSync(srcDir)) {
    console.error(`Source folder not found: ${srcDir}`);
    process.exit(1);
  }

  // Check that acorn and acorn-walk are available
  try {
    require.resolve('acorn');
    require.resolve('acorn-walk');
  } catch (e) {
    console.error('Missing dependency: ' + e.message);
    console.error('Run: npm install --save-dev acorn acorn-walk');
    process.exit(2);
  }

  const files = collectFiles(srcDir);
  const allIssues = [];

  for (const filePath of files) {
    const src = fs.readFileSync(filePath, 'utf8');
    let ast;
    try {
      ast = parse(src);
    } catch (e) {
      console.warn(`[WARN] Could not parse ${filePath}: ${e.message}`);
      continue;
    }

    const relPath = path.relative(process.cwd(), filePath).replace(/\\/g, '/');
    checkLooseIdComparison(src, ast, relPath, allIssues);
    checkUnawaitedNotifyCall(src, ast, relPath, allIssues);
    checkFindNoNullGuard(src, ast, relPath, allIssues);
  }

  if (allIssues.length === 0) {
    console.log('Never Twice guardrail: no issues found.');
    process.exit(0);
  }

  console.log(`Never Twice guardrail: ${allIssues.length} issue(s) found.\n`);
  for (const issue of allIssues) {
    console.log(`  [${issue.pattern}]`);
    console.log(`  File    : ${issue.file}`);
    console.log(`  Function: ${issue.fn}`);
    console.log(`  Line    : ${issue.line}`);
    console.log(`  Detail  : ${issue.detail}`);
    console.log('');
  }
  process.exit(1);
}

main();
