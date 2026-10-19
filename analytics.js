const express = require('express');
const router = express.Router();
const dataStore = require('../services/dataStore');

// GET /api/analytics/summary
router.get('/summary', (req, res) => {
  const activeEventId = dataStore.getActiveEventId();
  const zones = dataStore.getZones(activeEventId);
  const alerts = dataStore.getAlerts(activeEventId);
  const history = dataStore.getTrendHistory();

  const totalCrowd = zones.reduce((sum, z) => sum + (z.current_people || 0), 0);
  const avgCrowd = zones.length ? Math.round(totalCrowd / zones.length) : 0;
  const maxCrowd = history.length ? Math.max(...history.map(h => h.total)) : totalCrowd;
  
  const mostCrowded = [...zones].sort((a, b) => (b.current_people || 0) - (a.current_people || 0))[0];
  const warningCount = alerts.filter(a => a.severity === 'WARNING').length;
  const criticalCount = alerts.filter(a => a.severity === 'CRITICAL').length;

  res.json({
    totalCrowd,
    averageCrowd: avgCrowd,
    maximumCrowd: maxCrowd,
    peakTime: '14:30 - 15:15 PM',
    mostCrowdedZone: mostCrowded ? mostCrowded.zone_name : 'N/A',
    warningsCount: warningCount,
    criticalAlertsCount: criticalCount
  });
});

// GET /api/analytics/zone-comparison
router.get('/zone-comparison', (req, res) => {
  const activeEventId = dataStore.getActiveEventId();
  const zones = dataStore.getZones(activeEventId);
  const data = zones.map(z => ({
    name: z.zone_name,
    count: z.current_people || 0,
    capacity: z.capacity,
    occupancy: z.occupancy || 0,
    status: z.status
  }));
  res.json(data);
});

// GET /api/analytics/crowd-trend
router.get('/crowd-trend', (req, res) => {
  const range = req.query.range || '30m';
  const history = dataStore.getTrendHistory();

  let sliced = history;
  if (range === '30m') {
    sliced = history.slice(-15);
  } else if (range === '1h') {
    sliced = history.slice(-30);
  }

  res.json(sliced);
});

module.exports = router;
