# PM-202: Order Confirmation Reported as Success Despite Notification Failure

**Incident ID:** PM-202  
**Date:** 2026-05-22  
**Severity:** SEV-1  
**Status:** Resolved

---

## Summary

During a partial outage of the notification service, customers who placed orders received a successful order response from the API, but never received a confirmation email. Orders were recorded in the system as `confirmed` even though the notification step had thrown an error. This led to customer confusion, duplicate orders, and a surge in support contacts asking "Did my order go through?"

---

## Customer Impact

Approximately 1,200 orders placed during a 4-hour window on 2026-05-22 were confirmed without any email notification being sent. Of these, an estimated 180 customers placed duplicate orders believing the first had failed. Refunds and order consolidations were processed manually over the following 48 hours at an estimated cost of $14,000 in staff time and refund overhead.

---

## Detection

Detected by the on-call SRE at 11:03 UTC when the notification service PagerDuty alert fired. Cross-referencing order creation logs against notification delivery logs revealed the discrepancy. Customers had also begun opening support tickets at scale by 11:15.

---

## Timeline

| Time (UTC) | Event |
|---|---|
| 10:47 | Notification service begins returning errors (upstream SMTP provider issue) |
| 10:51 | First orders placed without confirmation email |
| 11:03 | SRE paged by notification service alert |
| 11:18 | Engineering confirms orders are marked `confirmed` despite notification errors |
| 11:32 | Root cause identified in `checkoutCart` in `cart.js` |
| 11:49 | Fix deployed; `checkoutCart` now awaits the notification call |
| 12:01 | Notification service recovers; all subsequent orders confirmed correctly |
| 12:30 | Duplicate orders identified and manual remediation begins |

---

## Root Cause

In `cart.js`, `checkoutCart` called `notify.sendCartCheckoutReminder` without `await`. Because the call was not awaited, any rejection thrown by the notification service was silently lost. The function continued to the success return path regardless of whether the notification had been sent, resulting in the caller receiving `{ success: true }` even when the underlying async operation failed.

---

## Code Before

```js
notify.sendCartCheckoutReminder(userId, total);
return { success: true, total };
```

---

## Code After

```js
try {
  await notify.sendCartCheckoutReminder(userId, total);
} catch (err) {
  return { success: false, reason: 'notification_failed' };
}
return { success: true, total };
```

---

## Fix Applied

Added `await` to the `notify.sendCartCheckoutReminder` call inside `checkoutCart` and wrapped it in a `try/catch` block so that a notification failure propagates as a failure response rather than being silently swallowed.

---

## Lessons Learned

- Unhandled promise rejections can produce misleading success responses that are invisible in logs if Node's `unhandledRejection` event is not monitored.
- Checkout flows that depend on external services must treat notification failure as a first-class error, not a fire-and-forget side effect.
- Code review should flag every `async` function call to verify it is either awaited or explicitly handled.

---

## Action Items

| # | Item | Owner | Status |
|---|---|---|---|
| 1 | Enable Node.js `--unhandled-rejections=throw` in production | Platform team | Completed |
| 2 | Add integration test for `checkoutCart` with a failing notify stub | Backend team | Completed |
| 3 | Audit the codebase for similar patterns | Backend team | **NOT completed** |
