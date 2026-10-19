const express = require('express');
const router = express.Router();
const dataStore = require('../services/dataStore');

// GET /api/intelligence/crowd
router.get('/crowd', (req, res) => {
  const activeEventId = dataStore.getActiveEventId();
  const zones = dataStore.getZones(activeEventId);

  if (!zones || zones.length === 0) {
    return res.json({
      highestDensityZone: 'None',
      density: 0,
      crowdTrend: 'stable',
      riskLevel: 'safe',
      recommendation: 'No active monitored zones.'
    });
  }

  // Find zone with highest density
  const sortedByDensity = [...zones].sort((a, b) => b.density - a.density);
  const highestDensity = sortedByDensity[0];

  // Peak crowd zone
  const sortedByPeople = [...zones].sort((a, b) => b.current_people - a.current_people);
  const peakZone = sortedByPeople[0];

  let riskLevel = 'safe';
  let recommendation = 'Normal flow observed across all campus entryways.';

  if (highestDensity.status === 'CRITICAL') {
    riskLevel = 'critical';
    recommendation = `Divert inbound crowd flow away from ${highestDensity.zone_name}. Deploy safety marshals.`;
  } else if (highestDensity.status === 'WARNING') {
    riskLevel = 'warning';
    recommendation = `Monitor ${highestDensity.zone_name} entrances closely to prevent threshold breach.`;
  }

  res.json({
    highestDensityZone: highestDensity.zone_name,
    peakCrowdZone: peakZone.zone_name,
    density: highestDensity.density,
    crowdTrend: 'increasing',
    riskLevel,
    recommendation,
    aiMonitoringStatus: 'ACTIVE'
  });
});

module.exports = router;
