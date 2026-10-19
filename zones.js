const express = require('express');
const router = express.Router();
const dataStore = require('../services/dataStore');

// GET /api/zones
router.get('/', (req, res) => {
  const eventId = req.query.eventId || dataStore.getActiveEventId();
  const zones = dataStore.getZones(eventId);
  res.json(zones);
});

// GET /api/zones/:id
router.get('/:id', (req, res) => {
  const zone = dataStore.getZoneById(req.params.id);
  if (!zone) return res.status(404).json({ error: 'Zone not found' });
  res.json(zone);
});

// POST /api/zones
router.post('/', (req, res) => {
  const { zone_name, event_id, area, capacity, warning_threshold, critical_threshold, monitoring_enabled } = req.body;
  if (!zone_name || !capacity || !area) {
    return res.status(400).json({ error: 'Zone name, area, and capacity are required.' });
  }
  const newZone = dataStore.addZone({
    zone_name,
    event_id: Number(event_id) || dataStore.getActiveEventId(),
    area: Number(area),
    capacity: Number(capacity),
    warning_threshold: Number(warning_threshold) || 70.0,
    critical_threshold: Number(critical_threshold) || 90.0,
    monitoring_enabled: monitoring_enabled !== undefined ? monitoring_enabled : true
  });
  if (req.io) req.io.emit('zone:update', dataStore.getZones(newZone.event_id));
  res.status(201).json(newZone);
});

// PUT /api/zones/:id
router.put('/:id', (req, res) => {
  const updated = dataStore.updateZone(req.params.id, req.body);
  if (!updated) return res.status(404).json({ error: 'Zone not found' });
  if (req.io) req.io.emit('zone:update', dataStore.getZones(updated.event_id));
  res.json(updated);
});

// DELETE /api/zones/:id
router.delete('/:id', (req, res) => {
  dataStore.deleteZone(req.params.id);
  if (req.io) req.io.emit('zone:update', dataStore.getZones());
  res.json({ success: true });
});

module.exports = router;
