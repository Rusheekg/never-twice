# Postmortem Patterns

Extracted from all postmortems in `postmortems/`. TEMPLATE files skipped (none present).

---

## Pattern 1 — Missing None-check after dict.get()

| Field | Detail |
|---|---|
| **Incident ID** | PM-001 |
| **Pattern name** | missing-none-check |
| **How to recognise** | A variable is assigned from `<dict>.get(key)` (or any call that can return `None`), then the variable is subscripted, attribute-accessed, or otherwise used **without** a preceding `if <var> is None` / `if not <var>` guard. |
| **How to fix** | Immediately after the `.get()` call add `if <var> is None: raise ValueError(...)` (or return a sentinel / 404 response). Do **not** assume the key exists. |
| **Already-fixed location** | `app/users.py` → `update_user_profile()` — already has the `if user is None: raise ValueError(...)` guard added in hotfix v1.14.3. |

---

## Pattern 2 — Outbound HTTP call without timeout or exception handling

| Field | Detail |
|---|---|
| **Incident ID** | PM-002 |
| **Pattern name** | http-no-timeout |
| **How to recognise** | A call to `requests.post()` / `requests.get()` (or an aliased `http.post()` / `http.get()`) that **either** lacks a `timeout=` argument **or** is not wrapped in a `try/except` block that catches `requests.exceptions.Timeout` / `requests.exceptions.RequestException`. |
| **How to fix** | Add `timeout=<N>` to the call **and** wrap it in `try/except http.exceptions.Timeout` + `except http.exceptions.RequestException` that re-raises as `RuntimeError`. |
| **Already-fixed location** | `app/notifications.py` → `send_email_notification()` — already has `timeout=5` and the full `try/except` block added in hotfix v1.17.1. |

---

## Pattern 3 — Naive/aware datetime comparison

| Field | Detail |
|---|---|
| **Incident ID** | PM-003 |
| **Pattern name** | naive-aware-datetime |
| **How to recognise** | A `datetime.strptime(...)` result (which is always timezone-**naive**) is compared (`<=`, `<`, `>`, `-`) against a `datetime.now(timezone.utc)` result (which is timezone-**aware**) without a `.replace(tzinfo=timezone.utc)` or `.astimezone()` call in between. |
| **How to fix** | Immediately after every `datetime.strptime(...)` call, chain `.replace(tzinfo=timezone.utc)` before the datetime value participates in any comparison or arithmetic involving an aware datetime. |
| **Already-fixed location** | `app/bookings.py` → `is_booking_active()` — already has `.replace(tzinfo=timezone.utc)` on both `ci` and `co`, added in hotfix v1.18.2. |
