# PM-003 — Incorrect Booking Availability: Timezone Mismatch Causes Wrong Active-Status Results

| Field | Value |
|---|---|
| **Incident ID** | PM-003 |
| **Date** | 2026-07-09 |
| **Severity** | SEV-3 |
| **Status** | Resolved |

---

## Summary

A silent logic error in the booking availability check caused the system to
incorrectly classify bookings as inactive (or to crash with a `TypeError` when
the server's local clock offset triggered the comparison path). Guests whose
check-in date had passed were sometimes shown as "not currently checked in" on
the internal operations dashboard, leading to room assignment conflicts at the
front desk. The defect was a classic timezone mismatch: one datetime was
constructed as timezone-naive while the other was timezone-aware, making the
comparison either raise an unhandled exception or produce a silently wrong result
depending on the Python version and system locale.

---

## Customer Impact

- **Incident window:** Approximately 6 weeks (undetected from 2026-05-28 when
  the dashboard feature shipped, until discovered 2026-07-09)
- **Incorrectly flagged bookings:** 23 confirmed cases identified via audit
  (actual number likely higher for the pre-audit period)
- **Operational disruption:** 6 front-desk room assignment conflicts during
  peak check-in hours; 2 required guests to wait while staff resolved duplicates
  manually
- **Guest complaints:** 4 formal complaints; 2 escalated to the duty manager
- **Data corruption:** None — no bookings were modified or deleted as a result
- **Revenue impact:** 2 partial refunds issued as goodwill gestures (total £140)

---

## Detection

The issue was discovered on 2026-07-09 by a front-desk supervisor who noticed
that the operations dashboard consistently showed a VIP guest's long-stay booking
as "inactive" despite the guest being physically present in the hotel. The
supervisor raised a ticket with the engineering team.

Initial investigation by an engineer reproduced the problem locally, where the
call raised:

```
TypeError: can't compare offset-naive and offset-aware datetimes
```

On the production server running Python 3.9 with a UTC-offset system clock, the
same code path did not raise but instead returned `False` (inactive) for all
bookings whose check-in date was before the naive/aware boundary — a silent
wrong result rather than a visible crash.

---

## Timeline

| Time (UTC) | Event |
|---|---|
| 2026-05-28 | Dashboard feature shipping in v1.15.0 introduces the defective comparison |
| 2026-07-09 10:14 | Front-desk supervisor reports incorrect "inactive" status for an in-house guest |
| 2026-07-09 10:31 | Ticket escalated to backend engineering |
| 2026-07-09 10:48 | Engineer reproduces `TypeError` locally on a UTC+1 development machine |
| 2026-07-09 11:02 | Root cause confirmed as naive/aware datetime mismatch in `is_booking_active()` |
| 2026-07-09 11:15 | Fix implemented and peer-reviewed |
| 2026-07-09 11:34 | Hotfix v1.18.2 deployed; dashboard results immediately correct |
| 2026-07-09 11:45 | Booking audit run to identify historically affected records |
| 2026-07-09 14:00 | Post-incident review meeting held |

---

## Root Cause

The `is_booking_active()` function determines whether a booking's date range
covers the current moment. It constructs the current time using
`datetime.now(timezone.utc)`, which produces a **timezone-aware** datetime
object. The check-in and check-out dates, however, were parsed from stored
date strings using `datetime.strptime(..., "%Y-%m-%d")`, which always produces a
**timezone-naive** datetime object (no `tzinfo` attribute).

Python's comparison operators (`<=`, `<`) raise a `TypeError` when one operand
is timezone-aware and the other is timezone-naive. The specific behaviour on
production — silent wrong result rather than a crash — occurred because the
production server's system timezone caused the C-level comparator to short-
circuit before the mixed-type path was reached in certain conditions. This
class of bug is particularly dangerous because it can produce wrong answers on
some systems while raising exceptions on others, making it hard to reproduce
consistently.

### Code before (v1.15.0 – v1.18.1)

```python
def is_booking_active(booking_id: str) -> bool:
    booking = BOOKINGS.get(booking_id)
    if booking is None:
        return False

    now = datetime.now(timezone.utc)          # timezone-aware
    ci = datetime.strptime(booking["check_in"], "%Y-%m-%d")   # naive
    co = datetime.strptime(booking["check_out"], "%Y-%m-%d")  # naive
    return ci <= now < co  # TypeError or silent wrong result
```

### Code after (hotfix v1.18.2)

```python
def is_booking_active(booking_id: str) -> bool:
    """Return True if the booking covers today (timezone-aware comparison)."""
    booking = BOOKINGS.get(booking_id)
    if booking is None:
        return False

    now = datetime.now(timezone.utc)
    ci = datetime.strptime(booking["check_in"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    co = datetime.strptime(booking["check_out"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return ci <= now < co
```

---

## Fix Applied

Both `ci` and `co` are now explicitly made timezone-aware by appending
`.replace(tzinfo=timezone.utc)` immediately after the `strptime()` call. All
three datetime values in the comparison — `ci`, `now`, and `co` — share the
same `timezone.utc` tzinfo, eliminating both the `TypeError` and the silent
wrong-result path.

Hotfix released as **v1.18.2** at 11:34 UTC on 2026-07-09.

---

## Lessons Learned

1. **Naive datetime objects must never mix with aware ones.** The fix is simple
   but the bug class is subtle: Python will sometimes raise an exception and
   sometimes silently produce an incorrect result depending on which operand is
   evaluated first and the runtime environment. The only safe rule is: every
   datetime that participates in a comparison or arithmetic operation must carry
   explicit timezone information.

2. **Bugs in silent-wrong-result mode are harder to find than crashes.** A
   `TypeError` would have appeared in error logs and triggered an alert
   immediately. A silently incorrect boolean silently corrupted dashboard data
   for six weeks. Code paths that return booleans from datetime comparisons
   deserve extra scrutiny and integration tests that exercise both the truthy
   and falsy branches with timezone-aware input.

3. **New features need integration tests against realistic data.** The
   `is_booking_active()` function was added as part of the dashboard feature but
   had no automated test. A test that passed a real booking ID and asserted the
   expected boolean would have caught the `TypeError` in CI on the first run.

4. **The dashboard feature was released without any QA on the date-boundary
   behaviour.** Acceptance criteria should include at least one scenario where
   the current time falls within the booking range and one where it falls outside,
   verified against production-like data.

---

## Action Items

| # | Action | Owner | Due | Status |
|---|---|---|---|---|
| 1 | Add linter rule (or pre-commit hook) to flag `datetime.strptime` calls not immediately followed by `.replace(tzinfo=...)` or `.astimezone()` | Engineering Lead | 2026-07-23 | ✅ Completed |
| 2 | Add integration tests for `is_booking_active()` covering in-range, pre-range, and post-range cases with timezone-aware inputs | Backend Team | 2026-07-16 | ✅ Completed |
| 3 | Establish a policy: all datetime objects stored in or retrieved from the data layer must include UTC tzinfo | Engineering Lead | 2026-07-23 | ✅ Completed |
| 4 | Contact the 4 affected guests who submitted formal complaints and offer a goodwill discount code | Guest Relations | 2026-07-12 | ✅ Completed |
| 5 | Audit the codebase for datetime comparisons or subtractions that mix timezone-naive and timezone-aware objects | Backend Team | 2026-07-30 | ❌ Not completed |
