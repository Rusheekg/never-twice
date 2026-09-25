# Never Twice — Prevention Report

Generated: 2026-09-26  
Project: Hotel Booking API  
Audit scope: `app/` (5 files · ~500 LOC)

---

## 1. Summary Table

| Past Incident | Pattern | New Bug Found | File | Function | Fixed | Test Name |
|---|---|---|---|---|---|---|
| PM-001 (SEV-2) | Missing None-guard after `dict.get()` | ✅ Yes | `app/users.py` | `get_user_profile()` | ✅ Yes | `test_get_user_profile_missing_none_check` |
| PM-001 (SEV-2) | Missing None-guard after `dict.get()` | ✅ Yes | `app/bookings.py` | `get_booking_summary()` | ✅ Yes | `test_get_booking_summary_missing_none_check` |
| PM-001 (SEV-2) | Missing None-guard after `dict.get()` | ✅ Yes | `app/rooms.py` | `get_room_details()` | ✅ Yes | `test_get_room_details_missing_none_check_unknown_room` + `test_get_room_details_none_description_field` |
| PM-002 (SEV-1) | Outbound HTTP call without timeout/error handling | ✅ Yes | `app/notifications.py` | `send_sms_notification()` | ✅ Yes | `test_send_sms_notification_timeout_raises_runtime_error` + `test_send_sms_notification_connection_error_raises_runtime_error` |
| PM-002 (SEV-1) | Outbound HTTP call without timeout/error handling | ✅ Yes | `app/payments.py` | `process_payment()` | ✅ Yes | `test_process_payment_timeout_raises_runtime_error` + `test_process_payment_connection_error_raises_runtime_error` |
| PM-003 (SEV-3) | Naive/aware datetime mismatch | ✅ Yes | `app/bookings.py` | `create_booking()` | ✅ Yes | `test_create_booking_naive_aware_datetime_mismatch` |
| PM-003 (SEV-3) | Naive/aware datetime mismatch | ✅ Yes | `app/bookings.py` | `get_booking_duration()` | ✅ Yes | `test_get_booking_duration_naive_aware_datetime_mismatch` |

---

## 2. Locations Checked and Judged Safe

| File | Function | Pattern Checked | Reason Safe |
|---|---|---|---|
| `app/users.py` | `get_user()` | PM-001 | Returns `.get()` result directly; all call sites check for `None` before use |
| `app/users.py` | `update_user_profile()` | PM-001 | Already fixed in PM-001 hotfix v1.14.3; has explicit `if user is None` guard |
| `app/users.py` | `create_user()` | PM-001 | No store lookup — constructs new record from validated input |
| `app/users.py` | `list_users()` | PM-001 | Returns all values; no single-key lookup |
| `app/bookings.py` | `get_booking()` | PM-001 | Returns `.get()` directly; route handler checks `None` |
| `app/bookings.py` | `create_booking()` | PM-001 | Checks `user is None` and `room is None` explicitly |
| `app/bookings.py` | `cancel_booking()` | PM-001 / PM-002 | Has `if booking is None` guard; HTTP call has `timeout=5` and errors intentionally swallowed (non-blocking cancellation notification) |
| `app/bookings.py` | `get_booking_duration()` | PM-001 | Has `if booking is None` guard |
| `app/bookings.py` | `is_booking_active()` | PM-001 / PM-003 | Already fixed in PM-003 hotfix v1.18.2; both strptime results have `.replace(tzinfo=timezone.utc)` |
| `app/bookings.py` | `confirm_booking()` | PM-001 | Has `if booking is None` guard |
| `app/bookings.py` | `list_bookings_for_user()` | PM-001 | Iterates values; no single-key lookup |
| `app/rooms.py` | `get_room()` | PM-001 | Returns `.get()` directly; route handler checks `None` |
| `app/rooms.py` | `list_available_rooms()` | PM-001 | Filters `ROOMS.values()`; no single-key lookup |
| `app/rooms.py` | `update_room_status()` | PM-001 | Has `if room is None` guard |
| `app/rooms.py` | `calculate_room_cost()` | PM-001 | Has `if room is None` guard |
| `app/rooms.py` | `search_rooms()` | PM-001 | Filters `ROOMS.values()` with criteria; no single-key lookup |
| `app/notifications.py` | `send_email_notification()` | PM-002 | Already fixed in PM-002 hotfix v1.17.1; has `timeout=5` and `try/except` |
| `app/notifications.py` | `notify_booking_confirmed()` | PM-002 | Delegates to fixed `send_email_notification()` |
| `app/notifications.py` | `get_notification_log()` | PM-001 | Iterates values; no single-key lookup |
| `app/payments.py` | `get_payment()` | PM-001 | Returns `.get()` directly; route handler checks `None` |
| `app/payments.py` | `get_payment_status()` | PM-001 | Iterates values; returns safe default dict on miss |
| `app/payments.py` | `refund_payment()` | PM-001 / PM-002 | Has `if payment is None` guard; HTTP call has `timeout=8` and `try/except` |
| `app/payments.py` | `list_payments_for_user()` | PM-001 | Iterates values; no single-key lookup |

---

## 3. Totals

| Metric | Value |
|---|---|
| Patterns extracted from postmortems | 3 |
| Python files reviewed | 5 |
| Functions reviewed | ~35 |
| **Confirmed bugs found** | **7** |
| Locations checked and ruled out as safe | 23 |
| **Tests written** | **10** |
| Tests failing before fix | 10 / 10 |
| Tests passing after fix | 10 / 10 |
| Guardrail issues before fix | 7 |
| Guardrail issues after fix | 0 |

---

## 4. Timestamps and Duration

| Step | Start Time | End Time | Duration |
|---|---|---|---|
| Step 1 — Learn from history | 2026-09-26 00:10:59 | 2026-09-26 00:11:58 | ~1 min |
| Step 2 — Hunt in parallel (3 subagents) | 2026-09-26 00:11:58 | 2026-09-26 00:13:41 | ~2 min |
| Step 3 — Prove each bug | 2026-09-26 00:13:41 | 2026-09-26 00:14:56 | ~1 min 15 sec |
| Step 4 — Build guardrails | 2026-09-26 00:14:56 | 2026-09-26 00:17:51 | ~3 min |
| Checkpoint + human approval | 2026-09-26 00:17:51 | 2026-09-26 00:17:51 | — |
| Step 5 — Fix and verify | 2026-09-26 00:17:51 | 2026-09-26 00:19:28 | ~1 min 37 sec |
| Step 6 — Report | 2026-09-26 00:19:28 | 2026-09-26 00:19:28 | — |
| **Total** | | | **~9 min** |

---

## 5. What Would Have Happened

### Bug 1 — `get_user_profile()` (PM-001 pattern)

Every call to `GET /users/{id}/profile` for a non-existent user ID would have
raised `TypeError: 'NoneType' object is not subscriptable`, identical to the
PM-001 incident. Flask's generic error handler would have returned HTTP 500
with no useful information. Based on PM-001 this could have gone undetected for
hours (the original alert threshold was too high for low-traffic endpoints).
Affected users would have received a 500 error instead of a 404, leaking no
helpful diagnostic message and potentially causing client-side retry storms.

### Bug 2 — `get_booking_summary()` (PM-001 pattern)

`GET /bookings/{id}/summary` for any invalid or deleted booking ID would have
crashed with `TypeError`. The Flask route catches a broad `Exception` and
returns 500. The operations dashboard, which uses this summary endpoint to
display booking details, would have shown error tiles for any booking that was
cancelled or whose ID was mistyped — silently, without alarming staff until a
pattern was noticed.

### Bug 3 — `get_room_details()` (PM-001 pattern + None field)

Two crash paths: (a) unknown room IDs would raise `TypeError` → 500; (b) room
`r110` (a real, existing maintenance room) would raise `AttributeError: 'NoneType'
object has no attribute 'strip'` on *every* call to `GET /rooms/r110/details`.
This is not a theoretical edge case — `r110` is in the seed data. Any booking or
admin flow that looks up maintenance-room details would have crashed, masking the
room from any UI that renders detailed descriptions.

### Bug 4 — `send_sms_notification()` (PM-002 pattern)

This is the PM-002 failure mode reproduced almost exactly. `notify_payment_received()`
routes every payment receipt through `send_sms_notification()`. A gateway outage
would have caused all 8 Gunicorn workers to block within minutes of the first
payment being processed during the outage window. Based on PM-002 (SEV-1, 23-minute
full outage, £6,200 revenue at risk), this bug in the SMS path could have triggered
an equivalent total API blackout — worse, because payment processing and SMS
receipts are coupled on the same critical path.

### Bug 5 — `process_payment()` (PM-002 pattern)

Payment is the highest-criticality path in the entire system: it is called
synchronously during booking confirmation. A payment gateway timeout with no
timeout parameter set means each blocked `requests.post()` call occupies a
Gunicorn worker indefinitely. Under even modest concurrent booking traffic,
all workers would saturate within seconds, halting the entire API. Unlike
PM-002 (which was triggered by a planned maintenance window), payment gateways
can experience transient slowdowns during peak load — this bug could have
triggered unannounced. Revenue impact would exceed PM-002's £6,200 estimate
because *all* in-flight bookings (not just receipt emails) would have failed.

### Bug 6 — `create_booking()` (PM-003 pattern)

Every call to `POST /bookings/` on Python 3.9 would have raised
`TypeError: can't compare offset-naive and offset-aware datetimes` at line 71,
before any booking was written to the store. **This bug would have made it
impossible to create any new booking in the system.** Unlike PM-003 (a silent
wrong result), this crash would have been immediately visible — but would have
appeared as a mysterious 400 or 500 depending on how the route handler caught
the exception, with no useful message explaining the timezone issue.

### Bug 7 — `get_booking_duration()` (PM-003 pattern)

`GET /bookings/{id}/duration` would have raised `TypeError` on every call,
meaning any dashboard or operations tool that shows how many nights a guest has
been staying would have been broken entirely. Staff relying on this endpoint to
manage check-in/check-out timing would have received 404 errors (because the
route catches `ValueError` → 404, but the actual exception is `TypeError` which
propagates to Flask's 500 handler). Combined with Bug 6, all datetime-sensitive
operations on bookings would have been non-functional.

---

## 6. Artifacts Produced

| File | Description |
|---|---|
| `reports/patterns.md` | 3 extracted bug patterns with recognition rules and fix guidance |
| `reports/findings.md` | Full per-function audit results (7 confirmed bugs + 23 safe locations) |
| `tests/test_confirmed_bugs.py` | 10 pytest tests (all failed before fix, all pass after fix) |
| `guardrails/check_patterns.py` | AST-based static analysis script (0 issues after fix) |
| `guardrails/REVIEW_CHECKLIST.md` | 3-section code review checklist linked to postmortems |
| `reports/PREVENTION_REPORT.md` | This document |
