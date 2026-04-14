const express = require('express');
const axios = require('axios');
const router = express.Router();

router.get('/', async (req, res) => {
  try {
    const fastApiUrl = process.env.FASTAPI_URL || 'http://localhost:8000';
    const response = await axios.get(`${fastApiUrl}/anomalies`, {
      params: { last_n: req.query.last_n || 100 }
    });
    res.json(response.data);
  } catch (err) {
    console.error('Error fetching anomalies from FastAPI:', err.message);
    res.status(500).json({ error: 'Failed to fetch anomalies' });
  }
});

module.exports = router;
