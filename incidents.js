const express = require('express');
const router = express.Router();
const dataStore = require('../services/dataStore');

// GET /api/incidents (List + Summary Metrics)
router.get('/', (req, res) => {
  const eventId = req.query.eventId || dataStore.getActiveEventId();
  const { status, severity, search } = req.query;

  const allEventIncidents = dataStore.getIncidents(eventId);
  const filteredIncidents = dataStore.getIncidents(eventId, { status, severity, search });

  // Summary counts
  const total = allEventIncidents.length;
  const open = allEventIncidents.filter(i => i.status === 'OPEN').length;
  const critical = allEventIncidents.filter(i => i.severity === 'CRITICAL' && (i.status === 'OPEN' || i.status === 'IN PROGRESS')).length;
  const inProgress = allEventIncidents.filter(i => i.status === 'IN PROGRESS').length;

  const today = new Date().toISOString().slice(0, 10);
  const resolvedToday = allEventIncidents.filter(i => 
    i.status === 'RESOLVED' && i.resolved_at && i.resolved_at.startsWith(today)
  ).length;

  res.json({
    summary: {
      total,
      open,
      critical,
      inProgress,
      resolvedToday
    },
    incidents: filteredIncidents
  });
});

// GET /api/incidents/officers/list
router.get('/officers/list', (req, res) => {
  res.json(dataStore.getSecurityOfficers());
});

// GET /api/incidents/:id
router.get('/:id', (req, res) => {
  const incident = dataStore.getIncidentById(req.params.id);
  if (!incident) {
    return res.status(404).json({ error: `Incident ${req.params.id} not found` });
  }
  res.json(incident);
});

// POST /api/incidents (Create)
router.post('/', (req, res) => {
  const { event_id, zone_id, type, severity, description, recommended_action, assigned_officer_name } = req.body;
  
  if (!zone_id) {
    return res.status(400).json({ error: 'zone_id is required to create an incident' });
  }

  const newInc = dataStore.addIncident({
    event_id: event_id || dataStore.getActiveEventId(),
    zone_id,
    type: type || 'Security Incident',
    severity: severity || 'HIGH',
    status: 'OPEN',
    description,
    recommended_action,
    assigned_officer_name,
    actor: req.body.actor || 'Manual Dispatch'
  });

  if (req.io) {
    req.io.emit('incident:new', newInc);
  }

  res.status(201).json(newInc);
});

// PATCH /api/incidents/:id (Update)
router.patch('/:id', (req, res) => {
  const updated = dataStore.updateIncident(req.params.id, req.body, req.body.actor || 'Operator');
  if (!updated) {
    return res.status(404).json({ error: 'Incident not found' });
  }

  if (req.io) {
    req.io.emit('incident:update', updated);
  }

  res.json(updated);
});

// POST /api/incidents/:id/acknowledge
router.post('/:id/acknowledge', (req, res) => {
  const actor = req.body.actor || 'Security Officer';
  const ack = dataStore.acknowledgeIncident(req.params.id, actor);
  if (!ack) {
    return res.status(404).json({ error: 'Incident not found' });
  }

  if (req.io) {
    req.io.emit('incident:update', ack);
  }

  res.json({
    success: true,
    message: 'Incident acknowledged successfully.',
    incident: ack
  });
});

// POST /api/incidents/:id/assign
router.post('/:id/assign', (req, res) => {
  const { officerName, officerId, actor } = req.body;
  if (!officerName) {
    return res.status(400).json({ error: 'officerName is required' });
  }

  const assigned = dataStore.assignIncidentOfficer(req.params.id, officerName, officerId, actor || 'Command Center');
  if (!assigned) {
    return res.status(404).json({ error: 'Incident not found' });
  }

  if (req.io) {
    req.io.emit('incident:update', assigned);
  }

  res.json({
    success: true,
    message: `Officer ${officerName} assigned to incident ${assigned.incident_code}.`,
    incident: assigned
  });
});

// POST /api/incidents/:id/status
router.post('/:id/status', (req, res) => {
  const { status, actor, note } = req.body;
  if (!status) {
    return res.status(400).json({ error: 'status is required' });
  }

  const updated = dataStore.setIncidentStatus(req.params.id, status, actor || 'Command Center', note);
  if (!updated) {
    return res.status(404).json({ error: 'Incident not found or invalid status' });
  }

  if (req.io) {
    req.io.emit('incident:update', updated);
  }

  res.json({ success: true, incident: updated });
});

// POST /api/incidents/:id/resolve
router.post('/:id/resolve', (req, res) => {
  const { resolution_notes, actor } = req.body;
  const resolved = dataStore.resolveIncident(req.params.id, resolution_notes, actor || 'Command Center');
  if (!resolved) {
    return res.status(404).json({ error: 'Incident not found' });
  }

  if (req.io) {
    req.io.emit('incident:resolved', resolved);
    req.io.emit('incident:update', resolved);
  }

  res.json({
    success: true,
    message: 'Incident marked as resolved.',
    incident: resolved
  });
});

// POST /api/incidents/:id/close
router.post('/:id/close', (req, res) => {
  const { actor } = req.body;
  const closed = dataStore.closeIncident(req.params.id, actor || 'Admin');
  if (!closed) {
    return res.status(404).json({ error: 'Incident not found' });
  }

  if (req.io) {
    req.io.emit('incident:update', closed);
  }

  res.json({
    success: true,
    message: 'Incident closed successfully.',
    incident: closed
  });
});

module.exports = router;
