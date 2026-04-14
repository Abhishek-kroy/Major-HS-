import { create } from 'zustand';

const useStore = create((set) => ({
  // Connection state
  wsConnected: false,
  fastApiOnline: false,
  sparkRunning: false,
  setWsConnected: (connected) => set({ wsConnected: connected }),
  setFastApiOnline: (online) => set({ fastApiOnline: online }),
  setSparkRunning: (running) => set({ sparkRunning: running }),

  // Machine state — keyed by machine_id 0..4
  machines: {
    0: { kwh: 0, is_anomaly: false, recon_error: 0, last_updated: null, status: 'IDLE' },
    1: { kwh: 0, is_anomaly: false, recon_error: 0, last_updated: null, status: 'IDLE' },
    2: { kwh: 0, is_anomaly: false, recon_error: 0, last_updated: null, status: 'IDLE' },
    3: { kwh: 0, is_anomaly: false, recon_error: 0, last_updated: null, status: 'IDLE' },
    4: { kwh: 0, is_anomaly: false, recon_error: 0, last_updated: null, status: 'IDLE' }
  },
  
  // Selected machine for detail view
  selectedMachine: 0,
  setSelectedMachine: (id) => set({ selectedMachine: id }),

  // Time-series data per machine (rolling 200 points)
  machineTimeSeries: {
    0: [], 1: [], 2: [], 3: [], 4: []
  },
  
  // Anomaly event log (last 200)
  anomalyEvents: [],
  
  // Active breakdowns
  activeBreakdowns: {},  // { machine_id: { start_time, readings_remaining } }
  
  // FastAPI metrics
  serverMetrics: { total_requests: 0, total_anomalies: 0, anomaly_rate_pct: 0, avg_latency_ms: 0, uptime_seconds: 0 },
  
  // Spark KPIs
  sparkKPIs: [],
  sparkLogs: [],

  // Actions
  addDataPoint: (machine_id, point) => set((state) => {
    const updatedSeries = [...state.machineTimeSeries[machine_id], point].slice(-200);
    return {
      machines: {
        ...state.machines,
        [machine_id]: {
          ...state.machines[machine_id],
          kwh: point.kwh,
          is_anomaly: point.is_anomaly,
          recon_error: point.recon_error,
          last_updated: point.timestamp,
          status: point.is_anomaly ? 'ANOMALY' : 'NORMAL'
        }
      },
      machineTimeSeries: {
        ...state.machineTimeSeries,
        [machine_id]: updatedSeries
      }
    };
  }),

  addAnomalyEvent: (event) => set((state) => ({
    anomalyEvents: [event, ...state.anomalyEvents].slice(0, 200)
  })),

  updateMachineStatus: (machine_id, status) => set((state) => ({
    machines: {
      ...state.machines,
      [machine_id]: { ...state.machines[machine_id], status }
    }
  })),

  setServerMetrics: (metrics) => set({ serverMetrics: metrics }),
  
  setSparkKPIs: (kpis) => set({ sparkKPIs: kpis }),
  
  appendSparkLog: (log) => set((state) => ({
    sparkLogs: [...state.sparkLogs, log]
  })),

  clearSparkLogs: () => set({ sparkLogs: [] }),

  injectBreakdown: (machine_id) => set((state) => ({
    activeBreakdowns: {
      ...state.activeBreakdowns,
      [machine_id]: { start_time: new Date().toISOString(), readings_remaining: 10 }
    }
  }))
}));

export default useStore;
