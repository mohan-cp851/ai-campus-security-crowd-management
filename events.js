const express = require('express');
const router = express.Router();
const dataStore = require('../services/dataStore');

// GET /api/events
router.get('/', (req, res) => {
  const events = dataStore.getEvents();
  const activeEventId = dataStore.getActiveEventId();
  res.json({
    activeEventId,
    events
  });
});

// POST /api/events
router.post('/', (req, res) => {
  const { event_name, event_date, start_time, end_time, venue, status, description } = req.body;
  if (!event_name || !event_date || !venue) {
    return res.status(400).json({ error: 'Missing required event fields' });
  }
  const newEvent = dataStore.addEvent({
    event_name,
    event_date,
    start_time: start_time || '09:00:00',
    end_time: end_time || '18:00:00',
    venue,
    status: status || 'PLANNED',
    description: description || ''
  });
  if (req.io) req.io.emit('event:status', { type: 'CREATED', event: newEvent });
  res.status(201).json(newEvent);
});

// POST /api/events/select
router.post('/select', (req, res) => {
  const { eventId } = req.body;
  if (!eventId) return res.status(400).json({ error: 'eventId is required' });
  dataStore.setActiveEventId(eventId);
  if (req.io) req.io.emit('event:status', { type: 'ACTIVE_CHANGED', activeEventId: eventId });
  res.json({ success: true, activeEventId: eventId });
});

// PUT /api/events/:id
router.put('/:id', (req, res) => {
  const updated = dataStore.updateEvent(req.params.id, req.body);
  if (!updated) return res.status(404).json({ error: 'Event not found' });
  if (req.io) req.io.emit('event:status', { type: 'UPDATED', event: updated });
  res.json(updated);
});

// DELETE /api/events/:id
router.delete('/:id', (req, res) => {
  dataStore.deleteEvent(req.params.id);
  if (req.io) req.io.emit('event:status', { type: 'DELETED', id: req.params.id });
  res.json({ success: true });
});

module.exports = router;
