const express = require('express');
const router = express.Router();
const { runSpark } = require('../lib/sparkRunner');
const { getSparkKPIs, getSparkMonthly } = require('../lib/csvParser');

module.exports = (io) => {
  router.post('/run', (req, res) => {
    const projectRoot = process.env.PROJECT_ROOT;
    runSpark(io, projectRoot);
    res.json({ message: 'Spark pipeline started' });
  });

  router.get('/kpis', (req, res) => {
    const projectRoot = process.env.PROJECT_ROOT;
    const kpis = getSparkKPIs(projectRoot);
    res.json(kpis);
  });

  router.get('/monthly', (req, res) => {
    const projectRoot = process.env.PROJECT_ROOT;
    const monthly = getSparkMonthly(projectRoot);
    res.json(monthly);
  });

  return router;
};
