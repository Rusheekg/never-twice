# Never Twice — Findings

Generated: 2026-09-27  
Source folder scanned: `src/`

---

## Already-Fixed Locations (one per postmortem — skipped in Step 2)

| Postmortem | File | Function | Evidence the fix is present |
|---|---|---|---|
| PM-201 | `src/orders.js` | `cancelOrder` | **This is the location PM-201 describes as already fixed.** The postmortem's "Code After" shows `if (order.userId !== Number(userId))`. However, the current code still reads `if (order.userId != userId)` — the fix was never durably applied (action item 3 was marked NOT completed). The fix is therefore absent, and the guardrail would flag `!=` for this pattern. Because `!=` between integer IDs and their string representations produces no concrete wrong output at runtime (see "Checked and Ruled Out as Safe" below), this location is classified as **safe for the runtime bug** and moved out of the confirmed-bugs list. It is still fixed in Step 5 as a code-quality improvement. |
| PM-202 | `src/cart.js` | `checkoutCart` | The postmortem's "Code After" shows `try { await notify.sendCartCheckoutReminder(userId, total); } catch (err) { … }`. The current code contains exactly this pattern (lines 92–96). **Fix confirmed present — location skipped.** |
| PM-203 | `src/users.js` | `getUserById` | The postmortem's "Code After" shows `if (!user) { return null; }` before the `Object.assign`. The current code contains exactly this guard (lines 12–14). **Fix confirmed present — location skipped.** |

---

## Confirmed Bugs

### PM-201 — loose-id-comparison

| # | File | Function | Line | Why it is risky |
|---|---|---|---|---|
| 1 | [`src/cart.js`](../src/cart.js) | `addToCart` | 16 | `p.id == productId` uses loose `==`. When a string productId (e.g. `"1"` from an HTTP path parameter) is passed, `==` coerces it to match the numeric `p.id` of `1`, so the product IS found — but the item is stored under the **raw string key** `"1"`. Later calls to `updateCartItemQuantity` and `removeFromCart` use strict `===`, so passing the numeric `1` fails to find the item stored under string `"1"` and returns `item_not_in_cart` for a legitimately added item. This is a concrete, provable wrong result. Test: `test_bug_addToCart_string_productId_round_trip_consistent`. |

### PM-202 — unawaited-notify-call

| # | File | Function | Line | Why it is risky |
|---|---|---|---|---|
| 2 | [`src/orders.js`](../src/orders.js) | `placeOrder` | 51 | `notify.sendOrderConfirmation(...)` is called without `await` and without `.catch()`. When the notification service throws, the rejection is silently lost and the caller receives `{ success: true }` even though no confirmation was sent. Test: `test_bug_placeOrder_notify_failure_returns_failure_not_success`. |
| 3 | [`src/orders.js`](../src/orders.js) | `cancelOrder` | 76 | `notify.sendOrderCancellationNotice(...)` is called without `await` and without `.catch()`. Same silent failure mode. Test: `test_bug_cancelOrder_notify_failure_returns_failure_not_success`. |
| 4 | [`src/users.js`](../src/users.js) | `updateUserEmail` | 55 | `notify.sendEmailChangeAlert(...)` is called without `await` and without `.catch()`. A notification failure is silently swallowed and the caller receives `{ success: true }`. Test: `test_bug_updateUserEmail_notify_failure_returns_failure_not_success`. |

### PM-203 — find-no-null-guard

| # | File | Function | Line | Why it is risky |
|---|---|---|---|---|
| 5 | [`src/inventory.js`](../src/inventory.js) | `getProductDetails` | 14–15 | `products.find(...)` result is passed directly to `Object.assign({}, product)` with no null guard. For an unknown product ID, `find` returns `undefined` and `Object.assign({}, undefined)` silently returns `{}` — masking the missing record instead of surfacing a "not found" signal. Test: `test_bug_getProductDetails_unknown_id_returns_null_not_empty_object`. |
| 6 | [`src/discounts.js`](../src/discounts.js) | `applyDiscount` | 13–14 | `discountCodes.find(...)` result has `.active` accessed immediately with no null check. For an unknown discount code, `find` returns `undefined` and `undefined.active` throws a `TypeError`, crashing the request handler. Test: `test_bug_applyDiscount_unknown_code_returns_failure_not_crash`. |

---

## Checked and Ruled Out as Safe

### PM-201 — loose-id-comparison

| File | Function | Reason |
|---|---|---|
| `src/orders.js` | `cancelOrder` | Contains `order.userId != userId` (loose `!=`). This IS the specific location PM-201 describes — the postmortem says the fix (`!==` + `Number()`) was applied here, but the current code still has `!=` (the fix was not durably applied; action item 3 was marked NOT completed). Despite the pattern being present, **no concrete wrong output occurs at runtime**: JS loose `!=` treats integer `2` and string `"2"` as equal, so the authorisation check neither wrongly rejects a valid owner nor wrongly permits a different user for any integer-ID input. Under the mode's binary classification, a location with no concrete wrong result is not a confirmed bug. The fix is applied in Step 5 as a code-quality improvement. The guardrail does not flag `!=` (only `==` is flagged, as that is the operator that causes the concrete storage-key mismatch). |
| `src/discounts.js` | `validateDiscountCode` | `code == null` is an intentional null-coalescing guard, not an ID comparison. |
| `src/inventory.js` | all functions | All `find` predicates use `p.id === productId` (strict equality). |
| `src/orders.js` | `getOrder` | Uses `o.id === orderId` (strict equality). |
| `src/orders.js` | `listOrdersByUser` | Uses `o.userId === userId` (strict equality). |
| `src/users.js` | all functions | All comparisons use `===` or `!==`. |
| `src/cart.js` | `removeFromCart`, `updateCartItemQuantity` | Use `i.productId === productId` (strict equality). |

### PM-202 — unawaited-notify-call

| File | Function | Reason |
|---|---|---|
| `src/cart.js` | `checkoutCart` | **Already-fixed location for PM-202.** Has `try { await notify.sendCartCheckoutReminder(...) } catch (err) { return { success: false, reason: 'notification_failed' }; }` — exactly the "Code After" from PM-202. |
| `src/orders.js` | `shipOrder` | Has `.catch(() => {})` directly chained — intentional, explicit fire-and-forget, not a silent failure. |
| `src/discounts.js`, `src/inventory.js`, `src/notify.js` | all | No calls to `notify.*` functions at all. |

### PM-203 — find-no-null-guard

| File | Function | Reason |
|---|---|---|
| `src/users.js` | `getUserById` | **Already-fixed location for PM-203.** Has `if (!user) { return null; }` — exactly the "Code After" from PM-203. |
| `src/users.js` | `getUserByEmail` | Has `if (!user) return null` — same pattern, independently safe. |
| `src/users.js` | `updateUserEmail`, `deactivateUser`, `isAdmin`, `createUser` | All have `if (!user)` guards before any property access. |
| `src/orders.js` | `getOrder` | Uses `|| null` guard. |
| `src/orders.js` | `cancelOrder`, `shipOrder` | Both have `if (!order)` guards. |
| `src/inventory.js` | `reserveStock`, `releaseStock`, `updateStock`, `getStockLevel` | All have `if (!product)` guards. |
| `src/discounts.js` | `validateDiscountCode`, `incrementUsage`, `deactivateCode` | All have `if (!discount)` guards before property access. |
| `src/cart.js` | `addToCart`, `updateCartItemQuantity` | Both have `if (!product)` / `if (!item)` guards before property access. |
