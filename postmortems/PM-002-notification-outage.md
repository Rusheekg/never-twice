# PM-002 — Notification Service Outage: Email Dispatch Hangs Under Gateway Failure

| Field | Value |
|---|---|
| **Incident ID** | PM-002 |
| **Date** | 2026-05-22 |
| **Severity** | SEV-1 |
| **Status** | Resolved |

---

## Summary

A planned maintenance window on the third-party notification gateway caused the
`send_email_notification()` function to hang indefinitely, exhausting all
available Gunicorn worker processes within 8 minutes. With no workers free to
accept new connections, the entire hotel booking API became unavailable. The root
cause was an outbound HTTP call to the gateway with no timeout and no exception
handling, meaning a slow or unreachable upstream service could silently stall
every worker thread. The incident lasted 23 minutes from first customer impact to
full service restoration.

---

## Customer Impact

- **Service unavailability:** 23 minutes (07:41 UTC – 08:04 UTC)
- **Affected users:** All active users — approximately 2,100 sessions were
  active at the time of the incident
- **Failed booking confirmations:** 87 booking requests returned 502 or timed out
  with no response
- **Failed payment acknowledgements:** 34 payment records were written but the
  associated email receipts were never queued
- **Revenue at risk:** Estimated £6,200 in in-flight booking transactions that
  required manual follow-up
- **Customer complaints received:** 41 (email and support chat)

---

## Detection

Detection was entirely reactive. No automated alert was configured for worker
saturation or response-time degradation on the notifications path.

At 08:01 UTC, a senior engineer noticed the booking service was returning no
response (connection reset) when attempting to test a feature unrelated to
notifications. They checked the Gunicorn process list and saw all 8 workers in
`T` (sleeping/blocked) state. Correlating this with an email from the
notification gateway provider — sent at 07:35 UTC, 6 minutes before the incident
began — confirmed the upstream maintenance window as the trigger.

---

## Timeline

| Time (UTC) | Event |
|---|---|
| 2026-05-22 07:35 | Notification gateway provider sends maintenance-window email to ops alias |
| 2026-05-22 07:41 | Gateway begins rejecting connections; first outbound email calls start hanging |
| 2026-05-22 07:49 | All 8 Gunicorn workers saturated; API stops accepting new requests |
| 2026-05-22 07:52 | First customer complaint received via support chat |
| 2026-05-22 08:01 | On-call engineer detects worker saturation during unrelated manual check |
| 2026-05-22 08:01 | Ops alias email from gateway provider is found and read |
| 2026-05-22 08:03 | Gunicorn restarted; workers freed immediately |
| 2026-05-22 08:04 | Service confirmed healthy; new requests accepted normally |
| 2026-05-22 08:06 | Hotfix branch opened to add timeout and error handling |
| 2026-05-22 09:47 | Hotfix v1.17.1 deployed to production |
| 2026-05-22 11:00 | Post-incident review meeting held |

---

## Root Cause

The `send_email_notification()` function made a `POST` request to the external
notification gateway using `requests.post()` with no `timeout` parameter and no
`try/except` block. Python's `requests` library defaults to waiting
indefinitely when no timeout is specified. When the gateway stopped accepting
connections during its maintenance window, each call to `requests.post()` blocked
the worker thread until the OS-level TCP timeout elapsed — a window of several
minutes per connection.

Because every new booking confirmation and payment receipt triggers a call to
this function, all 8 Gunicorn workers accumulated blocked threads within 8
minutes, rendering the entire API unresponsive.

Had a short timeout been set, the call would have raised
`requests.exceptions.Timeout` after a few seconds. Had a `try/except` been
present, that exception would have been caught and converted to a descriptive
`RuntimeError`, allowing the caller to return a graceful error response without
blocking the worker.

### Code before (prior to v1.17.1)

```python
def send_email_notification(user_id: str, subject: str, body: str) -> dict:
    payload = {
        "channel": "email",
        "recipient": user_id,
        "subject": subject,
        "body": body,
    }

    response = http.post(MOCK_NOTIFY_URL, json=payload)  # no timeout, no error handling
    gateway_data = response.json()

    if response.status_code != 200 or gateway_data.get("status") != "sent":
        raise RuntimeError(
            f"Notification failed: {gateway_data.get('message', 'unknown error')}"
        )
    ...
```

### Code after (hotfix v1.17.1)

```python
def send_email_notification(user_id: str, subject: str, body: str) -> dict:
    payload = {
        "channel": "email",
        "recipient": user_id,
        "subject": subject,
        "body": body,
    }

    try:
        response = http.post(MOCK_NOTIFY_URL, json=payload, timeout=5)
        gateway_data = response.json()
    except http.exceptions.Timeout:
        raise RuntimeError("Notification service timed out")
    except http.exceptions.RequestException as exc:
        raise RuntimeError(f"Notification service unreachable: {exc}")

    if response.status_code != 200 or gateway_data.get("status") != "sent":
        raise RuntimeError(
            f"Notification failed: {gateway_data.get('message', 'unknown error')}"
        )
    ...
```

---

## Fix Applied

Two changes were made in hotfix **v1.17.1**:

1. **Added `timeout=5`** to the `requests.post()` call so that any slow or
   unresponsive gateway response raises `requests.exceptions.Timeout` after
   5 seconds instead of blocking indefinitely.

2. **Wrapped the call in `try/except`** to catch both `Timeout` and the broader
   `RequestException` (covering connection errors, DNS failures, etc.) and
   re-raise them as `RuntimeError` with a descriptive message. This allows the
   caller to return a proper HTTP 502 to the client without stalling the worker.

---

## Lessons Learned

1. **All outbound HTTP calls must have an explicit timeout.** There is no
   meaningful scenario in which a production service should wait indefinitely for
   a third-party response. A 5-second timeout is a safe default for synchronous
   notification calls; background jobs may warrant a longer value.

2. **Worker saturation has no alert.** The incident persisted for over 20 minutes
   before being discovered manually. A metric tracking the ratio of active-to-
   available Gunicorn workers, with an alert at 80% utilisation, would have
   detected this within the first minute.

3. **Provider maintenance emails must reach on-call staff, not a shared alias.**
   The gateway provider sent notice 6 minutes before the window opened, but the
   email arrived at an ops alias nobody monitors in real time. Routing these
   emails to the on-call rotation or a monitored Slack channel would allow
   preventive action (e.g., temporarily disabling email dispatch).

4. **Notification failures should not cascade to booking failures.** Sending a
   confirmation email is a non-critical side-effect of a booking. The architecture
   should decouple them — for example, via an async queue — so that a gateway
   outage cannot take down the entire booking path.

---

## Action Items

| # | Action | Owner | Due | Status |
|---|---|---|---|---|
| 1 | Add Gunicorn worker utilisation metric and alert at 80% saturation | Platform | 2026-06-05 | ✅ Completed |
| 2 | Route all third-party provider maintenance emails to the on-call Slack channel | Ops | 2026-05-29 | ✅ Completed |
| 3 | Spike: evaluate async task queue (e.g. Celery + Redis) to decouple notifications from the request path | Backend Team | 2026-06-19 | ✅ Completed |
| 4 | Add `timeout` to all outbound `requests` calls and wrap in `try/except` as a mandatory code review gate | Engineering Lead | 2026-06-05 | ✅ Completed |
| 5 | Audit the codebase for any remaining outbound HTTP calls that lack a timeout or exception handling | Backend Team | 2026-06-26 | ❌ Not completed |
