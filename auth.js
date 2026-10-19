const express = require('express');
const router = express.Router();
const jwt = require('jsonwebtoken');

const JWT_SECRET = process.env.JWT_SECRET || 'campus_security_jwt_secret_key_2026';

// Pre-configured demo accounts for fast access
const USERS = [
  { id: 1, email: 'admin@campus.edu', password: 'password123', name: 'Chief Security Officer', role: 'ADMIN' },
  { id: 2, email: 'officer@campus.edu', password: 'password123', name: 'Field Officer Marcus', role: 'SECURITY_OFFICER' },
  { id: 3, email: 'coordinator@campus.edu', password: 'password123', name: 'Elena Vance (Events)', role: 'EVENT_COORDINATOR' }
];

// POST /api/auth/login
router.post('/login', (req, res) => {
  const { email, password } = req.body;
  const user = USERS.find(u => u.email === email && u.password === password);

  if (!user) {
    return res.status(401).json({ error: 'Invalid email or password' });
  }

  const token = jwt.sign(
    { id: user.id, name: user.name, email: user.email, role: user.role },
    JWT_SECRET,
    { expiresIn: '24h' }
  );

  res.json({
    token,
    user: {
      id: user.id,
      name: user.name,
      email: user.email,
      role: user.role
    }
  });
});

module.exports = router;
