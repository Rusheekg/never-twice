const notify = require('./notify');
const inventory = require('./inventory');

const carts = new Map();

function getCart(userId) {
  if (!carts.has(userId)) {
    return { userId, items: [], updatedAt: null };
  }
  return Object.assign({}, carts.get(userId), {
    items: carts.get(userId).items.map(i => Object.assign({}, i)),
  });
}

function addToCart(userId, productId, quantity) {
  productId = Number(productId);
  const product = inventory.getAllProducts().find(p => p.id === productId);
  if (!product) {
    return { success: false, reason: 'product_not_found' };
  }
  if (product.stock < quantity) {
    return { success: false, reason: 'insufficient_stock' };
  }
  if (!carts.has(userId)) {
    carts.set(userId, { userId, items: [], updatedAt: null });
  }
  const cart = carts.get(userId);
  const existing = cart.items.find(i => i.productId === productId);
  if (existing) {
    existing.quantity += quantity;
  } else {
    cart.items.push({ productId, name: product.name, price: product.price, quantity });
  }
  cart.updatedAt = new Date().toISOString();
  return { success: true, cart: getCart(userId) };
}

function removeFromCart(userId, productId) {
  if (!carts.has(userId)) {
    return { success: false, reason: 'cart_not_found' };
  }
  const cart = carts.get(userId);
  const index = cart.items.findIndex(i => i.productId === productId);
  if (index === -1) {
    return { success: false, reason: 'item_not_in_cart' };
  }
  cart.items.splice(index, 1);
  cart.updatedAt = new Date().toISOString();
  return { success: true };
}

function updateCartItemQuantity(userId, productId, quantity) {
  if (!carts.has(userId)) {
    return { success: false, reason: 'cart_not_found' };
  }
  const cart = carts.get(userId);
  const item = cart.items.find(i => i.productId === productId);
  if (!item) {
    return { success: false, reason: 'item_not_in_cart' };
  }
  if (quantity <= 0) {
    return removeFromCart(userId, productId);
  }
  item.quantity = quantity;
  cart.updatedAt = new Date().toISOString();
  return { success: true };
}

function clearCart(userId) {
  carts.delete(userId);
  return { success: true };
}

function getCartTotal(userId) {
  if (!carts.has(userId)) {
    return 0;
  }
  const cart = carts.get(userId);
  return parseFloat(
    cart.items.reduce((sum, item) => sum + item.price * item.quantity, 0).toFixed(2)
  );
}

async function checkoutCart(userId) {
  if (!carts.has(userId)) {
    return { success: false, reason: 'cart_empty' };
  }
  const cart = carts.get(userId);
  if (cart.items.length === 0) {
    return { success: false, reason: 'cart_empty' };
  }
  const total = getCartTotal(userId);
  try {
    await notify.sendCartCheckoutReminder(userId, total);
  } catch (err) {
    return { success: false, reason: 'notification_failed' };
  }
  return { success: true, total };
}

module.exports = {
  getCart,
  addToCart,
  removeFromCart,
  updateCartItemQuantity,
  clearCart,
  getCartTotal,
  checkoutCart,
};
