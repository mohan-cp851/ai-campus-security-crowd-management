const express = require('express');
const router = express.Router();
const simulationService = require('../services/simulationService');

// POST /api/simulation/start
router.post('/start', (req, res) => {
  simulationService.startSimulation();
  if (req.io) req.io.emit('simulation:status', simulationService.getSimulationStatus());
  res.json({ message: 'Simulation started successfully', ...simulationService.getSimulationStatus() });
});

// POST /api/simulation/stop
router.post('/stop', (req, res) => {
  simulationService.stopSimulation();
  if (req.io) req.io.emit('simulation:status', simulationService.getSimulationStatus());
  res.json({ message: 'Simulation stopped successfully', ...simulationService.getSimulationStatus() });
});

// GET /api/simulation/status
router.get('/status', (req, res) => {
  res.json(simulationService.getSimulationStatus());
});

module.exports = router;
