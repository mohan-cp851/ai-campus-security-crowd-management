const express = require('express');
const router = express.Router();
const dataStore = require('../services/dataStore');

// GET /api/emergency/status
router.get('/status', (req, res) => {
  const status = dataStore.getEmergencyStatus();
  res.json(status);
});

// POST /api/emergency/activate
router.post('/activate', (req, res) => {
  const { reason, activatedBy } = req.body;
  const status = dataStore.activateEmergency(
    reason || 'Campus Security Emergency Activated',
    activatedBy || 'Chief Security Officer',
    req.io
  );

  res.status(200).json({
    success: true,
    message: 'Emergency Mode activated. Command center switched to high-priority triage.',
    status
  });
});

// POST /api/emergency/deactivate
router.post('/deactivate', (req, res) => {
  const { deactivatedBy, force } = req.body;
  const currentStatus = dataStore.getEmergencyStatus();

  // If critical incidents still exist and force not specified, warn the caller
  if (currentStatus.criticalIncidentsCount > 0 && !force) {
    return res.status(409).json({
      error: 'CRITICAL_INCIDENTS_ACTIVE',
      criticalCount: currentStatus.criticalIncidentsCount,
      message: `Warning: ${currentStatus.criticalIncidentsCount} critical incidents remain active. Please confirm deactivation.`
    });
  }

  const result = dataStore.deactivateEmergency(deactivatedBy || 'Chief Security Officer', req.io);
  res.json(result);
});

// POST /api/emergency/assign-officer
router.post('/assign-officer', (req, res) => {
  const { officerName, zoneId, incidentId, actor } = req.body;
  if (!officerName) {
    return res.status(400).json({ error: 'officerName is required' });
  }

  // Dynamic Zone Assignment
  if (zoneId) {
    dataStore.assignOfficerToZone(officerName, zoneId, actor || 'Emergency Commander');
  }

  if (incidentId) {
    const updatedInc = dataStore.assignIncidentOfficer(incidentId, officerName, null, actor || 'Emergency Commander');
    if (req.io) req.io.emit('incident:update', updatedInc);
  }

  const status = dataStore.getEmergencyStatus();
  if (req.io) {
    req.io.emit('emergency:update', status);
    req.io.emit('officers:update', dataStore.getSecurityOfficers());
  }

  res.json({
    success: true,
    message: `Officer ${officerName} assigned successfully.`,
    status
  });
});

// POST /api/emergency/unassign-officer
router.post('/unassign-officer', (req, res) => {
  const { officerName, actor } = req.body;
  if (!officerName) {
    return res.status(400).json({ error: 'officerName is required' });
  }

  dataStore.unassignOfficer(officerName, actor || 'Emergency Commander');

  const status = dataStore.getEmergencyStatus();
  if (req.io) {
    req.io.emit('emergency:update', status);
    req.io.emit('officers:update', dataStore.getSecurityOfficers());
  }

  res.json({
    success: true,
    message: `Officer ${officerName} unassigned and set to AVAILABLE.`,
    status
  });
});

module.exports = router;
