const express = require('express');
const router = express.Router();
const dataStore = require('../services/dataStore');

// GET /api/alerts
router.get('/', (req, res) => {
  const eventId = req.query.eventId || dataStore.getActiveEventId();
  const alerts = dataStore.getAlerts(eventId);
  res.json(alerts);
});

// PATCH /api/alerts/:alertId/acknowledge (Prompt 7)
router.patch('/:alertId/acknowledge', (req, res) => {
  const acknowledged = dataStore.acknowledgeAlert(req.params.alertId);
  if (!acknowledged) {
    return res.status(404).json({ error: 'Alert not found' });
  }

  if (req.io) {
    req.io.emit('alert:acknowledged', acknowledged);
  }

  res.json({
    success: true,
    message: 'Alert acknowledged successfully.',
    alert: acknowledged
  });
});

module.exports = router;
