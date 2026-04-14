const express = require('express');
const axios = require('axios');
const router = express.Router();

router.get('/', async (req, res) => {
  try {
    const fastApiUrl = process.env.FASTAPI_URL || 'http://localhost:8000';
    const response = await axios.get(`${fastApiUrl}/health`);
    res.json(response.data);
  } catch (err) {
    // Return offline status instead of error
    res.json({ status: 'offline', model_loaded: false });
  }
});

module.exports = router;
