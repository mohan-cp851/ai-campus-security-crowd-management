const express = require('express');
const router = express.Router();
const dataStore = require('../services/dataStore');
const predictionEngine = require('../services/predictionEngine');

// GET /api/predictions
router.get('/', (req, res) => {
  const activeEventId = dataStore.getActiveEventId();
  const zones = dataStore.getZones(activeEventId);
  const horizon = parseInt(req.query.horizon, 10) || 15;

  const predictions = predictionEngine.predictAllZones(zones, horizon);

  // Determine highest risk zone and summary stats
  const highestRisk = [...predictions].sort((a, b) => (b.predictedOccupancy || 0) - (a.predictedOccupancy || 0))[0];
  const breachingZones = predictions.filter(p => p.willBreach);
  const totalCurrent = zones.reduce((s, z) => s + (z.current_people || 0), 0);
  const totalPredicted = predictions.reduce((s, p) => s + (p.predictedCrowd || 0), 0);

  // Confidence calculation across active predictions
  const validConfs = predictions.filter(p => p.hasSufficientData).map(p => p.confidence);
  const avgConfidence = validConfs.length ? Math.round(validConfs.reduce((a, b) => a + b, 0) / validConfs.length) : 0;

  res.json({
    summary: {
      horizon,
      totalCurrent,
      totalPredicted,
      highestRiskZone: highestRisk?.zoneName || 'None',
      highestRiskLevel: highestRisk?.riskLevel || 'SAFE',
      highestRiskOccupancy: highestRisk?.predictedOccupancy || 0,
      breachCount: breachingZones.length,
      breachingZones: breachingZones.map(b => ({
        zoneId: b.zoneId,
        zoneName: b.zoneName,
        predictedCrowd: b.predictedCrowd,
        capacity: b.capacity,
        excessPeople: b.excessPeople,
        expectedTimeToBreach: b.expectedTimeToBreach
      })),
      confidence: avgConfidence,
      modelMethod: 'Linear Regression Trend',
      timestamp: new Date().toISOString()
    },
    predictions
  });
});

// GET /api/predictions/history
router.get('/history', (req, res) => {
  const activeEventId = dataStore.getActiveEventId();
  const zones = dataStore.getZones(activeEventId);
  const result = {};

  zones.forEach(z => {
    result[z.id] = {
      zoneId: z.id,
      zoneName: z.zone_name,
      history: predictionEngine.getZoneHistory(z.id)
    };
  });

  res.json(result);
});

// GET /api/predictions/:zoneId
router.get('/:zoneId', (req, res) => {
  const zoneId = Number(req.params.zoneId);
  const zone = dataStore.getZoneById(zoneId);
  if (!zone) {
    return res.status(404).json({ error: `Zone ${zoneId} not found` });
  }

  const horizon = parseInt(req.query.horizon, 10) || 15;
  const prediction = predictionEngine.predictZoneCrowd(zone, horizon);

  res.json(prediction);
});

module.exports = router;
