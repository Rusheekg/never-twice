# Secret Bug List

This file is the answer key for the hotel booking API code-review exercise.
**Do not share this file with candidates.**

---

## 1. Hidden Bugs

### Bug A-1 — Type A: Missing None check
| Field | Value |
|-------|-------|
| **File** | `app/users.py` |
| **Function** | `get_user_profile()` |
| **Bug type** | Type A — missing None/empty check |
| **Description** | `USERS.get(user_id)` returns `None` when the user does not exist, but the function immediately dereferences the result (`user["name"]`, `user["loyalty_tier"]`) without checking for `None` first, raising a `TypeError`. |
| **Triggering input** | `get_user_profile("u999")` — any user_id that is not in `USERS` |

---

### Bug A-2 — Type A: Missing None check
| Field | Value |
|-------|-------|
| **File** | `app/rooms.py` |
| **Function** | `get_room_details()` |
| **Bug type** | Type A — missing None/empty check |
| **Description** | `room["description"]` is `None` for room `r110` (and any future room added without a description). Calling `.strip()` on `None` raises `AttributeError`. Additionally, the function does not guard against the room itself being absent (`ROOMS.get(room_id)` can return `None`). |
| **Triggering input** | `get_room_details("r110")` — room exists but has `description: None` |

---

### Bug A-3 — Type A: Missing None check
| Field | Value |
|-------|-------|
| **File** | `app/bookings.py` |
| **Function** | `get_booking_summary()` |
| **Bug type** | Type A — missing None/empty check |
| **Description** | `BOOKINGS.get(booking_id)` is never checked for `None`. If the booking does not exist the function immediately subscripts the result (`booking["user_id"]`), raising a `TypeError`. |
| **Triggering input** | `get_booking_summary("bk_nonexistent")` — any booking_id absent from `BOOKINGS` |

---

### Bug B-1 — Type B: Missing try/except and timeout
| Field | Value |
|-------|-------|
| **File** | `app/payments.py` |
| **Function** | `process_payment()` |
| **Bug type** | Type B — missing error handling on external HTTP call |
| **Description** | `http.post(MOCK_PAYMENT_URL, json=payload)` has no `timeout` argument and no `try/except`. If the mock service is down or slow, the call blocks indefinitely and raises `requests.exceptions.ConnectionError` or `requests.exceptions.Timeout`, both of which are unhandled and propagate as a 500. |
| **Triggering input** | Call `process_payment("bk001", "u001", 100.0)` while the mock service is not running, or hit the mock with `?slow=60` |

---

### Bug B-2 — Type B: Missing try/except and timeout
| Field | Value |
|-------|-------|
| **File** | `app/notifications.py` |
| **Function** | `send_sms_notification()` |
| **Bug type** | Type B — missing error handling on external HTTP call |
| **Description** | `http.post(MOCK_NOTIFY_URL, json=payload)` has no `timeout` argument and no `try/except`. Network errors or mock service unavailability will raise unhandled `requests` exceptions. Compare with the correctly handled `send_email_notification()` in the same file. |
| **Triggering input** | Call `send_sms_notification("u001", "Hello")` while the mock service is not running, or hit the mock with `?slow=60` |

---

### Bug C-1 — Type C: Timezone-naive / timezone-aware mixing
| Field | Value |
|-------|-------|
| **File** | `app/bookings.py` |
| **Function** | `create_booking()` |
| **Bug type** | Type C — mixing naive and aware datetimes |
| **Description** | `request_deadline = datetime.now(timezone.utc)` is timezone-aware, but `booking_start = datetime.strptime(check_in, "%Y-%m-%d")` is timezone-naive. The comparison `if booking_start < request_deadline` raises `TypeError: can't compare offset-naive and offset-aware datetimes`. |
| **Triggering input** | `create_booking("u001", "r101", "2025-09-01", "2025-09-03", 1)` — any call where the date is in the future triggers the comparison |

---

### Bug C-2 — Type C: Timezone-naive / timezone-aware mixing
| Field | Value |
|-------|-------|
| **File** | `app/bookings.py` |
| **Function** | `get_booking_duration()` |
| **Bug type** | Type C — mixing naive and aware datetimes |
| **Description** | `check_in_dt = datetime.strptime(...)` is timezone-naive; `now = datetime.now(timezone.utc)` is timezone-aware. Subtracting them (`now - check_in_dt`) raises `TypeError: can't subtract offset-naive and offset-aware datetimes`. |
| **Triggering input** | `get_booking_duration("bk001")` — any existing booking triggers the subtraction |

---

## 2. Already-Fixed Examples

### Fix for Type A — `update_user_profile()` in `app/users.py`
The function calls `USERS.get(user_id)` and **immediately checks `if user is None: raise ValueError(...)`** before accessing any field. This is the correct pattern for Type A.

### Fix for Type B — `send_email_notification()` in `app/notifications.py`
The `http.post(...)` call uses `timeout=5` and is wrapped in a `try/except` block that catches `requests.exceptions.Timeout` and `requests.exceptions.RequestException` separately, re-raising them as descriptive `RuntimeError`s. This is the correct pattern for Type B.

### Fix for Type C — `is_booking_active()` in `app/bookings.py`
Both `ci` and `co` are constructed with `.replace(tzinfo=timezone.utc)` so they are timezone-aware, and `now = datetime.now(timezone.utc)` is also aware. All three datetimes share the same timezone before comparison. This is the correct pattern for Type C.

---

## 3. Decoys

### Decoy 1 — `list_available_rooms()` in `app/rooms.py`
**Why it is safe:** The function filters `ROOMS.values()` directly using a list comprehension. `ROOMS` is a module-level dictionary that is always initialised and never `None`. The resulting `available` list may be empty but will never be `None`, so no `None`-dereference can occur.

### Decoy 2 — `get_payment_status()` in `app/payments.py`
**Why it is safe:** The function iterates over `PAYMENTS.values()` and returns a safe default dict `{"payment_id": None, "status": "not_found", ...}` when no match is found. There is no unguarded attribute access on a potentially-`None` value; every code path returns a valid dictionary.

### Decoy 3 — `cancel_booking()` in `app/bookings.py`
**Why it is safe:** The `http.post(...)` call to the notification service **is** wrapped in a `try/except Exception: pass` block, and the booking cancellation proceeds regardless of whether the notification succeeds. It deliberately swallows the error so a network failure cannot roll back the cancellation — this is an intentional design choice, not a bug.
