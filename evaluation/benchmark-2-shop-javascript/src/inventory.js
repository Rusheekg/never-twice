const products = [
  { id: 1, name: 'Wireless Headphones', price: 79.99, stock: 50, category: 'electronics' },
  { id: 2, name: 'Running Shoes', price: 129.99, stock: 30, category: 'footwear' },
  { id: 3, name: 'Coffee Maker', price: 49.99, stock: 20, category: 'kitchen' },
  { id: 4, name: 'Yoga Mat', price: 34.99, stock: 100, category: 'fitness' },
  { id: 5, name: 'Desk Lamp', price: 24.99, stock: 75, category: 'home' },
];

function getAllProducts() {
  return products.map(p => Object.assign({}, p));
}

function getProductDetails(productId) {
  const product = products.find(p => p.id === productId);
  if (!product) {
    return null;
  }
  return Object.assign({}, product);
}

function reserveStock(productId, quantity) {
  const product = products.find(p => p.id === productId);
  if (!product) {
    return { success: false, reason: 'product_not_found' };
  }
  if (product.stock < quantity) {
    return { success: false, reason: 'insufficient_stock' };
  }
  product.stock -= quantity;
  return { success: true, remaining: product.stock };
}

function releaseStock(productId, quantity) {
  const product = products.find(p => p.id === productId);
  if (!product) {
    return { success: false, reason: 'product_not_found' };
  }
  product.stock += quantity;
  return { success: true, remaining: product.stock };
}

function updateStock(productId, newQuantity) {
  const product = products.find(p => p.id === productId);
  if (!product) {
    return { success: false, reason: 'product_not_found' };
  }
  if (newQuantity < 0) {
    return { success: false, reason: 'invalid_quantity' };
  }
  product.stock = newQuantity;
  return { success: true };
}

function getStockLevel(productId) {
  const product = products.find(p => p.id === productId);
  if (!product) {
    return null;
  }
  return product.stock;
}

function searchProducts(query) {
  const lower = query.toLowerCase();
  return products
    .filter(p => p.name.toLowerCase().includes(lower) || p.category.toLowerCase().includes(lower))
    .map(p => Object.assign({}, p));
}

module.exports = {
  getAllProducts,
  getProductDetails,
  reserveStock,
  releaseStock,
  updateStock,
  getStockLevel,
  searchProducts,
};
