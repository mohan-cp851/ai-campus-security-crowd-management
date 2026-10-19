const express = require('express');
const router = express.Router();
const dataStore = require('../services/dataStore');

// GET /api/dashboard/kpis
router.get('/kpis', (req, res) => {
  const activeEventId = dataStore.getActiveEventId();
  const zones = dataStore.getZones(activeEventId);
  const alerts = dataStore.getAlerts(activeEventId);

  const totalCrowd = zones.reduce((sum, z) => sum + (z.current_people || 0), 0);
  const totalEntries = zones.reduce((sum, z) => sum + (z.total_entries || 0), 0);
  const activeZonesCount = zones.filter(z => z.monitoring_enabled).length;
  const criticalAlertsCount = alerts.filter(a => a.severity === 'CRITICAL' && !a.acknowledged).length;

  let overallStatus = 'SAFE';
  if (zones.some(z => z.status === 'CRITICAL')) {
    overallStatus = 'CRITICAL';
  } else if (zones.some(z => z.status === 'WARNING')) {
    overallStatus = 'WARNING';
  }

  res.json({
    totalCrowd,
    totalEntries,
    totalCrowdChangePercent: '+0.0%',
    activeZones: activeZonesCount,
    criticalAlerts: criticalAlertsCount,
    overallEventStatus: overallStatus,
    timestamp: new Date().toISOString()
  });
});

// GET /api/crowd/live
router.get('/live', (req, res) => {
  const activeEventId = dataStore.getActiveEventId();
  const zones = dataStore.getZones(activeEventId);
  const totalCrowd = zones.reduce((sum, z) => sum + (z.current_people || 0), 0);
  const totalEntries = zones.reduce((sum, z) => sum + (z.total_entries || 0), 0);

  res.json({
    totalCrowd,
    totalEntries,
    zones,
    timestamp: new Date().toISOString()
  });
});

module.exports = router;
