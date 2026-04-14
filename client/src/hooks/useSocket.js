import { useEffect, useRef } from 'react';
import { io } from 'socket.io-client';
import useStore from '../store/useStore';

const useSocket = () => {
  const socketRef = useRef();
  const { 
    setWsConnected, 
    addDataPoint, 
    addAnomalyEvent, 
    appendSparkLog, 
    setSparkRunning,
    updateMachineStatus,
    setSparkKPIs
  } = useStore();

  useEffect(() => {
    const socket = io('/', {
      path: '/socket.io'
    });
    socketRef.current = socket;

    socket.on('connect', () => {
      console.log('Connected to Node server');
      setWsConnected(true);
    });

    socket.on('disconnect', () => {
      console.log('Disconnected from Node server');
      setWsConnected(false);
    });

    socket.on('data_point', (point) => {
      addDataPoint(point.machine_id, point);
    });

    socket.on('anomaly_event', (event) => {
      addAnomalyEvent(event);
      // Also ensure data point is added if not already
      addDataPoint(event.machine_id, {
        machine_id: event.machine_id,
        kwh: event.kwh,
        recon_error: event.recon_error,
        is_anomaly: event.is_anomaly,
        timestamp: event.timestamp
      });
    });

    socket.on('breakdown_injected', ({ machine_id }) => {
      updateMachineStatus(machine_id, 'SPIKE INJECTING');
    });

    socket.on('spark_start', () => {
      setSparkRunning(true);
    });

    socket.on('spark_log', (log) => {
      appendSparkLog(log);
    });

    socket.on('spark_done', () => {
      setSparkRunning(false);
      // Trigger KPI refresh
      fetch('/api/spark/kpis')
        .then(res => res.json())
        .then(kpis => setSparkKPIs(kpis));
    });

    socket.on('initial_anomalies', (anomalies) => {
      anomalies.forEach(a => addAnomalyEvent(a));
    });

    return () => {
      socket.disconnect();
    };
  }, []);

  return socketRef.current;
};

export default useSocket;
