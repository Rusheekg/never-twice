# Never Twice — Pattern Catalogue

Generated: 2026-09-27

---

## PM-201 — Loose Equality on ID Comparison

| Field | Value |
|---|---|
| **Incident ID** | PM-201 |
| **Pattern name** | `loose-id-comparison` |
| **Severity** | SEV-2 |

### How to recognise it in code
Any comparison of an ID value using `==` or `!=` instead of `===` or `!==`.
IDs that cross an HTTP boundary arrive as strings; comparing them against
in-memory numeric IDs with loose operators silently passes type-mismatches.
Look for: `x == y`, `x != y`, `x == productId`, `x != userId` etc. where
either operand is named `id`, `userId`, `productId`, `orderId`, etc.

### How to fix it correctly
Replace `==` with `===` and `!=` with `!==`.  
If the incoming value may be a string, coerce it first:
`Number(userId)` (for numeric IDs) or `.toString()` (for string IDs),
then use strict equality.

### Already-fixed location (skip in Step 2)
`cancelOrder` in `src/orders.js` — **NOT yet fixed** (action item 3 was never completed).  
No location is excluded; all occurrences are in scope.

---

## PM-202 — Unawaited Async Notify Call (Silent Fire-and-Forget)

| Field | Value |
|---|---|
| **Incident ID** | PM-202 |
| **Pattern name** | `unawaited-notify-call` |
| **Severity** | SEV-1 |

### How to recognise it in code
A call to any `notify.*` async function that is **not** preceded by `await`
and is **not** wrapped in a `.then()` / `.catch()` error handler or a
`try { await ... } catch` block. A bare call like
`notify.sendXxx(...)` in an `async` function is the footprint.
An explicit `.catch(() => {})` attached directly to the call is an
intentional fire-and-forget and is NOT the pattern.

### How to fix it correctly
Wrap the call in a try/catch and await it:
```js
try {
  await notify.sendXxx(...);
} catch (err) {
  return { success: false, reason: 'notification_failed' };
}
```

### Already-fixed location (skip in Step 2)
`checkoutCart` in `src/cart.js` — already has `await` + try/catch.  
`shipOrder` in `src/orders.js` — intentionally fire-and-forget with explicit `.catch(() => {})`, not silent.

---

## PM-203 — Missing Null Guard After `.find()` Returns `undefined`

| Field | Value |
|---|---|
| **Incident ID** | PM-203 |
| **Pattern name** | `find-no-null-guard` |
| **Severity** | SEV-2 |

### How to recognise it in code
A call to `Array.prototype.find(...)` whose return value is used
immediately (property access, passed to another function) without first
checking that the result is truthy (i.e., no `if (!x)` / `if (x == null)`
guard between the `find` call and the first use of its result).
`Object.assign({}, undefined)` is a masked version of the same bug.

### How to fix it correctly
Add a null guard immediately after `find`:
```js
if (!result) {
  return null; // or return { success: false, reason: 'not_found' }
}
```

### Already-fixed location (skip in Step 2)
`getUserById` in `src/users.js` — already has `if (!user) return null`.  
`getUserByEmail` in `src/users.js` — already has `if (!user) return null`.
