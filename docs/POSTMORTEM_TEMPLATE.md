# Postmortem Template

<!-- Copy this file to postmortems/PM-NNN-short-description.md and fill in every section.
     Files whose names contain "TEMPLATE" are ignored by Never Twice, so rename it first. -->

# PM-NNN — [One-line title: what broke and what the visible symptom was]

| Field | Value |
|---|---|
| **Incident ID** | PM-NNN |
| **Date** | YYYY-MM-DD |
| **Severity** | SEV-1 / SEV-2 / SEV-3 |
| **Status** | Resolved |

---

## Summary

<!-- 2-4 sentences: what failed, how it was introduced, how long it lasted,
     and what the root cause turned out to be. -->

---

## Customer Impact

<!-- Quantify the impact as precisely as possible. Include:
     - Number of affected users (estimated or confirmed)
     - Duration of impact
     - Number of failed requests / transactions
     - Revenue at risk or lost (if known)
     - Customer complaints received
     - Any data loss or corruption -->

- **Affected users:** [number or estimate]
- **Duration:** [HH:MM (start UTC - end UTC)]
- **Failed requests:** [number and endpoint/operation]
- **Revenue at risk:** [amount or "None identified"]
- **Customer complaints received:** [number]
- **Data loss:** [description or "None"]

---

## Detection

<!-- How was the incident discovered? Was it an automated alert, a customer
     complaint, or manual observation? How long after the incident started was
     it detected, and why? -->

---

## Timeline

| Time (UTC) | Event |
|---|---|
| YYYY-MM-DD HH:MM | [e.g. Deployment of release vX.Y.Z completes] |
| YYYY-MM-DD HH:MM | [First error appears in logs] |
| YYYY-MM-DD HH:MM | [Alert fires / issue reported] |
| YYYY-MM-DD HH:MM | [Engineer begins investigation] |
| YYYY-MM-DD HH:MM | [Root cause identified] |
| YYYY-MM-DD HH:MM | [Hotfix deployed / incident resolved] |
| YYYY-MM-DD HH:MM | [Post-incident review held] |

---

## Root Cause

<!-- This is the most important section for Never Twice. Be specific:
     - What was the exact code path that failed?
     - What assumption did the code make that turned out to be wrong?
     - What class of bug does this represent (e.g. missing None check, no
       timeout on outbound call, naive/aware datetime mismatch)?

     Include a "code before" block showing the buggy code: -->

[Explanation of root cause]

### Code before (version that introduced the bug)

```python
# paste the broken function here
```

### Code after (hotfix)

```python
# paste the fixed function here
```

---

## Fix Applied

<!-- Describe the fix in one or two sentences as a general rule, not just
     as "we added a None check here". The rule should be generalisable:
     "Any dict.get() result must be checked for None before use."
     Never Twice uses this section to derive the pattern it hunts for. -->

[Description of the fix and the general rule it encodes]

Hotfix released as **vX.Y.Z** at HH:MM UTC on YYYY-MM-DD.

---

## Lessons Learned

<!-- List 2-4 actionable lessons. For each one, state the general principle,
     not just the specific instance. -->

1. **[General principle]:** [Explanation]
2. **[General principle]:** [Explanation]
3. **[General principle]:** [Explanation]

---

## Action Items

| # | Action | Owner | Due | Status |
|---|---|---|---|---|
| 1 | [Immediate fix or process change] | [Team] | YYYY-MM-DD | [ ] Pending |
| 2 | [Monitoring or alerting improvement] | [Team] | YYYY-MM-DD | [ ] Pending |
| 3 | [Code review or tooling gate] | [Team] | YYYY-MM-DD | [ ] Pending |
| 4 | **Audit the codebase for similar patterns** | Backend Team | YYYY-MM-DD | [ ] Pending |
