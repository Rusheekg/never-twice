'use strict';
/**
 * Never Twice — bug-proving and safety tests
 *
 * Naming conventions:
 *   test_bug_*    → must FAIL on current (unfixed) code, PASS after fix
 *   test_safety_* → must PASS both before and after fix
 *
 * PM-202 unhandled-rejection containment strategy
 * -----------------------------------------------
 * The buggy code calls notify.* without await.  When the mock rejects, the
 * resulting promise has no handler, and Node 24 would crash the worker.
 *
 * Fix: mock the notify function with mockImplementation so that the returned
 * promise is rejected AND pre-caught in the same expression:
 *
 *   notify.sendXxx.mockImplementation(() => {
 *     const p = Promise.reject(new Error('...'));
 *     p.catch(() => {});   // ← handles the rejection immediately
 *     return p;            // ← still a rejected promise (so await would throw)
 *   });
 *
 * Now Node never sees an "unhandled" rejection (it is already handled by the
 * .catch()), so the worker stays alive and the test can observe the wrong
 * return value from the buggy code.
 */

// ---------------------------------------------------------------------------
// Top-level jest.mock declarations (hoisted by Jest — no out-of-scope refs).
// ---------------------------------------------------------------------------
jest.mock('../src/notify', () => ({
  sendOrderConfirmation:       jest.fn(),
  sendOrderCancellationNotice: jest.fn(),
  sendShippingUpdate:          jest.fn(),
  sendEmailChangeAlert:        jest.fn(),
  sendCartCheckoutReminder:    jest.fn(),
  setNotifyFailure:            jest.fn(),
}));

jest.mock('../src/inventory', () => ({
  getAllProducts: jest.fn(() => [
    { id: 1, name: 'Wireless Headphones', price: 79.99, stock: 50, category: 'electronics' },
    { id: 2, name: 'Running Shoes',       price: 129.99, stock: 30, category: 'footwear' },
  ]),
  getProductDetails: jest.fn(),
  reserveStock:      jest.fn(() => ({ success: true, remaining: 49 })),
  releaseStock:      jest.fn(() => ({ success: true, remaining: 50 })),
  updateStock:       jest.fn(),
  getStockLevel:     jest.fn(),
  searchProducts:    jest.fn(),
}));

// Require mocked modules (and modules that depend on them) after jest.mock
const notify    = require('../src/notify');
const inventory = require('../src/inventory');   // mocked version (for spy/reset)
const cart      = require('../src/cart');
const orders    = require('../src/orders');
const users     = require('../src/users');

// Require REAL implementations for PM-203 tests (bypass the mock)
const realInventory = jest.requireActual('../src/inventory');
const discounts     = require('../src/discounts'); // no mock, loaded fresh

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Reset every notify mock to resolved (success) behaviour.
 * Called in afterEach so no test can pollute the next one.
 */
function resetNotifySuccess() {
  notify.sendOrderConfirmation.mockReset();
  notify.sendOrderCancellationNotice.mockReset();
  notify.sendShippingUpdate.mockReset();
  notify.sendEmailChangeAlert.mockReset();
  notify.sendCartCheckoutReminder.mockReset();

  notify.sendOrderConfirmation.mockResolvedValue({ sent: true });
  notify.sendOrderCancellationNotice.mockResolvedValue({ sent: true });
  notify.sendShippingUpdate.mockResolvedValue({ sent: true });
  notify.sendEmailChangeAlert.mockResolvedValue({ sent: true });
  notify.sendCartCheckoutReminder.mockResolvedValue({ sent: true });
}

/**
 * Return a mockImplementation that makes a notify function reject with the
 * given message, while pre-catching the returned promise so Node never sees
 * an unhandled rejection even when the caller does NOT await the call.
 */
function containedReject(message) {
  return () => {
    const p = Promise.reject(new Error(message));
    p.catch(() => {}); // suppress unhandled-rejection crash in Node 24 workers
    return p;
  };
}

// ---------------------------------------------------------------------------
// PM-201 — loose-id-comparison
// ---------------------------------------------------------------------------
describe('PM-201 loose-id-comparison', () => {

  afterEach(() => {
    resetNotifySuccess();
    inventory.getAllProducts.mockReturnValue([
      { id: 1, name: 'Wireless Headphones', price: 79.99, stock: 50, category: 'electronics' },
      { id: 2, name: 'Running Shoes',       price: 129.99, stock: 30, category: 'footwear' },
    ]);
    inventory.reserveStock.mockReturnValue({ success: true, remaining: 49 });
    inventory.releaseStock.mockReturnValue({ success: true });
  });

  // ---- src/cart.js · addToCart ----------------------------------------

  describe('cart.addToCart', () => {

    test('test_bug_addToCart_string_productId_round_trip_consistent', () => {
      // The bug: addToCart uses `p.id == productId` (loose ==).
      // When productId is the string "1", == coerces it to match the numeric id 1,
      // so the product IS found.  But the item is stored with the RAW string "1"
      // as its productId.  Later, updateCartItemQuantity uses strict ===:
      //   i.productId === productId
      // Passing numeric 1 to update finds nothing (stored "1" !== 1) → item_not_in_cart.
      //
      // After the fix: addToCart normalises to Number(productId) before storing,
      // so the key is always a number and the round-trip is consistent.
      inventory.getAllProducts.mockReturnValue([
        { id: 1, name: 'Wireless Headphones', price: 79.99, stock: 50, category: 'electronics' },
      ]);

      const addResult = cart.addToCart(801, '1', 2);  // string productId via HTTP
      expect(addResult.success).toBe(true);

      const updateResult = cart.updateCartItemQuantity(801, 1, 5); // numeric productId
      // After fix  → both normalised to Number → match → { success: true }
      // Before fix → stored "1" !== number 1   → { success: false, reason: 'item_not_in_cart' }
      expect(updateResult.success).toBe(true);  // FAILS on buggy code
    });

    test('test_safety_addToCart_numeric_productId_works', () => {
      inventory.getAllProducts.mockReturnValue([
        { id: 1, name: 'Wireless Headphones', price: 79.99, stock: 50, category: 'electronics' },
      ]);
      const result = cart.addToCart(802, 1, 1);
      expect(result.success).toBe(true);
      expect(result.cart.items).toHaveLength(1);
    });

    test('test_safety_addToCart_unknown_product_returns_not_found', () => {
      const result = cart.addToCart(803, 9999, 1);
      expect(result.success).toBe(false);
      expect(result.reason).toBe('product_not_found');
    });
  });

  // ---- src/orders.js · cancelOrder (PM-201) ---------------------------
  // The current code has `order.userId != userId`.  With loose !=, the integer
  // 2 and the string "2" are loosely equal, so cancelOrder never wrongly rejects
  // for the numeric-string pairing that the postmortem describes.  No concrete
  // wrong output can be produced at runtime with the current `!=` operator for
  // integer IDs — the loose coercion coincidentally produces the correct result.
  //
  // Verdict: CHECKED AND JUDGED SAFE for runtime correctness with integer IDs.
  // The guardrail still flags the unreliable operator as a code-quality issue,
  // and the fix (=== + Number()) is still applied in Step 5.
  // No test_bug_ test is written for this location because there is no input
  // combination that produces a concrete wrong result with `!=` on integer IDs.

  describe('orders.cancelOrder (PM-201 safety only)', () => {
    beforeEach(() => {
      inventory.reserveStock.mockReturnValue({ success: true, remaining: 49 });
      inventory.releaseStock.mockReturnValue({ success: true });
    });

    test('test_safety_cancelOrder_owner_with_string_userId_can_cancel', async () => {
      // Passes on both buggy and fixed code — documents correct runtime behaviour.
      const placed = await orders.placeOrder(2, [{ productId: 1, quantity: 1, unitPrice: 79.99 }]);
      expect(placed.success).toBe(true);
      const result = await orders.cancelOrder(placed.orderId, '2');
      expect(result.success).toBe(true);
    });

    test('test_safety_cancelOrder_different_user_is_unauthorized', async () => {
      const placed = await orders.placeOrder(1, [{ productId: 1, quantity: 1, unitPrice: 79.99 }]);
      const result = await orders.cancelOrder(placed.orderId, 3);
      expect(result.success).toBe(false);
      expect(result.reason).toBe('unauthorized');
    });

    test('test_safety_cancelOrder_numeric_userId_same_user_succeeds', async () => {
      const placed = await orders.placeOrder(1, [{ productId: 1, quantity: 1, unitPrice: 79.99 }]);
      const result = await orders.cancelOrder(placed.orderId, 1);
      expect(result.success).toBe(true);
    });
  });
});

// ---------------------------------------------------------------------------
// PM-202 — unawaited-notify-call
// ---------------------------------------------------------------------------
describe('PM-202 unawaited-notify-call', () => {

  beforeEach(() => {
    resetNotifySuccess();
    inventory.reserveStock.mockReturnValue({ success: true, remaining: 49 });
    inventory.releaseStock.mockReturnValue({ success: true });
  });

  afterEach(() => {
    resetNotifySuccess();
  });

  // ---- src/orders.js · placeOrder -------------------------------------

  describe('orders.placeOrder', () => {

    test('test_bug_placeOrder_notify_failure_returns_failure_not_success', async () => {
      // Set sendOrderConfirmation to reject, with the rejection pre-caught so
      // Node 24 never sees an unhandled rejection even when the buggy code
      // doesn't await the call.
      notify.sendOrderConfirmation.mockImplementation(
        containedReject('Notification service unavailable'),
      );

      const result = await orders.placeOrder(
        1,
        [{ productId: 1, quantity: 1, unitPrice: 79.99 }],
      );
      // After fix (await + try/catch): { success: false, reason: 'notification_failed' }
      // Before fix (unawaited):        rejection pre-caught, silently dropped → { success: true }
      expect(result.success).toBe(false);           // FAILS on buggy code
      expect(result.reason).toBe('notification_failed');
    });

    test('test_safety_placeOrder_notify_success_returns_success', async () => {
      const result = await orders.placeOrder(
        1,
        [{ productId: 1, quantity: 1, unitPrice: 79.99 }],
      );
      expect(result.success).toBe(true);
      expect(result.orderId).toBeDefined();
    });
  });

  // ---- src/orders.js · cancelOrder (notification leg) -----------------

  describe('orders.cancelOrder – notify failure', () => {

    test('test_bug_cancelOrder_notify_failure_returns_failure_not_success', async () => {
      // Place the order first (sendOrderConfirmation resolves from beforeEach).
      const placed = await orders.placeOrder(
        1,
        [{ productId: 1, quantity: 1, unitPrice: 79.99 }],
      );
      expect(placed.success).toBe(true);
      const orderId = placed.orderId;

      // Now make the cancellation notification fail (pre-caught to avoid crash).
      notify.sendOrderCancellationNotice.mockImplementation(
        containedReject('Notification service unavailable'),
      );

      const result = await orders.cancelOrder(orderId, 1);
      // After fix: { success: false, reason: 'notification_failed' }
      // Before fix: rejection pre-caught & silently dropped → { success: true }
      expect(result.success).toBe(false);           // FAILS on buggy code
      expect(result.reason).toBe('notification_failed');
    });
  });

  // ---- src/users.js · updateUserEmail ---------------------------------

  describe('users.updateUserEmail', () => {

    test('test_bug_updateUserEmail_notify_failure_returns_failure_not_success', async () => {
      // updateUserEmail accepts notify as its third argument.
      notify.sendEmailChangeAlert.mockImplementation(
        containedReject('Notification service unavailable'),
      );

      const result = await users.updateUserEmail(1, 'changed@example.com', notify);
      // After fix: { success: false, reason: 'notification_failed' }
      // Before fix: rejection pre-caught & silently dropped → { success: true }
      expect(result.success).toBe(false);           // FAILS on buggy code
      expect(result.reason).toBe('notification_failed');
    });

    test('test_safety_updateUserEmail_notify_success_returns_success', async () => {
      const result = await users.updateUserEmail(1, 'safe@example.com', notify);
      expect(result.success).toBe(true);
    });
  });
});

// ---------------------------------------------------------------------------
// PM-203 — find-no-null-guard
// ---------------------------------------------------------------------------
describe('PM-203 find-no-null-guard', () => {

  // ---- src/inventory.js · getProductDetails ---------------------------
  // Uses realInventory (jest.requireActual) to bypass the top-level mock.

  describe('inventory.getProductDetails (real implementation)', () => {

    test('test_bug_getProductDetails_unknown_id_returns_null_not_empty_object', () => {
      // After fix: returns null for an unknown product ID
      // Before fix: Object.assign({}, undefined) silently returns {}
      const result = realInventory.getProductDetails(9999);
      expect(result).toBeNull();  // FAILS on buggy code (returns {} instead)
    });

    test('test_safety_getProductDetails_known_id_returns_product', () => {
      const result = realInventory.getProductDetails(1);
      expect(result).not.toBeNull();
      expect(result.id).toBe(1);
      expect(result.name).toBe('Wireless Headphones');
    });
  });

  // ---- src/discounts.js · applyDiscount -------------------------------

  describe('discounts.applyDiscount', () => {

    test('test_bug_applyDiscount_unknown_code_returns_failure_not_crash', () => {
      // After fix: returns { success: false, reason: 'invalid_code' }
      // Before fix: discount is undefined → discount.active throws TypeError → crash
      expect(
        () => discounts.applyDiscount('NONEXISTENT', 100),
      ).not.toThrow();  // FAILS on buggy code (throws TypeError)

      const result = discounts.applyDiscount('NONEXISTENT', 100);
      expect(result.success).toBe(false);
      expect(result.reason).toBe('invalid_code');
    });

    test('test_safety_applyDiscount_valid_active_code_applies_discount', () => {
      const result = discounts.applyDiscount('SAVE10', 100);
      expect(result.success).toBe(true);
      expect(result.savings).toBe(10);
      expect(result.finalTotal).toBe(90);
    });

    test('test_safety_applyDiscount_inactive_code_returns_invalid', () => {
      const result = discounts.applyDiscount('VIP50', 200);
      expect(result.success).toBe(false);
      expect(result.reason).toBe('invalid_code');
    });
  });
});
