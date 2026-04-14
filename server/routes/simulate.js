const express = require('express');
const axios = require('axios');
const router = express.Router();

const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

module.exports = (io, machineBuffers) => {
  router.post('/breakdown', async (req, res) => {
    const { machine_id } = req.body;
    console.log(`Injecting breakdown for machine ${machine_id}`);

    io.emit('breakdown_injected', { machine_id, timestamp: new Date().toISOString() });

    // Simulation logic
    const fastApiUrl = process.env.FASTAPI_URL || 'http://localhost:8000';
    
    // Get last readings for this machine
    const baseReadings = machineBuffers[machine_id] || Array(24).fill(150.0);
    
    // Fire 10 spiked readings
    (async () => {
      for (let i = 0; i < 10; i++) {
        // Multiply readings by 3.0 to simulate breakdown
        const spikedReadings = baseReadings.map(r => r * 3.0);
        try {
          await axios.post(`${fastApiUrl}/predict`, {
            machine_id: parseInt(machine_id),
            readings: spikedReadings,
            predicted_kwh: baseReadings[23] * 1.05
          });
        } catch (err) {
          console.error('Error injecting breakdown reading:', err.message);
        }
        await sleep(500);
      }
    })();

    res.json({ message: `Breakdown injected for machine ${machine_id}` });
  });

  return router;
};
