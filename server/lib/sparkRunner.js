const { spawn } = require('child_process');
const path = require('path');

function runSpark(io, projectRoot) {
  const pythonCmd = process.env.PYTHON_CMD || 'python';
  const scriptPath = path.join(projectRoot, 'capstone4_spark', '4_spark_pipeline.py');
  
  console.log(`Running Spark: ${pythonCmd} ${scriptPath}`);
  
  const proc = spawn(pythonCmd, [scriptPath], {
    cwd: projectRoot,
    shell: true, // Required for Windows
    env: { ...process.env, PYTHONUNBUFFERED: '1' }
  });
  
  io.emit('spark_start', { timestamp: new Date().toISOString() });

  proc.stdout.on('data', (data) => {
    const lines = data.toString().split('\n');
    lines.forEach(line => {
      if (line.trim()) {
        io.emit('spark_log', { line: line.trim(), type: 'stdout' });
      }
    });
  });
  
  proc.stderr.on('data', (data) => {
    const lines = data.toString().split('\n');
    lines.forEach(line => {
      if (line.trim()) {
        io.emit('spark_log', { line: line.trim(), type: 'stderr' });
      }
    });
  });
  
  proc.on('close', (code) => {
    console.log(`Spark process exited with code ${code}`);
    io.emit('spark_done', { exit_code: code, timestamp: new Date().toISOString() });
  });
  
  return proc;
}

module.exports = { runSpark };
