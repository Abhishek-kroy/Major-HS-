const express = require('express');
const axios = require('axios');
const router = express.Router();

router.get('/', async (req, res) => {
  try {
    const fastApiUrl = process.env.FASTAPI_URL || 'http://localhost:8000';
    const response = await axios.get(`${fastApiUrl}/metrics`);
    res.json(response.data);
  } catch (err) {
    console.error('Error fetching metrics from FastAPI:', err.message);
    res.status(500).json({ error: 'Failed to fetch metrics' });
  }
});

module.exports = router;
