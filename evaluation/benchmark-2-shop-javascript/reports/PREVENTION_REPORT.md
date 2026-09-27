# Never Twice — Prevention Report

**Project:** shop-js  
**Source folder:** `src/`  
**Postmortems:** `postmortems/`  
**Date:** 2026-09-27  
**Node version:** 24.14.1  
**Test framework:** Jest 29.7.0 (`npx jest`)

---

## Summary Table

| Past Incident | Pattern | New Bug Found | File | Function | Fixed | Test Name(s) |
|---|---|---|---|---|---|---|
| PM-201 | loose-id-comparison | Yes | `src/cart.js` | `addToCart` | ✅ Yes | `test_bug_addToCart_string_productId_round_trip_consistent` |
| PM-201 | loose-id-comparison (code-quality) | No (safe) | `src/orders.js` | `cancelOrder` | ✅ Yes (code-quality) | *(none — no wrong output at runtime; safety tests pass)* |
| PM-202 | unawaited-notify-call | Yes | `src/orders.js` | `placeOrder` | ✅ Yes | `test_bug_placeOrder_notify_failure_returns_failure_not_success` |
| PM-202 | unawaited-notify-call | Yes | `src/orders.js` | `cancelOrder` | ✅ Yes | `test_bug_cancelOrder_notify_failure_returns_failure_not_success` |
| PM-202 | unawaited-notify-call | Yes | `src/users.js` | `updateUserEmail` | ✅ Yes | `test_bug_updateUserEmail_notify_failure_returns_failure_not_success` |
| PM-203 | find-no-null-guard | Yes | `src/inventory.js` | `getProductDetails` | ✅ Yes | `test_bug_getProductDetails_unknown_id_returns_null_not_empty_object` |
| PM-203 | find-no-null-guard | Yes | `src/discounts.js` | `applyDiscount` | ✅ Yes | `test_bug_applyDiscount_unknown_code_returns_failure_not_crash` |

---

## Fixes Applied

### Bug 1 — `addToCart` in `src/cart.js` (PM-201)

`productId` is now normalised to `Number` at the top of `addToCart`, so the product lookup, the existing-item check, and the stored item key are all numeric. String productIds from HTTP path parameters are handled correctly.

```diff
-function addToCart(userId, productId, quantity) {
-  const product = inventory.getAllProducts().find(p => p.id == productId);
+function addToCart(userId, productId, quantity) {
+  productId = Number(productId);
+  const product = inventory.getAllProducts().find(p => p.id === productId);
```

### Bug 2 — `placeOrder` in `src/orders.js` (PM-202)

```diff
-  notify.sendOrderConfirmation(userId, order.id, order.total);
+  try {
+    await notify.sendOrderConfirmation(userId, order.id, order.total);
+  } catch (err) {
+    return { success: false, reason: 'notification_failed' };
+  }
```

### Bug 3 — `cancelOrder` notification in `src/orders.js` (PM-202)

```diff
-  notify.sendOrderCancellationNotice(userId, orderId);
+  try {
+    await notify.sendOrderCancellationNotice(userId, orderId);
+  } catch (err) {
+    return { success: false, reason: 'notification_failed' };
+  }
```

### Code-quality improvement — `cancelOrder` authorisation in `src/orders.js` (PM-201)

Not a confirmed runtime bug (no wrong output possible with integer IDs), but the unreliable `!=` operator was replaced with the postmortem's intended fix:

```diff
-  if (order.userId != userId) {
+  if (order.userId !== Number(userId)) {
```

### Bug 4 — `updateUserEmail` in `src/users.js` (PM-202)

```diff
-  notify.sendEmailChangeAlert(oldEmail, newEmail);
+  try {
+    await notify.sendEmailChangeAlert(oldEmail, newEmail);
+  } catch (err) {
+    return { success: false, reason: 'notification_failed' };
+  }
```

### Bug 5 — `getProductDetails` in `src/inventory.js` (PM-203)

```diff
 function getProductDetails(productId) {
   const product = products.find(p => p.id === productId);
+  if (!product) {
+    return null;
+  }
   return Object.assign({}, product);
 }
```

### Bug 6 — `applyDiscount` in `src/discounts.js` (PM-203)

```diff
 function applyDiscount(code, orderTotal) {
   const discount = discountCodes.find(d => d.code === code);
+  if (!discount) {
+    return { success: false, reason: 'invalid_code' };
+  }
   if (!discount.active) {
```

---

## Suspicious-Looking Locations Checked and Judged Safe

| File | Function | Pattern Checked | Reason Safe |
|---|---|---|---|
| `src/orders.js` | `cancelOrder` | PM-201 loose-id-comparison | Contains `order.userId != userId`. This IS the PM-201 postmortem location; the fix was documented but not durably applied (action item 3 NOT completed). With integer IDs, JS loose `!=` coerces `"2"` and `2` as equal — no wrong output occurs. Operator improved to `!==` + `Number()` as a code-quality fix. |
| `src/orders.js` | `shipOrder` | PM-202 unawaited-notify-call | `notify.sendShippingUpdate(...).catch(() => {})` — explicit `.catch` chain. Intentional fire-and-forget: the caller cannot do anything if a shipping SMS fails after the order is already shipped. Not a silent failure. |
| `src/cart.js` | `checkoutCart` | PM-202 unawaited-notify-call | Already fixed (PM-202 postmortem location): has `try { await notify.sendCartCheckoutReminder(...) } catch`. |
| `src/users.js` | `getUserById` | PM-203 find-no-null-guard | Already fixed (PM-203 postmortem location): has `if (!user) return null`. |
| `src/users.js` | `getUserByEmail` | PM-203 find-no-null-guard | Has `if (!user) return null`. Safe. |
| `src/discounts.js` | `validateDiscountCode` | PM-201 loose-id-comparison | `code == null` is an intentional null-coalescing guard — not an ID comparison. |
| `src/inventory.js` | `reserveStock`, `releaseStock`, `updateStock`, `getStockLevel` | PM-203 find-no-null-guard | All have `if (!product)` guards before any property access. |
| `src/discounts.js` | `validateDiscountCode`, `incrementUsage`, `deactivateCode` | PM-203 find-no-null-guard | All have `if (!discount)` guards before any property access. |
| `src/orders.js` | `cancelOrder`, `shipOrder` | PM-203 find-no-null-guard | Both have `if (!order)` guards before any property access. |
| `src/cart.js` | `addToCart`, `updateCartItemQuantity` | PM-203 find-no-null-guard | Both have `if (!product)` / `if (!item)` guards. |

---

## Totals

| Metric | Value |
|---|---|
| Confirmed bugs found | 6 |
| Code-quality improvements (not confirmed bugs) | 1 (`cancelOrder` PM-201 `!=`) |
| Tests written | 16 (6 bug-proving, 10 safety) |
| **Bug-proving tests FAILING before fix** | **6** (copied from `npx jest --verbose` output before Step 5) |
| **Safety tests PASSING before fix** | **10** (copied from `npx jest --verbose` output before Step 5) |
| **Bug-proving tests PASSING after fix** | **6** (copied from `npx jest --verbose` output after Step 5) |
| **Safety tests PASSING after fix** | **10** (copied from `npx jest --verbose` output after Step 5) |
| Total tests PASSING after fix | 16 |
| **Guardrail issues before fixes** | **6** (copied from `node guardrails/check_patterns.js src` output before Step 5) |
| **Guardrail issues after fixes** | **0** (copied from `node guardrails/check_patterns.js src` output after Step 5) |
| Guardrail exit code before fixes | 1 |
| Guardrail exit code after fixes | 0 |

---

## Time Taken

| Step | Start (UTC+local) | End | Duration |
|---|---|---|---|
| BEFORE STEP 0 (setup questions) | 01:48:15 | 01:48:27 | ~12 s |
| STEP 0 — Project detection | 01:48:27 | 01:48:33 | ~6 s |
| STEP 1 — Learn from postmortems | 01:48:33 | 01:49:28 | ~55 s |
| STEPS 2–4 — Hunt, tests, guardrail (parallel subagents + iterations) | 01:49:28 | 02:02:19 | ~13 min |
| CHECKPOINT iterations (two rounds of feedback + fixes) | 02:02:19 | 02:23:17 | ~21 min |
| STEP 5 — Apply fixes & verify | 02:23:17 | 02:24:35 | ~78 s |
| STEP 6 — Report & CI | 02:24:35 | 02:25:30 | ~55 s |
| **Total** | **01:48:15** | **~02:25:30** | **~37 min** |

---

## What Would Have Happened

### Bug 1 — `addToCart` loose `==` (PM-201)

Any customer adding a product via a URL that supplies `productId` as a string (the normal HTTP case) would then be unable to update or remove that item from their cart — every subsequent `updateCartItemQuantity` or `removeFromCart` call would return `item_not_in_cart`. Customers would see items stuck in their cart at their original quantity with no way to change them, leading to incorrect order totals and support contacts.

### Bugs 2 & 3 — `placeOrder` and `cancelOrder` unawaited notify (PM-202)

During any notification-service outage, `placeOrder` would return `{ success: true }` with an order ID, but no confirmation email would be sent. Customers would not know whether their order was placed and would make duplicate orders — exactly the scenario from PM-202, which caused ~$14,000 in refund overhead. Similarly, `cancelOrder` would return success during an outage without sending the cancellation notice, leaving customers uncertain about their order status.

### Bug 4 — `updateUserEmail` unawaited notify (PM-202)

A notification-service outage during an email-change flow would silently update the stored email but return `{ success: true }` without alerting the user's old address. Security-alert emails would be lost, leaving users unaware that their email was changed — a potential account-takeover signal ignored.

### Bug 5 — `getProductDetails` no null guard (PM-203)

Any caller of `getProductDetails` with a deleted or non-existent product ID would receive `{}` instead of `null`. Callers that then accessed properties like `.price` or `.name` on the empty object would silently operate on `undefined` values — producing `NaN` prices, empty names, and corrupt display data instead of a clear "product not found" error. The same masking behaviour as PM-203 but for products rather than users.

### Bug 6 — `applyDiscount` no null guard (PM-203)

Any checkout attempt with an invalid, expired, or deleted discount code would cause an uncaught `TypeError: Cannot read properties of undefined (reading 'active')`. The request handler would crash and return a 500, preventing the customer from completing their purchase — even if the only issue was a mistyped promo code. This would produce a cluster of 500 errors identical in character to the PM-203 incident.

---

## CI Section

### Command run

```
Get-ChildItem -Force .github/workflows
```

### Output

```
Get-ChildItem : Cannot find path '...\shop-js-run\.github\workflows' because it does not exist.
```

### Decision: CI absent — proposal generated

No `.github/workflows/` directory exists. No existing workflow could be checked for the guardrail command.

**`reports/proposed-ci.yml` was created** with the following content:

```yaml
name: Never Twice — Guardrail & Tests

on:
  push:
    branches: ["**"]
  pull_request:
    branches: ["**"]

jobs:
  never-twice:
    name: Never Twice
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"

      - name: Install dependencies
        run: npm install

      - name: Run tests
        run: npm test -- --no-coverage

      - name: Run Never Twice guardrail
        run: node guardrails/check_patterns.js src
```

**To enable CI:**

1. Copy `reports/proposed-ci.yml` to `.github/workflows/never-twice.yml`
2. Review the `node-version` placeholder (currently `"20"` — adjust if the project targets a different LTS)
3. Commit and push — GitHub Actions will run the tests and guardrail on every push and pull request

The guardrail step exits non-zero if any of the three pattern violations are found; the workflow will fail and block the PR until the code is clean.
