# Never Twice — Extracted Patterns from Postmortems

Generated: 2026-09-26

---

## Pattern 1 — Missing None-Guard After dict.get()

| Field | Detail |
|---|---|
| **Incident ID** | PM-001 |
| **Pattern Name** | Missing None-Guard After dict.get() |
| **Severity of original incident** | SEV-2 |

### How to recognise it in code

A value is retrieved with `dict.get(key)` (or any lookup that can return `None`)
and the result is then used **without first checking whether it is `None`**.
Common manifestations:
- `result = store.get(id)` followed immediately by `result["field"]` or `result.method()`
- The None-check that existed in a previous version was removed during a refactor
- The function trusts that the caller always passes a valid key

### How to fix it correctly

Add an **explicit guard** immediately after the lookup:

```python
record = STORE.get(key)
if record is None:
    raise ValueError(f"Record {key!r} not found")
# safe to use record below
```

Raise a typed exception (`ValueError`, `KeyError`, or a domain-specific error)
with a descriptive message so that calling code can map it to the correct HTTP
status code without catching a generic `TypeError`.

### Already-fixed location

`app/users.py` → `update_user_profile()` (hotfix v1.14.3)

---

## Pattern 2 — Outbound HTTP Call Without Timeout or Error Handling

| Field | Detail |
|---|---|
| **Incident ID** | PM-002 |
| **Pattern Name** | Outbound HTTP Call Without Timeout or Error Handling |
| **Severity of original incident** | SEV-1 |

### How to recognise it in code

A call to `requests.get()` / `requests.post()` (or equivalent) that:
- **lacks a `timeout` parameter** — defaults to waiting indefinitely, so a slow
  upstream will block the worker thread for minutes
- **lacks a `try/except`** around `requests.exceptions.Timeout` and/or
  `requests.exceptions.RequestException` — so connection errors propagate as
  unhandled exceptions or silently crash the function

### How to fix it correctly

Always specify a `timeout` and wrap in `try/except`:

```python
try:
    response = requests.post(url, json=payload, timeout=5)
    data = response.json()
except requests.exceptions.Timeout:
    raise RuntimeError("External service timed out")
except requests.exceptions.RequestException as exc:
    raise RuntimeError(f"External service unreachable: {exc}")
```

Choose a timeout appropriate to the call's criticality; 5 seconds is a safe
default for synchronous notification calls.

### Already-fixed location

`app/notifications.py` → `send_email_notification()` (hotfix v1.17.1)

---

## Pattern 3 — Naive/Aware Datetime Mismatch in Comparisons

| Field | Detail |
|---|---|
| **Incident ID** | PM-003 |
| **Pattern Name** | Naive/Aware Datetime Mismatch in Comparisons |
| **Severity of original incident** | SEV-3 |

### How to recognise it in code

A `datetime` object produced by `datetime.now(timezone.utc)` (timezone-**aware**)
is compared or subtracted against a `datetime` produced by
`datetime.strptime(string, fmt)` (timezone-**naive**).  This either:
- raises `TypeError: can't compare offset-naive and offset-aware datetimes`
  (on some systems/Python versions), or
- silently returns a wrong result (on others)

Look for any arithmetic or comparison (`<`, `<=`, `>`, `>=`, `-`) that involves
both a `datetime.now(tz)` / `datetime(..., tzinfo=...)` value **and** a
`datetime.strptime(...)` value that has **not** been immediately followed by
`.replace(tzinfo=...)` or `.astimezone(...)`.

### How to fix it correctly

Attach `tzinfo` to every `strptime` result that will participate in
comparisons or arithmetic:

```python
dt = datetime.strptime(date_string, "%Y-%m-%d").replace(tzinfo=timezone.utc)
```

All datetime values in a comparison must share the same tzinfo.

### Already-fixed location

`app/bookings.py` → `is_booking_active()` (hotfix v1.18.2)
