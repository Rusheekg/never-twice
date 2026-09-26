# How to Use Never Twice on Your Project

Never Twice is a Bob mode that reads your past incident postmortems, extracts
the bug patterns they describe, hunts for those same patterns across your
codebase, proves every new occurrence with a failing test, builds a static-
analysis guardrail, and produces a prevention report — all in one automated
workflow with a mandatory human-approval gate before any code is changed.

---

## Prerequisites

- IBM Bob installed and accessible
- A Python project (Python 3.9+)
- At least one postmortem in the format described in
  [POSTMORTEM_TEMPLATE.md](POSTMORTEM_TEMPLATE.md)
- `pytest` available in your project's virtual environment
  (`pip install pytest`, or add it to `requirements.txt`)

---

## Step 1 — Write Your Postmortems

Create a `postmortems/` folder at the root of your project (or use any folder
name you prefer — you will tell Never Twice where to look).

For each past incident, create one Markdown file following the format in
[POSTMORTEM_TEMPLATE.md](POSTMORTEM_TEMPLATE.md).

**The two sections Never Twice relies on most are:**

| Section | What to include |
|---|---|
| `## Root Cause` | A clear explanation of the bug and why it happened, including a "code before" block showing the broken code |
| `## Fix Applied` | The corrected code ("code after" block) and the rule that prevents the class of bug |

The more precisely you describe the pattern (not just "we forgot a None check"
but "any `dict.get()` result used without a `None` guard"), the better Never
Twice will generalise it to other locations in the codebase.

**Naming convention:** `PM-NNN-short-description.md`  
**Files whose names contain `TEMPLATE`** (any case) are automatically ignored.

---

## Step 2 — Select and Run the Never Twice Mode

1. Open your project in Bob.
2. Click the **mode picker** (the current mode name shown in the top-left
   corner of the chat, e.g. "Agent").
3. Select **Never Twice** from the list.
4. Send any message to start — for example: `Run the full workflow.`

Bob will immediately ask you two questions:

> **(a) Which folder contains the Python source files to scan?**  
> **(b) Where are the postmortems?** (default: `postmortems`)

Answer both in one message, for example:

```
Source folder: src
Postmortems folder: postmortems
```

Or, if your defaults match:

```
Source folder: app
```

Never Twice will then run Steps 1–4 automatically (learn patterns, hunt for
bugs, write failing tests, build guardrails) and stop at the approval
checkpoint.

---

## Step 3 — Review and Respond to the Approval Checkpoint

After Step 4, Never Twice will print a table like this and **stop**:

| # | File | Function | Pattern | Proposed Fix |
|---|---|---|---|---|
| 1 | `src/users.py` | `get_profile()` | PM-001: Missing None-guard | Add `if user is None: raise ValueError(...)` |
| … | … | … | … | … |

**Before approving, review:**

- Does each "Confirmed bug" entry look like a real bug to you?
- Does the proposed fix match what the postmortem describes?
- Are there any false positives (locations flagged that you know are safe)?

If you see a false positive, tell Never Twice: `Bug 3 is safe because X` —
it will update the finding and re-show the table.

When you are satisfied, reply with exactly:

```
approve
```

Never Twice will then apply every fix, rerun all tests, and rerun the guardrail
script. **No application code is touched before this word.**

---

## Step 4 — Enable the CI Guardrail on GitHub

The file `.github/workflows/never-twice.yml` in this repository runs the tests
and the guardrail script on every push and pull request. To enable it on your
own project:

1. Copy `.github/workflows/never-twice.yml` into your repository at the same
   path.
2. Edit the `pip install` step if your `requirements.txt` lives somewhere other
   than `app/requirements.txt`:

   ```yaml
   - name: Install dependencies
     run: pip install -r requirements.txt   # adjust path as needed
   ```

3. Edit the `python guardrails/check_patterns.py` line if your source folder
   is not named `app`:

   ```yaml
   - name: Run guardrail pattern check
     run: python guardrails/check_patterns.py src/   # adjust folder as needed
   ```

4. Commit and push. GitHub Actions will run the workflow automatically on every
   push and pull request. The workflow fails (red ✗) if any test fails or any
   guardrail pattern is detected.

**Matrix:** The workflow tests on Python 3.9 and 3.12 by default. Add or remove
versions in the `matrix.python-version` list in the YAML file.

---

## CI for Your Language

Never Twice ships two generic CI templates in [`docs/ci-templates/`](ci-templates/)
that you can adapt for any project. Each template is a complete GitHub Actions
workflow with **every value a team must adjust clearly marked with a `# REPLACE`
comment**.

### Available templates

| File | Language / runtime | Installs via | Runs tests with | Runs guardrail with |
|---|---|---|---|---|
| [`docs/ci-templates/python.yml`](ci-templates/python.yml) | Python | `pip install -r <requirements file>` | `pytest` | `python guardrails/check_patterns.py <SOURCE_FOLDER>` |
| [`docs/ci-templates/javascript.yml`](ci-templates/javascript.yml) | JavaScript / Node.js LTS | `npm ci` | `npm test` | `node guardrails/check_patterns.js <SOURCE_FOLDER>` |

Both templates:
- Trigger on every `push` and `pull_request` to any branch.
- Use the current major versions of the official actions:
  `actions/checkout@v4`, `actions/setup-python@v5`, `actions/setup-node@v4`.
- Fail the workflow automatically if tests return a non-zero exit code **or** if
  the guardrail script detects any issues (guardrail exits non-zero when issues
  are found).

### Placeholders to replace

Before committing a template, search for `# REPLACE` and update each one:

| Placeholder | What to set |
|---|---|
| `<SOURCE_FOLDER>` | The folder containing your application source files (e.g. `app`, `src`, `lib`) |
| Requirements file path | Path to your `requirements.txt` or equivalent (Python only) |
| Test command | Your exact test command (e.g. `pytest tests/`, `npx vitest run`) |
| Branch filter | The branches you want the workflow to run on (e.g. `[main, develop]`) |
| Python / Node.js version matrix | The runtime versions your project targets |

### Using the proposed CI file from a Never Twice run

When Never Twice completes a run on a project that has **no existing
`.github/workflows/never-twice.yml`**, it automatically generates a ready-to-use
workflow file tailored to the detected language and saves it as
`reports/proposed-ci.yml`.

To activate it:

1. Review `reports/proposed-ci.yml` — confirm the source folder, dependency
   install command, test command, and guardrail invocation are correct.
2. Copy it to `.github/workflows/never-twice.yml`:

   ```bash
   cp reports/proposed-ci.yml .github/workflows/never-twice.yml
   ```

3. Commit and push. GitHub Actions picks it up automatically.

Never Twice will **never** create or modify files under `.github/` on its own —
the copy step is always a deliberate human action.

---

## Step 5 — Read the Prevention Report

After the workflow finishes, open `reports/PREVENTION_REPORT.md`. It contains:

| Section | What it tells you |
|---|---|
| **Summary table** | Every past incident → pattern → new bugs found → where → fixed or not → test name |
| **Safe locations** | Every function that looked suspicious but was ruled out, with the reason |
| **Totals** | Bugs found, tests written, test results before/after fix, guardrail issues before/after |
| **Timings** | How long each step took and the total wall-clock time |
| **What would have happened** | The likely production impact of each bug, based on the matching postmortem |

Use the summary table in sprint retrospectives, architecture reviews, or
onboarding documentation to show which categories of bugs recur in your
codebase.

---

## Quick Reference

| What | Where |
|---|---|
| Mode definition | `.bob/custom_modes.yaml` |
| Pattern extraction output | `reports/patterns.md` |
| Full audit findings | `reports/findings.md` |
| Failing/passing tests | `tests/test_confirmed_bugs.py` |
| Guardrail script | `guardrails/check_patterns.py` |
| Code review checklist | `guardrails/REVIEW_CHECKLIST.md` |
| CI workflow (active) | `.github/workflows/never-twice.yml` |
| CI workflow (proposed) | `reports/proposed-ci.yml` *(generated when no active CI found)* |
| CI templates | `docs/ci-templates/python.yml`, `docs/ci-templates/javascript.yml` |
| Prevention report | `reports/PREVENTION_REPORT.md` |
| Postmortem template | `docs/POSTMORTEM_TEMPLATE.md` |

---

## Install for All Your Projects

By default the Never Twice mode is only available inside this repository
because its definition lives in `.bob/custom_modes.yaml`. Run the installer
once and Bob will offer the mode in **every** project you open — no copying
needed.

### 1 — Install the Python dependency

```bash
pip install -r scripts/requirements.txt
```

### 2 — Install the mode globally

```bash
python scripts/install_never_twice.py
```

The script will:
- Locate your global Bob modes file (`~/.bob/settings/custom_modes.yaml` on
  macOS/Linux; `%USERPROFILE%\.bob\settings\custom_modes.yaml` on Windows).
- Create the file and any missing parent folders if they do not already exist.
- If the file exists, create a timestamped backup (e.g.
  `custom_modes.yaml.bak-20240115T143022`) before making any changes.
- Add the `never-twice` entry, or replace an existing entry with the same slug
  — all other modes in the file are left untouched.
- Read the file back and print a verification result confirming it parses
  correctly and contains exactly one `never-twice` entry.

> **Note on formatting:** PyYAML normalises whitespace and removes comments
> when it rewrites the file. Your original is preserved in the timestamped
> backup.

### 3 — Preview changes without writing (dry run)

```bash
python scripts/install_never_twice.py --dry-run
```

Prints the global file path, the backup path that *would* be created, and the
full YAML that *would* be written — without touching any file.

### 4 — Remove the mode

```bash
python scripts/install_never_twice.py --uninstall
```

Removes only the `never-twice` entry, creates a backup first, and verifies the
result. All other modes are left untouched.

### 5 — Confirm the mode appears in Bob

1. Open **any other folder** in Bob (one that does not have its own
   `.bob/custom_modes.yaml` with a `never-twice` entry).
2. Click the **mode picker** in the top-left corner of the chat panel.
3. **Never Twice** should appear in the list.

If it does not appear, restart Bob (the global modes file is read on startup).

### What happens if a project already has its own Never Twice entry?

If a project has `.bob/custom_modes.yaml` containing a `never-twice` entry,
**that project-level definition takes precedence** over the global one for that
project. The global entry is used only when no project-level entry with the
same slug exists. Running the installer does not affect, overwrite, or conflict
with any project-level mode.
