let _forceFailure = false;

function setNotifyFailure(shouldFail) {
  _forceFailure = shouldFail;
}

async function sendOrderConfirmation(userId, orderId, total) {
  if (_forceFailure) {
    throw new Error('Notification service unavailable');
  }
  return { sent: true, channel: 'email', userId, orderId, total };
}

async function sendOrderCancellationNotice(userId, orderId) {
  if (_forceFailure) {
    throw new Error('Notification service unavailable');
  }
  return { sent: true, channel: 'email', userId, orderId };
}

async function sendShippingUpdate(userId, orderId, trackingNumber) {
  if (_forceFailure) {
    throw new Error('Notification service unavailable');
  }
  return { sent: true, channel: 'sms', userId, orderId, trackingNumber };
}

async function sendEmailChangeAlert(oldEmail, newEmail) {
  if (_forceFailure) {
    throw new Error('Notification service unavailable');
  }
  return { sent: true, channel: 'email', oldEmail, newEmail };
}

async function sendCartCheckoutReminder(userId, total) {
  if (_forceFailure) {
    throw new Error('Notification service unavailable');
  }
  return { sent: true, channel: 'email', userId, total };
}

module.exports = {
  setNotifyFailure,
  sendOrderConfirmation,
  sendOrderCancellationNotice,
  sendShippingUpdate,
  sendEmailChangeAlert,
  sendCartCheckoutReminder,
};
