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
| CI workflow | `.github/workflows/never-twice.yml` |
| Prevention report | `reports/PREVENTION_REPORT.md` |
| Postmortem template | `docs/POSTMORTEM_TEMPLATE.md` |
