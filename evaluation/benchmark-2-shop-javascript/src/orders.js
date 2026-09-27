const notify = require('./notify');
const inventory = require('./inventory');

const orders = [];
let nextOrderId = 1001;

function getOrder(orderId) {
  return orders.find(o => o.id === orderId) || null;
}

function listOrdersByUser(userId) {
  return orders.filter(o => o.userId === userId).map(o => Object.assign({}, o));
}

async function placeOrder(userId, items, discountCode) {
  if (!items || items.length === 0) {
    return { success: false, reason: 'no_items' };
  }

  let subtotal = 0;
  const resolvedItems = [];
  for (const item of items) {
    const reservation = inventory.reserveStock(item.productId, item.quantity);
    if (!reservation.success) {
      return { success: false, reason: reservation.reason, productId: item.productId };
    }
    resolvedItems.push({
      productId: item.productId,
      quantity: item.quantity,
      unitPrice: item.unitPrice,
    });
    subtotal += item.unitPrice * item.quantity;
  }

  subtotal = parseFloat(subtotal.toFixed(2));

  const order = {
    id: nextOrderId++,
    userId,
    items: resolvedItems,
    subtotal,
    discount: discountCode || null,
    total: subtotal,
    status: 'pending',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };

  orders.push(order);

  try {
    await notify.sendOrderConfirmation(userId, order.id, order.total);
  } catch (err) {
    return { success: false, reason: 'notification_failed' };
  }

  order.status = 'confirmed';
  order.updatedAt = new Date().toISOString();

  return { success: true, orderId: order.id, total: order.total };
}

async function cancelOrder(orderId, userId) {
  const order = orders.find(o => o.id === orderId);
  if (!order) {
    return { success: false, reason: 'order_not_found' };
  }
  if (order.userId !== Number(userId)) {
    return { success: false, reason: 'unauthorized' };
  }
  if (order.status === 'shipped' || order.status === 'delivered') {
    return { success: false, reason: 'cannot_cancel_after_shipment' };
  }
  for (const item of order.items) {
    inventory.releaseStock(item.productId, item.quantity);
  }
  order.status = 'cancelled';
  order.updatedAt = new Date().toISOString();

  try {
    await notify.sendOrderCancellationNotice(userId, orderId);
  } catch (err) {
    return { success: false, reason: 'notification_failed' };
  }

  return { success: true };
}

async function shipOrder(orderId, trackingNumber) {
  const order = orders.find(o => o.id === orderId);
  if (!order) {
    return { success: false, reason: 'order_not_found' };
  }
  if (order.status !== 'confirmed') {
    return { success: false, reason: 'order_not_ready_to_ship' };
  }
  order.status = 'shipped';
  order.trackingNumber = trackingNumber;
  order.updatedAt = new Date().toISOString();

  notify.sendShippingUpdate(order.userId, orderId, trackingNumber).catch(() => {});

  return { success: true };
}

function listAllOrders() {
  return orders.map(o => Object.assign({}, o));
}

module.exports = {
  getOrder,
  listOrdersByUser,
  placeOrder,
  cancelOrder,
  shipOrder,
  listAllOrders,
};
