# PM-203: TypeError Crash When Fetching Unknown User ID

**Incident ID:** PM-203  
**Date:** 2026-01-30  
**Severity:** SEV-2  
**Status:** Resolved

---

## Summary

A downstream service sent a request containing a user ID that had been deleted from the system two weeks earlier. The call to `getUserById` in `users.js` returned `undefined` from `Array.prototype.find`, and the caller immediately tried to access a property on the result without checking for null. This produced an uncaught `TypeError: Cannot read properties of undefined`, which crashed the request handler and returned a 500 to the client.

---

## Customer Impact

The affected integration served loyalty-point balance lookups for approximately 90 customers whose accounts had been closed in a data-migration batch on 2026-01-16. Every balance lookup for those accounts resulted in a 500 error for a 14-day period before the issue was detected. No data was lost or corrupted; the impact was limited to failed read requests.

---

## Detection

Detected on 2026-01-30 by a weekly error-rate review. The Kibana dashboard showed a cluster of `TypeError` stack traces all originating from the same code path. The pattern was matched to the January migration batch by timestamp correlation.

---

## Timeline

| Time (UTC) | Event |
|---|---|
| 2026-01-16 09:00 | Data-migration batch deletes 90 closed accounts |
| 2026-01-16 09:45 | Loyalty service begins sending requests for deleted IDs |
| 2026-01-30 10:15 | Weekly error review flags the TypeError cluster |
| 2026-01-30 11:00 | Root cause identified: missing null check in `getUserById` |
| 2026-01-30 11:22 | Fix deployed |
| 2026-01-30 11:35 | Verified: unknown IDs now return `null` gracefully |

---

## Root Cause

`getUserById` in `users.js` called `users.find(u => u.id === userId)`. When the ID did not exist, `find` returned `undefined`. The function previously returned this raw `undefined` directly to callers without any guard. Callers that accessed properties such as `.email` or `.role` on the result immediately threw a `TypeError`.

The fix added an explicit null check: if `find` returns a falsy value, the function now returns `null`, and the caller can handle the missing-user case gracefully.

---

## Code Before

```js
function getUserById(userId) {
  const user = users.find(u => u.id === userId);
  return Object.assign({}, user);
}
```

---

## Code After

```js
function getUserById(userId) {
  const user = users.find(u => u.id === userId);
  if (!user) {
    return null;
  }
  return Object.assign({}, user);
}
```

---

## Fix Applied

Added a `if (!user) return null;` guard immediately after the `find` call. All callers were updated to handle a `null` return value as a "not found" signal instead of assuming the result is always a valid object.

---

## Lessons Learned

- `Array.prototype.find` returns `undefined` for no-match, not `null`; callers must always handle this case.
- Deleted or soft-deleted records must be treated as potentially present in external service requests long after removal.
- `Object.assign({}, undefined)` does not throw but returns `{}`, masking the missing record instead of surfacing the error — an explicit null guard is required.

---

## Action Items

| # | Item | Owner | Status |
|---|---|---|---|
| 1 | Update all `getUserById` callers to handle `null` | Backend team | Completed |
| 2 | Add a TypeScript strict-null-checks migration task to the backlog | Platform team | Completed |
| 3 | Audit the codebase for similar patterns | Backend team | **NOT completed** |
