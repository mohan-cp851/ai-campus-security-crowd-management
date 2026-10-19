const express = require('express');
const cors = require('cors');
const http = require('http');
const { Server } = require('socket.io');
require('dotenv').config();

const simulationService = require('./services/simulationService');

// Route Handlers
const authRoutes = require('./routes/auth');
const eventRoutes = require('./routes/events');
const zoneRoutes = require('./routes/zones');
const dashboardRoutes = require('./routes/dashboard');
const intelligenceRoutes = require('./routes/intelligence');
const alertRoutes = require('./routes/alerts');
const analyticsRoutes = require('./routes/analytics');
const reportRoutes = require('./routes/reports');
const simulationRoutes = require('./routes/simulation');
const internalRoutes = require('./routes/internal');
const incidentRoutes = require('./routes/incidents');
const emergencyRoutes = require('./routes/emergency');
const predictionRoutes = require('./routes/predictions');

const app = express();
const server = http.createServer(app);

const io = new Server(server, {
  cors: {
    origin: '*',
    methods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']
  }
});

// Middleware
app.use(cors());
app.use(express.json());

// Attach io to req for event triggers
app.use((req, res, next) => {
  req.io = io;
  next();
});

// API Routes
app.use('/api/auth', authRoutes);
app.use('/api/events', eventRoutes);
app.use('/api/zones', zoneRoutes);
app.use('/api/dashboard', dashboardRoutes);
app.use('/api/crowd', dashboardRoutes);
app.use('/api/intelligence', intelligenceRoutes);
app.use('/api/alerts', alertRoutes);
app.use('/api/analytics', analyticsRoutes);
app.use('/api/reports', reportRoutes);
app.use('/api/simulation', simulationRoutes);
app.use('/api/internal', internalRoutes); // Mounted internal endpoint (Prompt 5)
app.use('/api/incidents', incidentRoutes); // Feature 1: Incident Center
app.use('/api/emergency', emergencyRoutes); // Feature 2: Emergency Mode
app.use('/api/predictions', predictionRoutes); // Feature 3: AI Crowd Predictions

// Health Endpoint
app.get('/api/health', (req, res) => {
  res.json({
    status: 'online',
    timestamp: new Date().toISOString(),
    service: 'AI Campus Event Security Management API'
  });
});

// Initialize Socket.IO & Simulation Loop
io.on('connection', (socket) => {
  console.log(`[Socket.IO] Client connected: ${socket.id}`);

  // Send immediate status on connect
  socket.emit('simulation:status', simulationService.getSimulationStatus());

  socket.on('disconnect', () => {
    console.log(`[Socket.IO] Client disconnected: ${socket.id}`);
  });
});

const predictionEngine = require('./services/predictionEngine');
const dataStore = require('./services/dataStore');

// Start Simulation automatically
simulationService.initSimulation(io);

// Standing periodic prediction cycle (every 10s)
setInterval(() => {
  try {
    const activeEventId = dataStore.getActiveEventId();
    const zones = dataStore.getZones(activeEventId);
    if (zones && zones.length > 0) {
      predictionEngine.runPredictionCycle(io, zones, activeEventId, dataStore);
    }
  } catch (err) {
    // Silently continue
  }
}, 10000);

// Start Server
const PORT = process.env.PORT || 5000;
server.listen(PORT, () => {
  console.log(`====================================================`);
  console.log(` Campus Security Command Center API running on port ${PORT}`);
  console.log(` Internal ML Detection Endpoint: POST /api/internal/detections`);
  console.log(` Socket.IO real-time engine initialized`);
  console.log(`====================================================`);
});
