# PM-201: Order Cancellation Rejected for Valid User Due to Type Coercion

**Incident ID:** PM-201  
**Date:** 2026-03-14  
**Severity:** SEV-2  
**Status:** Resolved

---

## Summary

Customers were unable to cancel their own orders when the user ID was sourced from a URL path parameter or query string. The cancellation endpoint returned `unauthorized` for requests that should have been permitted, causing customers to contact support to process legitimate cancellations manually.

---

## Customer Impact

Approximately 340 cancellation attempts failed over a 6-hour window on 2026-03-14. All affected customers received an incorrect `unauthorized` response. Estimated 40 support tickets were opened as a direct result. No orders were incorrectly cancelled for other users.

---

## Detection

Detected by on-call engineer via a spike in support tickets reporting "I can't cancel my order." A manual test with `userId = "2"` (string) against an order owned by user `2` (number) reproduced the error immediately.

---

## Timeline

| Time (UTC) | Event |
|---|---|
| 07:42 | First support ticket received |
| 08:15 | Second batch of tickets flagged by support team; escalated to engineering |
| 08:31 | On-call engineer reproduces the issue in staging |
| 08:47 | Root cause identified in `cancelOrder` |
| 09:05 | Fix deployed to production |
| 09:12 | Verified: cancellations succeeding normally |

---

## Root Cause

In `orders.js`, the `cancelOrder` function compared `order.userId` (a `Number`) against the `userId` parameter using the `!=` operator. When `userId` arrived as a string (e.g. `"2"` from a parsed request path), the loose inequality evaluated as `true` — the string `"2"` is not strictly equal to the number `2` — causing every request to be rejected as unauthorized.

---

## Code Before

```js
if (order.userId != userId) {
  return { success: false, reason: 'unauthorized' };
}
```

---

## Code After

```js
if (order.userId !== Number(userId)) {
  return { success: false, reason: 'unauthorized' };
}
```

---

## Fix Applied

Replaced `!=` with `!==` and added an explicit `Number()` coercion on the incoming parameter so that the comparison is always between two numbers regardless of the input type.

---

## Lessons Learned

- IDs crossing an HTTP boundary arrive as strings; comparisons against in-memory numeric IDs must account for this.
- Loose equality operators (`==` / `!=`) can silently pass through type mismatches that strict operators would catch.
- Staging tests used numeric literals directly, masking the string-vs-number mismatch.

---

## Action Items

| # | Item | Owner | Status |
|---|---|---|---|
| 1 | Add a test case for `cancelOrder` with a string userId | Backend team | Completed |
| 2 | Enable ESLint `eqeqeq` rule to disallow `==` / `!=` in the project | Platform team | Completed |
| 3 | Audit the codebase for similar patterns | Backend team | **NOT completed** |
