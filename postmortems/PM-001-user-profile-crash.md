# PM-001 — Production Crash: User Profile Endpoint Returns 500 for Unknown Users

| Field | Value |
|---|---|
| **Incident ID** | PM-001 |
| **Date** | 2026-03-14 |
| **Severity** | SEV-2 |
| **Status** | Resolved |

---

## Summary

A `TypeError` crash in the user profile update path caused all `PATCH /users/{id}`
requests for non-existent user IDs to return HTTP 500 instead of a proper 404. The
error was introduced when the `update_user_profile()` function was refactored to
accept partial field updates but the None-guard on the dictionary lookup was
accidentally removed. The issue went undetected for approximately four hours before
an automated alert fired.

---

## Customer Impact

- **Affected users:** ~340 unique users who submitted profile update requests
  (estimated from error log line count)
- **Duration:** 4 hours 11 minutes (09:02 UTC – 13:13 UTC)
- **Failed requests:** 1,247 `PATCH /users/{id}` calls returned 500
- **Direct customer complaints received:** 12 (via support chat)
- **Data loss:** None — no writes reached the data layer for the failing requests

The majority of affected users were attempting to update billing addresses or
contact details ahead of an upcoming loyalty programme promotion, which increased
traffic to this endpoint roughly threefold compared to a normal Friday.

---

## Detection

At 13:02 UTC, the on-call engineer received a PagerDuty alert for a sustained
spike in HTTP 500 responses on `PATCH /users/*` (threshold: >50 errors/min for
3 consecutive minutes). The alert had been firing since approximately 12:58 UTC,
meaning the first ~4 hours of impact went undetected due to an error-rate
threshold that was set too high for low-traffic endpoints.

A secondary signal came from the customer support queue: five users had submitted
complaints between 10:30 and 12:45 UTC that were not escalated to engineering
until the alert fired.

---

## Timeline

| Time (UTC) | Event |
|---|---|
| 2026-03-14 08:55 | Deployment of release v1.14.2 completes successfully |
| 2026-03-14 09:02 | First 500 errors appear in application logs |
| 2026-03-14 10:31 | First customer support complaint received; triaged as isolated |
| 2026-03-14 12:58 | Error-rate alert fires in PagerDuty |
| 2026-03-14 13:02 | On-call engineer acknowledges alert and begins investigation |
| 2026-03-14 13:09 | Root cause identified in `update_user_profile()` via log trace |
| 2026-03-14 13:13 | Hotfix deployed; 500 errors cease immediately |
| 2026-03-14 13:25 | All systems confirmed stable; incident marked resolved |
| 2026-03-14 15:00 | Post-incident review meeting held |

---

## Root Cause

The `update_user_profile()` function calls `USERS.get(user_id)` to retrieve a
user record. When the supplied `user_id` does not exist in the store,
`dict.get()` returns `None`. The original implementation checked for `None`
before proceeding, but a refactor in v1.14.2 dropped that guard. The code then
attempted to subscript the `None` value directly, raising:

```
TypeError: 'NoneType' object is not subscriptable
```

Because the exception was unhandled at the function level, it propagated all the
way to Flask's generic 500 handler, leaking no useful information to the caller
and logging only a stack trace on the server side.

### Code before (introduced in v1.14.2)

```python
def update_user_profile(user_id: str, updates: dict) -> dict:
    """Apply partial updates to a user record."""
    user = USERS.get(user_id)

    allowed_fields = {"name", "email", "phone", "billing_address", "preferences"}
    for key, value in updates.items():
        if key in allowed_fields:
            user[key] = value  # TypeError if user is None

    return user
```

### Code after (hotfix v1.14.3)

```python
def update_user_profile(user_id: str, updates: dict) -> dict:
    """Apply partial updates to a user record."""
    user = USERS.get(user_id)
    if user is None:
        raise ValueError(f"User {user_id!r} not found")

    allowed_fields = {"name", "email", "phone", "billing_address", "preferences"}
    for key, value in updates.items():
        if key in allowed_fields:
            user[key] = value

    return user
```

---

## Fix Applied

Added an explicit `None` check immediately after the `dict.get()` call. When the
user is not found, the function now raises a `ValueError` with a descriptive
message. The calling Flask route already catches `ValueError` and returns a
structured HTTP 404, so no changes were required at the route layer.

Hotfix released as **v1.14.3** at 13:13 UTC on the same day.

---

## Lessons Learned

1. **Refactors that touch lookup patterns need focused review.** The `None` guard
   was removed as a side-effect of restructuring the validation logic, not as an
   intentional decision. A checklist item for "verify all `dict.get()` return
   values are checked" would have caught this.

2. **Alert thresholds on low-traffic endpoints were too coarse.** The 500-error
   alert fired only after 4 hours because the threshold was calibrated for
   high-traffic endpoints. Percentage-based thresholds (e.g., >5% 5xx rate over
   2 minutes) catch problems on low-traffic paths much earlier.

3. **Support complaints were not escalated promptly.** Multiple customers reported
   the problem via chat hours before the alert fired. A tighter feedback loop
   between support and on-call engineering would have reduced the impact window.

---

## Action Items

| # | Action | Owner | Due | Status |
|---|---|---|---|---|
| 1 | Lower 5xx alert thresholds to percentage-based rules for all user-facing endpoints | Platform | 2026-03-28 | ✅ Completed |
| 2 | Add a support-to-engineering escalation SLA of 30 minutes for repeated error reports | Support Ops | 2026-04-04 | ✅ Completed |
| 3 | Update code review checklist to include explicit check for `dict.get()` return value handling | Engineering Lead | 2026-03-21 | ✅ Completed |
| 4 | Audit the codebase for similar patterns where a lookup result is used without a None/empty check | Backend Team | 2026-04-11 | ❌ Not completed |
