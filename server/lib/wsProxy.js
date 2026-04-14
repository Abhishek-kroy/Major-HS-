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
        
        // Store readings if present (FastAPI might send it or we get it from /predict proxy)
        if (payload.readings && payload.machine_id !== undefined) {
          this.machineBuffers[payload.machine_id] = payload.readings;
          this.io.emit('data_point', {
            machine_id: payload.machine_id,
            kwh: payload.kwh,
            recon_error: payload.recon_error,
            is_anomaly: payload.is_anomaly,
            timestamp: payload.timestamp || new Date().toISOString()
          });
        }

        if (payload.type === 'ANOMALY_ALARM') {
          this.anomalyBuffer.push(payload);
          this.io.emit('anomaly_event', payload);
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
