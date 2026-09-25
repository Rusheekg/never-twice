# Never Twice — Bug Hunt Findings

Generated: 2026-09-26
Patterns applied: 3 (from PM-001, PM-002, PM-003)
Files reviewed: app/users.py, app/bookings.py, app/payments.py, app/notifications.py, app/rooms.py

---

## Confirmed Bugs

### Bug 1 — Missing None-Guard After dict.get()
| Field | Detail |
|---|---|
| **File** | `app/users.py` |
| **Function** | `get_user_profile()` |
| **Pattern** | PM-001: Missing None-Guard After dict.get() |
| **Why risky** | `user = USERS.get(user_id)` returns `None` for unknown user IDs. The function immediately accesses `user["name"]`, `user["loyalty_tier"]`, and `user["email"]` without any None check. Any call with an unknown `user_id` raises `TypeError: 'NoneType' object is not subscriptable`, which propagates to Flask's 500 handler — the same crash mode as PM-001. |

---

### Bug 2 — Missing None-Guard After dict.get()
| Field | Detail |
|---|---|
| **File** | `app/bookings.py` |
| **Function** | `get_booking_summary()` |
| **Pattern** | PM-001: Missing None-Guard After dict.get() |
| **Why risky** | `booking = BOOKINGS.get(booking_id)` returns `None` for unknown booking IDs. The function immediately accesses `booking["user_id"]`, `booking["room_id"]`, `booking["check_out"]`, `booking["check_in"]`, `booking["total_cost"]`, and `booking["status"]` without any None check. Results in an unhandled `TypeError` → HTTP 500. |

---

### Bug 3 — Missing None-Guard After dict.get() + None Field Value
| Field | Detail |
|---|---|
| **File** | `app/rooms.py` |
| **Function** | `get_room_details()` |
| **Pattern** | PM-001: Missing None-Guard After dict.get() |
| **Why risky** | Two sub-issues: (a) `room = ROOMS.get(room_id)` returns `None` for unknown room IDs, but the function then calls `room["description"].strip()` without a None guard on `room` itself. (b) Even for valid rooms, `room["description"]` is `None` for room `r110` (the maintenance room), so `None.strip()` raises `AttributeError` regardless of whether the room exists. Both paths result in HTTP 500. |

---

### Bug 4 — Outbound HTTP Call Without Timeout or Error Handling
| Field | Detail |
|---|---|
| **File** | `app/notifications.py` |
| **Function** | `send_sms_notification()` |
| **Pattern** | PM-002: Outbound HTTP Call Without Timeout or Error Handling |
| **Why risky** | `http.post(MOCK_NOTIFY_URL, json=payload)` has no `timeout` parameter and is not wrapped in any `try/except`. If the notification gateway is slow or unreachable, this call blocks the worker thread indefinitely — exactly the SEV-1 failure mode from PM-002. Every SMS notification (e.g. payment receipts via `notify_payment_received`) inherits this vulnerability. |

---

### Bug 5 — Outbound HTTP Call Without Timeout or Error Handling
| Field | Detail |
|---|---|
| **File** | `app/payments.py` |
| **Function** | `process_payment()` |
| **Pattern** | PM-002: Outbound HTTP Call Without Timeout or Error Handling |
| **Why risky** | `http.post(MOCK_PAYMENT_URL, json=payload)` has no `timeout` parameter and is not wrapped in any `try/except`. Payment processing is the most critical path in the application. A slow or unavailable payment gateway will block all Gunicorn workers within minutes, taking down the entire API. |

---

### Bug 6 — Naive/Aware Datetime Mismatch
| Field | Detail |
|---|---|
| **File** | `app/bookings.py` |
| **Function** | `create_booking()` |
| **Pattern** | PM-003: Naive/Aware Datetime Mismatch in Comparisons |
| **Why risky** | Line 68: `request_deadline = datetime.now(timezone.utc)` is timezone-**aware**. Line 69: `booking_start = datetime.strptime(check_in, "%Y-%m-%d")` is timezone-**naive**. Line 71: `if booking_start < request_deadline:` compares them directly. On Python 3.9 this raises `TypeError: can't compare offset-naive and offset-aware datetimes`, crashing every booking creation attempt. |

---

### Bug 7 — Naive/Aware Datetime Mismatch
| Field | Detail |
|---|---|
| **File** | `app/bookings.py` |
| **Function** | `get_booking_duration()` |
| **Pattern** | PM-003: Naive/Aware Datetime Mismatch in Comparisons |
| **Why risky** | Line 162: `check_in_dt = datetime.strptime(...)` is timezone-**naive**. Line 163: `now = datetime.now(timezone.utc)` is timezone-**aware**. Line 165: `elapsed = now - check_in_dt` subtracts aware from naive. Raises `TypeError: can't subtract offset-naive and offset-aware datetimes` on every call. |

---

## Checked and Ruled Out as Safe

| File | Function | Reason |
|---|---|---|
| `app/users.py` | `get_user()` | Returns `USERS.get()` result directly; the route handler checks for None before use. |
| `app/users.py` | `update_user_profile()` | Has explicit `if user is None: raise ValueError` guard — the already-fixed location. |
| `app/users.py` | `create_user()` | No external store lookup; uses `data.get()` with safe defaults. |
| `app/users.py` | `list_users()` | Returns all values; no single-key lookup. |
| `app/bookings.py` | `get_booking()` | Returns `BOOKINGS.get()` directly; route handler checks None. |
| `app/bookings.py` | `create_booking()` | Checks `user is None` and `room is None` explicitly. (Has datetime bug tracked above.) |
| `app/bookings.py` | `cancel_booking()` | Has `if booking is None: raise ValueError` guard. HTTP call has `timeout=5` and errors are intentionally swallowed. |
| `app/bookings.py` | `get_booking_duration()` | Has `if booking is None: raise ValueError` guard. (Has datetime bug tracked above.) |
| `app/bookings.py` | `is_booking_active()` | Already fixed in PM-003 hotfix; both `strptime` results have `.replace(tzinfo=timezone.utc)`. |
| `app/bookings.py` | `confirm_booking()` | Has `if booking is None: raise ValueError` guard. |
| `app/bookings.py` | `list_bookings_for_user()` | Iterates values; no single-key lookup. |
| `app/rooms.py` | `get_room()` | Returns `ROOMS.get()` directly; route handler checks None. |
| `app/rooms.py` | `list_available_rooms()` | Filters `ROOMS.values()`; no single-key lookup. |
| `app/rooms.py` | `update_room_status()` | Has `if room is None: raise ValueError` guard. |
| `app/rooms.py` | `calculate_room_cost()` | Has `if room is None: raise ValueError` guard. |
| `app/rooms.py` | `search_rooms()` | Filters `ROOMS.values()` with criteria; no single-key lookup. |
| `app/notifications.py` | `send_email_notification()` | Already fixed in PM-002 hotfix; has `timeout=5` and `try/except`. |
| `app/notifications.py` | `notify_booking_confirmed()` | Delegates to fixed `send_email_notification()`. |
| `app/notifications.py` | `notify_payment_received()` | Delegates to `send_sms_notification()` — flagged as Bug 4 above. |
| `app/notifications.py` | `get_notification_log()` | Iterates `NOTIFICATIONS.values()`; no single-key lookup. |
| `app/payments.py` | `get_payment()` | Returns `PAYMENTS.get()` directly; route handler checks None. |
| `app/payments.py` | `get_payment_status()` | Iterates `PAYMENTS.values()`; returns safe default dict if not found. |
| `app/payments.py` | `refund_payment()` | Has `if payment is None: raise ValueError` guard; HTTP call has `timeout=8` and `try/except`. |
| `app/payments.py` | `list_payments_for_user()` | Iterates values; no single-key lookup. |
