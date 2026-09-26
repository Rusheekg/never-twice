# Bug Hunt Findings

Scanned: `app/` — all 8 Python files, every function.
Patterns applied: 3 (from PM-001, PM-002, PM-003).
Already-fixed locations skipped as documented in `reports/patterns.md`.

---

## Confirmed Bugs

| # | File | Function | Pattern | Why it is risky |
|---|---|---|---|---|
| 1 | `app/users.py` | `get_user_profile` | missing-none-check | `user = USERS.get(user_id)` is not guarded before `user["name"].title()` and `user["loyalty_tier"].upper()`. Any request for an unknown `user_id` raises `TypeError: 'NoneType' object is not subscriptable`, propagating as a 500. |
| 2 | `app/bookings.py` | `get_booking_summary` | missing-none-check | `booking = BOOKINGS.get(booking_id)` is not guarded before `booking["user_id"]`, `booking["room_id"]`, and `booking["check_out"]`. A missing `booking_id` crashes with `TypeError`, returning a 500. |
| 3 | `app/rooms.py` | `get_room_details` | missing-none-check | `room = ROOMS.get(room_id)` is not guarded before `room["description"].strip()`. **Two failure modes:** (a) unknown `room_id` → `room` is `None` → `TypeError`; (b) valid room whose `description` field is `None` (e.g. room `r110`) → `AttributeError: 'NoneType' object has no attribute 'strip'`. |
| 4 | `app/notifications.py` | `send_sms_notification` | http-no-timeout | `http.post(MOCK_NOTIFY_URL, json=payload)` has no `timeout=` argument and is not wrapped in `try/except`. A slow or unreachable notification gateway will block the worker indefinitely — the exact condition that caused the SEV-1 outage (PM-002). |
| 5 | `app/payments.py` | `process_payment` | http-no-timeout | `http.post(MOCK_PAYMENT_URL, json=payload)` has no `timeout=` argument and is not wrapped in `try/except`. A slow or unreachable payment gateway will block every worker thread; because every booking triggers a payment call, worker saturation follows immediately — worse impact than PM-002. |
| 6 | `app/bookings.py` | `create_booking` | naive-aware-datetime | `booking_start = datetime.strptime(check_in, "%Y-%m-%d")` (naive) is compared with `request_deadline = datetime.now(timezone.utc)` (aware) using `<`. Raises `TypeError` on some Python/OS combinations; returns silently wrong result on others (check-in validation bypassed or incorrectly rejected). |
| 7 | `app/bookings.py` | `get_booking_duration` | naive-aware-datetime | `check_in_dt = datetime.strptime(booking["check_in"], "%Y-%m-%d")` (naive) is subtracted from `now = datetime.now(timezone.utc)` (aware). Raises `TypeError: can't subtract offset-naive and offset-aware datetimes`, crashing the duration endpoint. |

---

## Checked and Ruled Out as Safe

### Pattern: missing-none-check

| File | Function | Reason |
|---|---|---|
| `app/users.py` | `get_user` | Raw `USERS.get()` return — no usage of the result in this function. |
| `app/users.py` | `update_user_profile` | **Already fixed** (PM-001 hotfix v1.14.3): `if user is None: raise ValueError(...)` guard present. |
| `app/users.py` | `create_user` | Uses `data.get(field)` on caller-supplied input with explicit defaults; no store lookup. |
| `app/users.py` | `list_users` | Iterates `USERS.values()`; no `.get()` on individual records. |
| `app/bookings.py` | `create_booking` | `user` and `room` are both guarded with `if … is None: raise ValueError(...)` before use. |
| `app/bookings.py` | `get_booking` | Raw return; no usage inside this function. |
| `app/bookings.py` | `cancel_booking` | `if booking is None: raise ValueError(...)` guard present. |
| `app/bookings.py` | `get_booking_duration` | `if booking is None: raise ValueError(...)` guard present. |
| `app/bookings.py` | `is_booking_active` | `if booking is None: return False` guard present. |
| `app/bookings.py` | `confirm_booking` | `if booking is None: raise ValueError(...)` guard present. |
| `app/bookings.py` | `list_bookings_for_user` | Iterates `BOOKINGS.values()`; no single-record `.get()`. |
| `app/rooms.py` | `get_room` | Raw return; no usage inside this function. |
| `app/rooms.py` | `list_available_rooms` | Iterates `ROOMS.values()`; no single-record `.get()`. |
| `app/rooms.py` | `update_room_status` | `if room is None: raise ValueError(...)` guard present. |
| `app/rooms.py` | `calculate_room_cost` | `if room is None: raise ValueError(...)` guard present. |
| `app/rooms.py` | `search_rooms` | Iterates `ROOMS.values()`; no single-record `.get()`. |
| `app/payments.py` | `get_payment` | Raw return; no usage inside this function. |
| `app/payments.py` | `get_payment_status` | Iterates `PAYMENTS.values()`; returns a safe sentinel dict when not found. |
| `app/payments.py` | `refund_payment` | `if payment is None: raise ValueError(...)` guard present. |
| `app/payments.py` | `list_payments_for_user` | Iterates `PAYMENTS.values()`; no single-record `.get()`. |
| `app/notifications.py` | all functions | No lookups of user/booking/payment records by key. |
| `app/main.py` | all functions | No data-store lookups. |
| `app/mock_services.py` | all functions | No data-store lookups (uses `request.get_json()` / `data.get()` on request input). |

### Pattern: http-no-timeout

| File | Function | Reason |
|---|---|---|
| `app/notifications.py` | `send_email_notification` | **Already fixed** (PM-002 hotfix v1.17.1): `timeout=5` and full `try/except (Timeout, RequestException)` present. |
| `app/payments.py` | `refund_payment` | Has `timeout=8` and full `try/except (Timeout, RequestException)`. Safe. |
| `app/bookings.py` | `cancel_booking` | Has `timeout=5` and broad `try/except Exception` with explicit `pass`. Intentional fire-and-forget for non-critical cancellation notification. Safe. |
| All other functions | — | No outbound `requests` / `http` calls. |

### Pattern: naive-aware-datetime

| File | Function | Reason |
|---|---|---|
| `app/bookings.py` | `is_booking_active` | **Already fixed** (PM-003 hotfix v1.18.2): both `ci` and `co` have `.replace(tzinfo=timezone.utc)` applied before comparison. |
| `app/bookings.py` | `get_booking_summary` | Uses `_parse_date()` which returns a `date` object, not a `datetime`. Arithmetic is between two `date` objects only — no aware datetime involved. |
| `app/bookings.py` | `_parse_date` | Returns `date` (not `datetime`); never compared against an aware datetime. |
| `app/payments.py` | `process_payment` | `datetime.now(timezone.utc).isoformat()` is stored as a string; never compared with a naive datetime. |
| `app/notifications.py` | `send_email_notification`, `send_sms_notification` | `datetime.now(timezone.utc).isoformat()` stored as a string only. No comparisons. |
| All other functions | — | No datetime operations. |
