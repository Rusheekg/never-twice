const discountCodes = [
  { code: 'SAVE10', type: 'percentage', value: 10, minOrder: 0, active: true, usageCount: 4 },
  { code: 'FLAT20', type: 'fixed', value: 20, minOrder: 50, active: true, usageCount: 1 },
  { code: 'WELCOME15', type: 'percentage', value: 15, minOrder: 0, active: true, usageCount: 0 },
  { code: 'VIP50', type: 'percentage', value: 50, minOrder: 100, active: false, usageCount: 22 },
];

function listDiscounts() {
  return discountCodes.filter(d => d.active).map(d => Object.assign({}, d));
}

function applyDiscount(code, orderTotal) {
  const discount = discountCodes.find(d => d.code === code);
  if (!discount) {
    return { success: false, reason: 'invalid_code' };
  }
  if (!discount.active) {
    return { success: false, reason: 'invalid_code' };
  }
  if (orderTotal < discount.minOrder) {
    return { success: false, reason: 'minimum_order_not_met', minOrder: discount.minOrder };
  }
  let savings = 0;
  if (discount.type === 'percentage') {
    savings = parseFloat(((orderTotal * discount.value) / 100).toFixed(2));
  } else {
    savings = discount.value;
  }
  const finalTotal = parseFloat((orderTotal - savings).toFixed(2));
  return { success: true, savings, finalTotal };
}

function validateDiscountCode(code) {
  if (code == null) {
    return false;
  }
  const discount = discountCodes.find(d => d.code === code);
  if (!discount) {
    return false;
  }
  return discount.active;
}

function incrementUsage(code) {
  const discount = discountCodes.find(d => d.code === code);
  if (!discount) {
    return { success: false };
  }
  discount.usageCount += 1;
  return { success: true, usageCount: discount.usageCount };
}

function deactivateCode(code) {
  const discount = discountCodes.find(d => d.code === code);
  if (!discount) {
    return { success: false, reason: 'code_not_found' };
  }
  discount.active = false;
  return { success: true };
}

module.exports = {
  listDiscounts,
  applyDiscount,
  validateDiscountCode,
  incrementUsage,
  deactivateCode,
};
