# ANSWER KEY

> **Note:** This file should live in the parent folder of the project. It was placed in the project root instead because write access is limited to the workspace directory. Please move it one level up after reviewing.

---

## 1. Hidden Bugs (6 total)

### Bug G1 — Loose Equality (Type G)
| Field | Detail |
|---|---|
| **File** | `src/cart.js` |
| **Function** | `addToCart` |
| **Line** | `const product = inventory.getAllProducts().find(p => p.id == productId);` |
| **Type** | Type G — loose equality |
| **Trigger input** | Call `addToCart(1, 1, 1)` where `productId` is the number `1`. Because `getAllProducts()` returns objects whose `id` is a number, `==` works here — but call `addToCart(1, "99", 1)` (string ID that does not exist): `==` still coerces and may match unexpectedly. More critically, call `addToCart(1, "1", 1)`: the string `"1"` loose-equals the number `1`, so the wrong/accidental match goes through. Conversely, if internal IDs were stored as strings and the caller passes a number, the match fails entirely even for a valid product. |
| **Wrong result** | Product lookup behaves inconsistently based on the JavaScript type of `productId`. A string `"1"` matches product `1` (accidental success) while a number `99` fails (expected). The cart accumulates items keyed by mixed types, causing a duplicate entry: `existing` uses strict `===` on `i.productId === productId`, so a cart already holding `productId: 1` (number) will not merge with a new call passing `productId: "1"` (string), duplicating the line item. |
| **Correct behaviour after fix** | Replace `==` with `===` (and ensure callers normalise `productId` to a number) so the lookup is type-safe and the `existing` check is consistent. |

---

### Bug G2 — Loose Equality (Type G)
| Field | Detail |
|---|---|
| **File** | `src/orders.js` |
| **Function** | `cancelOrder` |
| **Line** | `if (order.userId != userId) {` |
| **Type** | Type G — loose equality |
| **Trigger input** | Orders are stored with `userId` as a number (e.g. `2`). Call `cancelOrder(1001, "2")` — passing a string user ID as would happen from a parsed URL param. |
| **Wrong result** | `order.userId != userId` evaluates as `2 != "2"` which is `false` under loose equality (they are coerced equal), so this call incorrectly passes the auth check — a different user whose ID happens to coerce to the same value could cancel someone else's order. Conversely, if stored as string and caller passes number, legitimate cancellations are blocked. |
| **Correct behaviour after fix** | Replace `!=` with `!==` (and/or normalise `userId` to `Number(userId)`) so the comparison is strict and type-safe. |

---

### Bug H1 — Unhandled Promise (Type H)
| Field | Detail |
|---|---|
| **File** | `src/orders.js` |
| **Function** | `placeOrder` |
| **Line** | `notify.sendOrderConfirmation(userId, order.id, order.total);` |
| **Type** | Type H — unhandled promise |
| **Trigger input** | Call `notify.setNotifyFailure(true)` then call `placeOrder(1, [{productId:1, quantity:1, unitPrice:79.99}], null)`. |
| **Wrong result** | The function does not `await` the notification call. When `sendOrderConfirmation` rejects, the rejection is unhandled (silent). The order is pushed to the array, its status is set to `'confirmed'`, and `{ success: true, ... }` is returned — yet the customer never receives a confirmation. The order ends up confirmed without notification and the error is invisible. |
| **Correct behaviour after fix** | `await notify.sendOrderConfirmation(...)` inside a try/catch; on failure either return an error or roll back the order status. |

---

### Bug H2 — Unhandled Promise (Type H)
| Field | Detail |
|---|---|
| **File** | `src/users.js` |
| **Function** | `updateUserEmail` |
| **Line** | `notify.sendEmailChangeAlert(oldEmail, newEmail);` |
| **Type** | Type H — unhandled promise |
| **Trigger input** | Call `notify.setNotifyFailure(true)` then call `updateUserEmail(1, 'newalice@example.com', notify)`. |
| **Wrong result** | The email is updated in memory and `{ success: true }` is returned. The rejection from `sendEmailChangeAlert` is silently lost. The user's email address is changed without the security alert being sent. |
| **Correct behaviour after fix** | `await notify.sendEmailChangeAlert(...)` and handle the rejection, either reverting the email change or returning a failure to the caller. |

---

### Bug I1 — Missing Null Check (Type I)
| Field | Detail |
|---|---|
| **File** | `src/discounts.js` |
| **Function** | `applyDiscount` |
| **Line** | `const discount = discountCodes.find(d => d.code === code);` followed immediately by `if (!discount.active)` |
| **Type** | Type I — missing null/undefined check |
| **Trigger input** | Call `applyDiscount('BOGUS999', 100)`. |
| **Wrong result** | `find` returns `undefined`. The next line accesses `discount.active`, throwing `TypeError: Cannot read properties of undefined (reading 'active')`. |
| **Correct behaviour after fix** | Check `if (!discount)` before accessing any property and return `{ success: false, reason: 'invalid_code' }`. |

---

### Bug I2 — Missing Null Check (Type I)
| Field | Detail |
|---|---|
| **File** | `src/inventory.js` |
| **Function** | `getProductDetails` |
| **Line** | `const product = products.find(p => p.id === productId);` followed by `return Object.assign({}, product);` |
| **Type** | Type I — missing null/undefined check |
| **Trigger input** | Call `getProductDetails(9999)`. |
| **Wrong result** | `find` returns `undefined`. `Object.assign({}, undefined)` does NOT throw — it silently returns `{}`, so the caller receives an empty object and has no way to tell whether the product was not found or simply has no properties. Any downstream code checking `product.price` gets `undefined` instead of an error. |
| **Correct behaviour after fix** | Add `if (!product) return null;` before the `Object.assign` so callers can detect the missing product. |

---

## 2. Already-Fixed Examples (3 total)

| # | File | Function | Type | Description |
|---|---|---|---|---|
| Fix G | `src/inventory.js` | `reserveStock` | Type G | Uses `===` to find the product by numeric ID: `products.find(p => p.id === productId)` — strict comparison, type-safe. |
| Fix H | `src/cart.js` | `checkoutCart` | Type H | Correctly `await`s `notify.sendCartCheckoutReminder` inside a `try/catch`, propagating failure as `{ success: false, reason: 'notification_failed' }`. |
| Fix I | `src/users.js` | `getUserById` | Type I | Checks `if (!user) return null;` after `users.find(...)` before accessing any properties. |

---

## 3. Decoys (3 total)

| # | File | Function | Why it is safe |
|---|---|---|---|
| Decoy G | `src/discounts.js` | `validateDiscountCode` | `if (code == null)` uses intentional loose `== null` to guard against both `null` and `undefined` in a single idiomatic check. This is a well-known deliberate pattern; it does not compare IDs or typed domain values. |
| Decoy H | `src/orders.js` | `shipOrder` | `notify.sendShippingUpdate(...).catch(() => {})` — the promise is explicitly handled. The `.catch` suppresses the rejection by design: shipping-status notifications are best-effort and a failure must not block the shipment record from being updated. This is intentional fire-and-forget with an explicit catch, not an unhandled promise. |
| Decoy I | `src/cart.js` | `updateCartItemQuantity` | The `cart.items.find(i => i.productId === productId)` call is preceded by a `carts.has(userId)` guard and the caller is `removeFromCart` which already validated the item exists. If `item` is `null` here, the function returns `{ success: false, reason: 'item_not_in_cart' }` — the check is present and correct. |
