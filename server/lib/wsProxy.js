const { WebSocket } = require('ws');

class WSProxy {
  constructor(fastApiUrl, io, anomalyBuffer, machineBuffers) {
    this.fastApiUrl = (fastApiUrl || 'http://localhost:8000').replace('http', 'ws') + '/ws';
    this.io = io;
    this.anomalyBuffer = anomalyBuffer;
    this.machineBuffers = machineBuffers;
    this.connect();
  }

  connect() {
    console.log(`Connecting to FastAPI WebSocket: ${this.fastApiUrl}`);
    this.ws = new WebSocket(this.fastApiUrl);

    this.ws.on('open', () => {
      console.log('Connected to FastAPI WebSocket');
    });

    this.ws.on('message', (data) => {
      try {
        const payload = JSON.parse(data);
        
        // Store readings if present
        if (payload.readings && payload.machine_id !== undefined) {
          this.machineBuffers[payload.machine_id] = payload.readings;
          this.io.emit('data_point', {
            machine_id: payload.machine_id,
            kwh: payload.kwh || payload.readings[payload.readings.length - 1],
            recon_error: payload.recon_error || payload.error,
            is_anomaly: payload.is_anomaly || payload.type === 'ANOMALY_ALARM',
            timestamp: payload.timestamp || new Date().toISOString()
          });
        }

        if (payload.type === 'ANOMALY_ALARM') {
          // Normalize payload for frontend before pushing to buffer and emitting
          const normalized = {
            machine_id: payload.machine_id,
            kwh: payload.kwh || 0, // Fallback if kwh not in WS stream
            recon_error: payload.error || payload.recon_error || 0,
            threshold: payload.threshold || 0.0979,
            timestamp: payload.timestamp || new Date().toISOString(),
            is_anomaly: true,
            alert: { sent: true },
            breakdown_simulated: false
          };
          
          this.anomalyBuffer.push(normalized);
          this.io.emit('anomaly_event', normalized);
        }
      } catch (err) {
        console.error('Error parsing WebSocket message:', err);
      }
    });

    this.ws.on('close', () => {
      console.log('FastAPI WebSocket closed. Reconnecting in 3s...');
      setTimeout(() => this.connect(), 3000);
    });

    this.ws.on('error', (err) => {
      console.error('FastAPI WebSocket error:', err.message);
    });
  }
}

module.exports = WSProxy;
