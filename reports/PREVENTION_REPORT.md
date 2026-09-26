# Prevention Report

Generated: 2026-09-26  
Source folder scanned: `app/`  
Postmortems read: 3 (PM-001, PM-002, PM-003)

---

## Summary Table

| Past incident | Pattern | New bugs found | File | Function | Fixed? | Test name(s) |
|---|---|---|---|---|---|---|
| PM-001 | missing-none-check | 3 | `app/users.py` | `get_user_profile` | Yes | `test_get_user_profile_missing_none_check` |
| PM-001 | missing-none-check | — | `app/bookings.py` | `get_booking_summary` | Yes | `test_get_booking_summary_missing_none_check` |
| PM-001 | missing-none-check | — | `app/rooms.py` | `get_room_details` | Yes | `test_get_room_details_unknown_room_missing_none_check`, `test_get_room_details_none_description` |
| PM-002 | http-no-timeout | 2 | `app/notifications.py` | `send_sms_notification` | Yes | `test_send_sms_notification_timeout`, `test_send_sms_notification_connection_error`, `test_send_sms_notification_has_timeout_kwarg` |
| PM-002 | http-no-timeout | — | `app/payments.py` | `process_payment` | Yes | `test_process_payment_timeout`, `test_process_payment_connection_error`, `test_process_payment_has_timeout_kwarg` |
| PM-003 | naive-aware-datetime | 2 | `app/bookings.py` | `create_booking` | Yes | `test_create_booking_naive_aware_datetime`, `test_create_booking_past_date_rejected` |
| PM-003 | naive-aware-datetime | — | `app/bookings.py` | `get_booking_duration` | Yes | `test_get_booking_duration_naive_aware_datetime` |

**Total new bugs found: 7 across 5 files.**

---

## Locations Checked and Judged Safe

### Pattern: missing-none-check

| File | Function | Reason judged safe |
|---|---|---|
| `app/users.py` | `update_user_profile` | Already fixed in PM-001 hotfix v1.14.3 — `if user is None: raise ValueError(...)` present. |
| `app/bookings.py` | `create_booking` | Both `user` and `room` results from `get_user()` / `get_room()` are guarded with `if … is None`. |
| `app/bookings.py` | `cancel_booking` | `if booking is None: raise ValueError(...)` guard present. |
| `app/bookings.py` | `get_booking_duration` | `if booking is None: raise ValueError(...)` guard present. |
| `app/bookings.py` | `is_booking_active` | `if booking is None: return False` guard present. |
| `app/bookings.py` | `confirm_booking` | `if booking is None: raise ValueError(...)` guard present. |
| `app/rooms.py` | `update_room_status` | `if room is None: raise ValueError(...)` guard present. |
| `app/rooms.py` | `calculate_room_cost` | `if room is None: raise ValueError(...)` guard present. |
| `app/payments.py` | `refund_payment` | `if payment is None: raise ValueError(...)` guard present. |
| `app/payments.py` | `get_payment_status` | Iterates `PAYMENTS.values()`; returns a safe sentinel dict when key not found. |

### Pattern: http-no-timeout

| File | Function | Reason judged safe |
|---|---|---|
| `app/notifications.py` | `send_email_notification` | Already fixed in PM-002 hotfix v1.17.1 — `timeout=5` and `try/except (Timeout, RequestException)` present. |
| `app/payments.py` | `refund_payment` | `timeout=8` and full `try/except (Timeout, RequestException)` present. |
| `app/bookings.py` | `cancel_booking` | `timeout=5` and broad `try/except Exception: pass` — intentional fire-and-forget; cancellation must not block on a notification failure. |

### Pattern: naive-aware-datetime

| File | Function | Reason judged safe |
|---|---|---|
| `app/bookings.py` | `is_booking_active` | Already fixed in PM-003 hotfix v1.18.2 — `.replace(tzinfo=timezone.utc)` on both `ci` and `co`. |
| `app/bookings.py` | `get_booking_summary` | Uses `_parse_date()` which returns a `date` object; arithmetic is between two `date` objects only — no aware datetime involved. |
| `app/payments.py` | `process_payment` | `datetime.now(timezone.utc).isoformat()` stored as string only — never compared with a naive datetime. |
| `app/notifications.py` | `send_email_notification`, `send_sms_notification` | `datetime.now(timezone.utc).isoformat()` stored as string; no comparisons. |

---

## Totals

| Metric | Value |
|---|---|
| Postmortems read | 3 |
| Patterns extracted | 3 |
| Python files scanned | 8 |
| Functions examined (total) | ~55 |
| Confirmed bugs found | 7 |
| Locations checked and ruled out as safe | 21 |
| Tests written | 13 |
| Tests failing before fixes | 13 / 13 |
| Tests passing after fixes | 13 / 13 |
| Guardrail issues flagged (before fixes) | 64 (7 confirmed + 57 false positives) |
| Guardrail issues flagged (after fixes) | 57 (0 confirmed + 57 false positives) |
| Confirmed guardrail issues after fixes | **0** |

---

## Step Durations

| Step | Start time | End time | Duration |
|---|---|---|---|
| Before Step 1 (project scan + postmortem reads) | 09:25:42 | 09:25:59 | ~17 s |
| Step 1 — Extract patterns, write reports/patterns.md | 09:25:59 | 09:27:19 | ~80 s |
| Step 2 — Hunt in parallel (3 subagents) | 09:27:19 | 09:28:51 | ~92 s |
| Step 3 — Write & validate failing tests | 09:28:51 | 09:29:38 | ~47 s |
| Step 4 — Build guardrails + run pre-fix | 09:29:38 | 09:31:14 | ~96 s |
| Checkpoint wait (human approval) | 09:31:14 | 09:35:20 | ~4 min 6 s |
| Step 5 — Apply fixes, rerun tests + guardrail | 09:35:20 | 09:36:15 | ~55 s |
| Step 6 — Write this report | 09:36:15 | 09:36:30 | ~15 s |
| **Total automated work (excl. approval wait)** | | | **~6 min 22 s** |
| **Total wall-clock (incl. approval wait)** | | | **~10 min 48 s** |

---

## What Would Have Happened

### Bug 1 — `get_user_profile` (missing-none-check, PM-001 pattern)

Any `GET /users/{unknown_id}/profile` request would have raised
`TypeError: 'NoneType' object is not subscriptable` and returned HTTP 500.
This is structurally identical to PM-001's `PATCH /users/{id}` crash: a TypeError
propagating unhandled to Flask's generic 500 handler. Given that PM-001 produced
1,247 failed requests and 12 customer complaints over 4 hours, a similar defect in the
profile endpoint — likely a higher-traffic read path — could have caused a larger or
longer incident, particularly if triggered by any feature using the profile summary
(e.g. a loyalty programme page).

### Bug 2 — `get_booking_summary` (missing-none-check, PM-001 pattern)

Any `GET /bookings/{unknown_id}/summary` request would crash with `TypeError`.
The summary endpoint is the canonical human-readable view of a booking, surfaced on
confirmation pages and the operations dashboard. A crash on this endpoint would break
booking confirmation UX and the internal dashboard simultaneously — the same
dashboard whose reliability problem was the core symptom of PM-003.

### Bug 3 — `get_room_details` (missing-none-check, PM-001 pattern)

Two live failure paths: (a) any request for an unknown room ID → HTTP 500; (b) any
request for room `r110` (whose `description` is `None`) → `AttributeError` and HTTP
500. Room `r110` exists in the production data store, so the second failure mode is a
guaranteed crash on a real room — reproducible on every request, not just for edge-
case inputs. This would have silently broken the room details page for a real room.

### Bug 4 — `send_sms_notification` (http-no-timeout, PM-002 pattern)

`send_sms_notification` is called for every payment receipt. With no `timeout=` and no
`try/except`, a gateway outage would block each Gunicorn worker for several minutes per
call — the same mechanism that caused the 23-minute SEV-1 outage in PM-002. Because
payment receipts follow bookings, a gateway outage during a busy check-in period would
exhaust workers within minutes and make the entire API unavailable. The impact would
be at least as severe as PM-002 (estimated £6,200 revenue at risk in that incident).

### Bug 5 — `process_payment` (http-no-timeout, PM-002 pattern)

`process_payment` is called on the critical booking creation path. With no timeout and
no exception handling, a payment gateway outage would block every booking attempt
indefinitely. Unlike the notification path (a side-effect), payment processing is
synchronous and mandatory — a blocked worker here means no new booking can complete.
This is the most severe of the seven bugs: a single payment gateway blip during a
busy period would take down the entire booking API. The financial and reputational
impact would significantly exceed PM-002.

### Bug 6 — `create_booking` (naive-aware-datetime, PM-003 pattern)

The check-in date validation (`booking_start < request_deadline`) would raise
`TypeError` on some environments and produce a silent wrong result on others.
On systems where Python's comparator raises, every `POST /bookings` request would
fail with HTTP 500 — blocking all new bookings. On systems where it silently returns
wrong results, past-date bookings might be accepted without error, corrupting the
booking calendar. PM-003's experience shows that silent wrong results persist
undetected for weeks.

### Bug 7 — `get_booking_duration` (naive-aware-datetime, PM-003 pattern)

`GET /bookings/{id}/duration` would raise `TypeError: can't subtract offset-naive and
offset-aware datetimes` for every request, returning HTTP 500. This endpoint is used
by front-desk staff to track how many nights a guest has been checked in. As in PM-003,
the crash would show up on the internal operations dashboard and cause the same class of
front-desk disruption that triggered the original incident report.

---

## Artefacts Created

| Artefact | Purpose |
|---|---|
| `reports/patterns.md` | 3 generalised bug patterns extracted from postmortems |
| `reports/findings.md` | Full audit: 7 confirmed bugs + 21 safe locations, with reasoning |
| `tests/test_confirmed_bugs.py` | 13 pytest tests (all failed before fixes, all pass after) |
| `guardrails/check_patterns.py` | AST-based static analyser for all 3 patterns |
| `guardrails/REVIEW_CHECKLIST.md` | PR review checklist — one section per postmortem |
| `reports/PREVENTION_REPORT.md` | This document |
