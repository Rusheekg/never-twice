# Never Twice — Code Review Checklist

Use this checklist during every pull request review that touches `src/`.
Each item links to the postmortem that produced it.

---

- [ ] **PM-201 — Loose ID comparison**
  All comparisons involving IDs (userId, productId, orderId, etc.) must use
  `===` / `!==` (strict equality), not `==` / `!=`.
  If the ID may arrive as a string from an HTTP request, coerce it explicitly
  with `Number(id)` before comparing.
  → [postmortems/PM-201-order-cancellation-auth.md](../postmortems/PM-201-order-cancellation-auth.md)

- [ ] **PM-202 — Unawaited async notify call**
  Every call to a `notify.*` function must be `await`-ed and wrapped in a
  `try { await notify.method(...) } catch (err) { return { success: false, ... } }`
  block so that notification failures propagate as errors rather than being
  silently swallowed.
  An explicit `.catch(() => {})` is acceptable only for genuinely fire-and-forget
  notifications (e.g. shipping updates where the caller cannot do anything about
  a failure).
  → [postmortems/PM-202-checkout-silent-notify-failure.md](../postmortems/PM-202-checkout-silent-notify-failure.md)

- [ ] **PM-203 — Missing null guard after `.find()`**
  Every use of `Array.prototype.find()` must be followed immediately by a
  null check: `if (!result) return null;` (or an appropriate error object)
  before the result is accessed or passed to another function.
  `Object.assign({}, undefined)` silently returns `{}` — it does NOT throw,
  but it masks a missing-record bug. An explicit null guard is always required.
  → [postmortems/PM-203-user-lookup-null-crash.md](../postmortems/PM-203-user-lookup-null-crash.md)
