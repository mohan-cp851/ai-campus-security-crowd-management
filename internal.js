const express = require('express');
const router = express.Router();
const dataStore = require('../services/dataStore');
const { calculateZoneMetrics } = require('../services/crowdEngine');
const predictionEngine = require('../services/predictionEngine');

const ML_SERVICE_SECRET = process.env.ML_SERVICE_SECRET || 'campus_security_ml_secret_key_2026';

// Middleware to authenticate internal ML service requests (Prompt 5)
function authenticateInternalService(req, res, next) {
  const secretKey = req.headers['x-ml-service-key'];
  if (!secretKey || secretKey !== ML_SERVICE_SECRET) {
    return res.status(401).json({
      error: 'Unauthorized: Missing or invalid x-ml-service-key header'
    });
  }
  next();
}

// POST /api/internal/detections (Prompt 5)
// Extended: also accepts optional active_count, total_entries from tracker (ML service)
router.post('/detections', authenticateInternalService, (req, res) => {
  const {
    camera_id, zone_id, people_count, confidence_avg, detection_source, timestamp,
    // Optional tracker fields — ignored gracefully if absent
    active_count, total_entries
  } = req.body;

  if (zone_id === undefined || people_count === undefined) {
    return res.status(400).json({ error: 'Missing required detection fields: zone_id, people_count' });
  }

  const numericZoneId = Number(zone_id);
  const count = Math.max(0, parseInt(people_count, 10));
  const activeEventId = dataStore.getActiveEventId();

  // Find zone in store
  const targetZone = dataStore.getZoneById(numericZoneId);
  if (!targetZone) {
    return res.status(404).json({ error: `Zone with id ${numericZoneId} not found.` });
  }

  // Prioritize actual optical people_count detected in the frame; fallback to active_count
  const effectiveCount = (count !== undefined && !isNaN(count))
    ? count
    : (active_count !== undefined && !isNaN(active_count) ? Math.max(0, parseInt(active_count, 10)) : 0);

  // Update zone state with real YOLOv8 detection
  const now = new Date(timestamp || Date.now()).toISOString();
  dataStore.updateZone(numericZoneId, {
    current_people: effectiveCount,
    active_count: effectiveCount,
    total_entries: total_entries !== undefined ? parseInt(total_entries, 10) : undefined,
    detection_source: detection_source || 'yolov8',
    last_ml_update: Date.now(),
    camera_status: 'ONLINE'
  });

  // Feature 3: Record crowd history for AI trend and prediction forecasting
  predictionEngine.recordZoneCrowd(numericZoneId, effectiveCount, Date.now());

  // Calculate metrics server-side (Prompt 13 of main spec)
  const metrics = calculateZoneMetrics(effectiveCount, targetZone);

  // Feature 1: Automatic Incident Center evaluation (deduplicated continuous condition)
  dataStore.autoProcessIncidentForZone({ ...targetZone, current_people: effectiveCount }, activeEventId, metrics, req.io);

  // Check alert conditions & trigger if needed
  let newAlert = null;
  const existingAlerts = dataStore.getAlerts(activeEventId);
  const hasActiveAlertForZone = existingAlerts.some(
    a => a.zone_id === numericZoneId && !a.acknowledged && a.severity === metrics.status
  );

  if (!hasActiveAlertForZone) {
    if (metrics.status === 'CRITICAL') {
      newAlert = dataStore.addAlert({
        event_id: activeEventId,
        zone_id: numericZoneId,
        severity: 'CRITICAL',
        message: `YOLOv8 DETECTED: ${targetZone.zone_name} exceeded critical threshold at ${metrics.occupancy}% occupancy (${count}/${targetZone.capacity} people).`
      });
    } else if (metrics.status === 'WARNING') {
      newAlert = dataStore.addAlert({
        event_id: activeEventId,
        zone_id: numericZoneId,
        severity: 'WARNING',
        message: `YOLOv8 Notice: ${targetZone.zone_name} warning threshold reached (${metrics.occupancy}% occupancy).`
      });
    }
  }

  // Fetch updated zones list
  const allZones = dataStore.getZones(activeEventId);
  const totalCrowd = allZones.reduce((sum, z) => sum + (z.current_people || 0), 0);

  // Determine overall event status
  let overallStatus = 'SAFE';
  if (allZones.some(z => z.status === 'CRITICAL')) {
    overallStatus = 'CRITICAL';
  } else if (allZones.some(z => z.status === 'WARNING')) {
    overallStatus = 'WARNING';
  }

  // Record trend point
  const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  dataStore.recordTrendPoint({
    time: timeStr,
    total: totalCrowd,
    mainGate: allZones.find(z => z.id === 1)?.current_people || 0,
    auditorium: allZones.find(z => z.id === 2)?.current_people || 0,
    foodCourt: allZones.find(z => z.id === 3)?.current_people || 0,
    ground: allZones.find(z => z.id === 4)?.current_people || 0
  });

  // Emit Socket.IO real-time events (Prompt 17)
  if (req.io) {
    req.io.emit('crowd:update', {
      totalCrowd,
      timestamp: now,
      overallStatus,
      detectionSource: 'yolov8',
      zones: allZones,
      // Extended tracker fields (optional — undefined when ML tracker not active)
      activeCount: active_count !== undefined ? Number(active_count) : undefined,
      totalEntries: total_entries !== undefined ? Number(total_entries) : undefined
    });
    req.io.emit('zone:update', allZones);
    if (newAlert) {
      req.io.emit('alert:new', newAlert);
    }
    // Update live predictions and emit prediction:update on every ML detection
    try {
      predictionEngine.runPredictionCycle(req.io, allZones, activeEventId, dataStore);
    } catch (e) {
      console.error('[Predictions] Error running prediction cycle:', e);
    }
  }

  res.status(200).json({
    success: true,
    processed: {
      zone_id: numericZoneId,
      people_count: count,
      occupancy: metrics.occupancy,
      density: metrics.density,
      status: metrics.status,
      alertGenerated: !!newAlert
    }
  });
});

module.exports = router;
