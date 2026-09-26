# Code Review Checklist — Postmortem-Derived Guards

Use this checklist on every pull request that touches Python source files.
Each item links back to the incident that motivated it.

---

## PM-001 · Missing None-check after dict.get()

> **Incident:** `update_user_profile()` dropped its `None` guard in a refactor,
> causing `TypeError: 'NoneType' object is not subscriptable` and 1,247 HTTP 500s
> over 4 hours.  
> **Postmortem:** [postmortems/PM-001-user-profile-crash.md](../postmortems/PM-001-user-profile-crash.md)

- [ ] Every variable assigned from `<dict>.get(key)` (or any function that can return `None`) has an explicit `if <var> is None:` guard **before** the variable is subscripted, attribute-accessed, or passed to code that assumes it is not `None`.
- [ ] The guard raises `ValueError` (or returns a 404 sentinel) — it does **not** silently continue with a `None` value.
- [ ] Refactors that restructure validation or lookup logic are reviewed specifically for accidental removal of existing `None` guards.

---

## PM-002 · Outbound HTTP call without timeout or exception handling

> **Incident:** `send_email_notification()` called `requests.post()` with no
> `timeout=`, causing all Gunicorn workers to hang during a gateway maintenance
> window and taking the entire API down for 23 minutes (SEV-1).  
> **Postmortem:** [postmortems/PM-002-notification-outage.md](../postmortems/PM-002-notification-outage.md)

- [ ] Every outbound `requests.post()` / `requests.get()` / `http.post()` etc. includes an explicit `timeout=<N>` argument.
- [ ] Every outbound HTTP call is wrapped in a `try/except` that catches at minimum `requests.exceptions.Timeout` and `requests.exceptions.RequestException`.
- [ ] The `except` block re-raises as `RuntimeError` (or a domain-specific exception) — it does **not** silently swallow the error unless the call is explicitly fire-and-forget and the code comment says so.
- [ ] Non-critical side-effect calls (e.g. sending a notification after a cancellation) that intentionally swallow errors use `except Exception: pass` with a comment explaining the intent.

---

## PM-003 · Naive/aware datetime comparison or arithmetic

> **Incident:** `is_booking_active()` mixed a timezone-naive `datetime.strptime()`
> result with a timezone-aware `datetime.now(timezone.utc)` result.  On production
> this produced a silent wrong result for 6 weeks; locally it raised
> `TypeError: can't compare offset-naive and offset-aware datetimes`.  
> **Postmortem:** [postmortems/PM-003-booking-timezone-error.md](../postmortems/PM-003-booking-timezone-error.md)

- [ ] Every `datetime.strptime(...)` result that will participate in a comparison (`<`, `<=`, `>`, `>=`) or arithmetic (`-`) with another datetime is immediately chained with `.replace(tzinfo=timezone.utc)` (or `.astimezone()`).
- [ ] `datetime.strptime(...)` results that are converted to `date` objects via `.date()` are exempt — `date` comparisons are always naive-vs-naive.
- [ ] New functions that work with datetime ranges include at least one test where the current time falls **inside** the range and one where it falls **outside**, verified with timezone-aware inputs.
- [ ] All datetime objects stored in or retrieved from the data layer carry explicit UTC `tzinfo`.

---

## Automated check

Run before merging any Python PR:

```bash
python guardrails/check_patterns.py app/
```

Exit code 0 = clean.  Exit code 1 = issues must be resolved before merge.
