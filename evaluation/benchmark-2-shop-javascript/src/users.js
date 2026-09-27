const users = [
  { id: 1, name: 'Alice Nguyen', email: 'alice@example.com', role: 'customer', createdAt: '2025-01-15' },
  { id: 2, name: 'Bob Harmon', email: 'bob@example.com', role: 'customer', createdAt: '2025-02-20' },
  { id: 3, name: 'Carol Smith', email: 'carol@example.com', role: 'admin', createdAt: '2024-11-01' },
  { id: 4, name: 'David Park', email: 'david@example.com', role: 'customer', createdAt: '2025-03-10' },
];

let nextUserId = 5;

function getUserById(userId) {
  const user = users.find(u => u.id === userId);
  if (!user) {
    return null;
  }
  return Object.assign({}, user);
}

function getUserByEmail(email) {
  const user = users.find(u => u.email === email);
  if (!user) {
    return null;
  }
  return Object.assign({}, user);
}

function listUsers() {
  return users.map(u => ({ id: u.id, name: u.name, email: u.email, role: u.role }));
}

function createUser(name, email, role) {
  if (users.find(u => u.email === email)) {
    return { success: false, reason: 'email_already_registered' };
  }
  const user = {
    id: nextUserId++,
    name,
    email,
    role: role || 'customer',
    createdAt: new Date().toISOString().slice(0, 10),
  };
  users.push(user);
  return { success: true, user: Object.assign({}, user) };
}

async function updateUserEmail(userId, newEmail, notify) {
  const user = users.find(u => u.id === userId);
  if (!user) {
    return { success: false, reason: 'user_not_found' };
  }
  if (users.find(u => u.email === newEmail && u.id !== userId)) {
    return { success: false, reason: 'email_already_in_use' };
  }
  const oldEmail = user.email;
  user.email = newEmail;
  try {
    await notify.sendEmailChangeAlert(oldEmail, newEmail);
  } catch (err) {
    return { success: false, reason: 'notification_failed' };
  }
  return { success: true };
}

function deactivateUser(userId) {
  const user = users.find(u => u.id === userId);
  if (!user) {
    return { success: false, reason: 'user_not_found' };
  }
  user.active = false;
  return { success: true };
}

function isAdmin(userId) {
  const user = users.find(u => u.id === userId);
  if (!user) {
    return false;
  }
  return user.role === 'admin';
}

module.exports = {
  getUserById,
  getUserByEmail,
  listUsers,
  createUser,
  updateUserEmail,
  deactivateUser,
  isAdmin,
};
