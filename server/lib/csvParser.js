const { parse } = require('csv-parse/sync');
const fs = require('fs');
const path = require('path');

function getSparkKPIs(projectRoot) {
  try {
    const kpiDir = path.join(projectRoot, 'spark_output', 'machine_kpis');
    if (!fs.existsSync(kpiDir)) return [];
    
    const files = fs.readdirSync(kpiDir).filter(f => f.endsWith('.csv'));
    if (files.length === 0) return [];
    
    // Read the most recent or the only one
    const content = fs.readFileSync(path.join(kpiDir, files[0]), 'utf8');
    return parse(content, { columns: true, skip_empty_lines: true });
  } catch (err) {
    console.error('Error parsing Spark KPIs:', err);
    return [];
  }
}

function getSparkMonthly(projectRoot) {
  try {
    const trendDir = path.join(projectRoot, 'spark_output', 'monthly_trends');
    if (!fs.existsSync(trendDir)) return [];
    
    const files = fs.readdirSync(trendDir).filter(f => f.endsWith('.csv'));
    if (files.length === 0) return [];
    
    const content = fs.readFileSync(path.join(trendDir, files[0]), 'utf8');
    return parse(content, { columns: true, skip_empty_lines: true });
  } catch (err) {
    console.error('Error parsing Spark Monthly Trends:', err);
    return [];
  }
}

module.exports = { getSparkKPIs, getSparkMonthly };
