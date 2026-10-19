const express = require('express');
const router = express.Router();
const dataStore = require('../services/dataStore');

// GET /api/reports/crowd
router.get('/crowd', (req, res) => {
  const activeEventId = dataStore.getActiveEventId();
  const zones = dataStore.getZones(activeEventId);
  const reportData = zones.map(z => ({
    zone_name: z.zone_name,
    capacity: z.capacity,
    current_people: z.current_people,
    occupancy_pct: z.occupancy,
    density_sqm: z.density,
    status: z.status,
    last_updated: z.last_updated
  }));
  res.json(reportData);
});

// GET /api/reports/alerts
router.get('/alerts', (req, res) => {
  const activeEventId = dataStore.getActiveEventId();
  const alerts = dataStore.getAlerts(activeEventId);
  res.json(alerts);
});

module.exports = router;
