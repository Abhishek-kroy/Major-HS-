require('dotenv').config();
const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const cors = require('cors');
const axios = require('axios');
const RingBuffer = require('./lib/ringBuffer');
const WSProxy = require('./lib/wsProxy');

const app = express();
const server = http.createServer(app);
const io = new Server(server, {
  cors: {
    origin: "*",
    methods: ["GET", "POST"]
  }
});

app.use(cors());
app.use(express.json());

const PORT = process.env.PORT || 3001;

// Shared state
const machineBuffers = {
  0: Array(24).fill(150),
  1: Array(24).fill(150),
  2: Array(24).fill(150),
  3: Array(24).fill(150),
  4: Array(24).fill(150),
};
const activeBreakdowns = {};
const anomalyBuffer = new RingBuffer(200);

// Initialize WS Proxy
new WSProxy(process.env.FASTAPI_URL, io, anomalyBuffer, machineBuffers);

// Proxy route for predictions
app.post('/api/predict-proxy', async (req, res) => {
  try {
    const fastApiUrl = process.env.FASTAPI_URL || 'http://localhost:8000';
    const response = await axios.post(`${fastApiUrl}/predict`, req.body);
    const data = response.data;
    
    // Emit every reading to frontend (this populates the live chart)
    io.emit('data_point', {
      machine_id: req.body.machine_id,
      kwh: req.body.readings[23],
      recon_error: data.recon_error,
      is_anomaly: data.is_anomaly,
      threshold: data.threshold,
      timestamp: data.timestamp
    });
    
    // Emit anomaly events separately for the feed
    if (data.is_anomaly) {
      io.emit('anomaly_event', {
        machine_id: req.body.machine_id,
        kwh: req.body.readings[23],
        recon_error: data.recon_error,
        threshold: data.threshold,
        timestamp: data.timestamp,
        alert: data.alert,
        breakdown_simulated: activeBreakdowns[req.body.machine_id] != null
      });
    }
    
    res.json(data);
  } catch (err) {
    res.status(503).json({ error: 'FastAPI unreachable', detail: err.message });
  }
});

// Routes
app.use('/api/health', require('./routes/health'));
app.use('/api/metrics', require('./routes/metrics'));
app.use('/api/anomalies', require('./routes/anomalies'));
app.use('/api/spark', require('./routes/spark')(io));
app.use('/api/simulate', require('./routes/simulate')(io, machineBuffers, activeBreakdowns));

// Socket.io connection
io.on('connection', (socket) => {
  console.log('Client connected:', socket.id);
  
  // Send last anomalies to late joiners
  socket.emit('initial_anomalies', anomalyBuffer.getAll());

  socket.on('disconnect', () => {
    console.log('Client disconnected:', socket.id);
  });
});

// Start server
server.listen(PORT, () => {
  console.log(`Node server running on port ${PORT}`);
});
