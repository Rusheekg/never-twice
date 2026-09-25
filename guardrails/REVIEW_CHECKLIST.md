# Code Review Checklist — Bug Prevention Guardrails

Derived from past incidents. Each item must be verified for every pull request
that touches the relevant code paths.

---

## PM-001 — Missing None-Guard After dict.get()
*Postmortem: [PM-001-user-profile-crash.md](../postmortems/PM-001-user-profile-crash.md)*

- [ ] Every `dict.get()` / `STORE.get()` call whose return value is subsequently
      subscripted or attribute-accessed has an explicit `if result is None:` guard
      **immediately after** the lookup.
- [ ] The guard raises a typed exception (`ValueError`, `KeyError`, or a domain
      error) with a descriptive message so callers can map it to the correct HTTP
      status code.
- [ ] Refactors that restructure validation logic have been checked to confirm no
      existing None-guard was accidentally removed.
- [ ] New lookup functions that return `None` on miss have their callers audited to
      ensure all call sites handle the `None` case.

---

## PM-002 — Outbound HTTP Call Without Timeout or Error Handling
*Postmortem: [PM-002-notification-outage.md](../postmortems/PM-002-notification-outage.md)*

- [ ] Every `requests.get()` / `requests.post()` (or equivalent) call includes an
      explicit `timeout=` parameter (5 seconds is a safe default for synchronous
      calls; document the chosen value with a comment if it differs).
- [ ] Every outbound HTTP call is wrapped in `try/except` that catches at minimum
      `requests.exceptions.Timeout` and `requests.exceptions.RequestException`,
      and re-raises them as a descriptive `RuntimeError`.
- [ ] Non-critical notifications (e.g. cancellation emails) use `except Exception:
      pass` with a comment explaining the intentional swallow, so reviewers can
      distinguish deliberate silence from a forgotten handler.
- [ ] The PR description confirms that no new `requests.` call was added without
      both a timeout and error handling.

---

## PM-003 — Naive/Aware Datetime Mismatch
*Postmortem: [PM-003-booking-timezone-error.md](../postmortems/PM-003-booking-timezone-error.md)*

- [ ] Every `datetime.strptime()` call that will participate in a comparison
      (`<`, `<=`, `>`, `>=`) or arithmetic (`-`) with another datetime is
      immediately chained with `.replace(tzinfo=timezone.utc)` or
      `.astimezone(timezone.utc)`.
- [ ] All three operands in a datetime comparison share the same `tzinfo`
      (all aware, all UTC).
- [ ] No new datetime object is stored in or retrieved from the data layer without
      explicit UTC tzinfo.
- [ ] Code paths that return a boolean from a datetime comparison have at least one
      test that exercises both the truthy and falsy branch with timezone-aware input.
