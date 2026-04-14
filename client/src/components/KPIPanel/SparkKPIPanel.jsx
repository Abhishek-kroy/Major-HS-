import React, { useEffect } from 'react';
import useStore from '../../store/useStore';
import MetricsBar from './MetricsBar';
import axios from 'axios';

const SparkKPIPanel = () => {
  const { sparkKPIs, setSparkKPIs, sparkRunning } = useStore();

  useEffect(() => {
    const fetchKPIs = async () => {
      try {
        const res = await axios.get('/api/spark/kpis');
        setSparkKPIs(res.data);
      } catch (err) {
        console.error('Failed to fetch Spark KPIs', err);
      }
    };
    fetchKPIs();
  }, []);

  return (
    <div className="p-6 bg-background">
      <MetricsBar />
      
      <div className="bg-surface border border-border rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-border flex justify-between items-center">
          <h3 className="text-sm font-bold uppercase tracking-widest text-primary/70">Spark Analytics: Machine KPIs</h3>
          {sparkRunning && (
             <div className="text-[10px] text-warning flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-warning animate-pulse" />
                UPDATING...
             </div>
          )}
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm border-collapse">
            <thead className="bg-black/20 text-white/40 uppercase text-[10px] font-bold">
              <tr>
                <th className="px-6 py-3 border-b border-border">Machine</th>
                <th className="px-6 py-3 border-b border-border">Total Readings</th>
                <th className="px-6 py-3 border-b border-border">Avg kWh</th>
                <th className="px-6 py-3 border-b border-border">Peak kWh</th>
                <th className="px-6 py-3 border-b border-border">P95 kWh</th>
                <th className="px-6 py-3 border-b border-border text-right">Anomaly Rate</th>
              </tr>
            </thead>
            <tbody className="font-mono">
              {sparkKPIs.length === 0 ? (
                <tr>
                  <td colSpan="6" className="px-6 py-12 text-center text-white/20 uppercase tracking-widest text-[11px]">
                    {sparkRunning ? 'Computing Spark Analytics...' : 'Run Spark pipeline to populate KPIs'}
                  </td>
                </tr>
              ) : (
                sparkKPIs.map((kpi, i) => (
                  <tr key={i} className="hover:bg-white/5 transition-colors border-b border-white/5">
                    <td className="px-6 py-4 font-bold text-primary">M-{kpi.machine_id}</td>
                    <td className="px-6 py-4 text-white/70">{kpi.total_readings}</td>
                    <td className="px-6 py-4 text-white/70">{parseFloat(kpi.avg_kwh || 0).toFixed(1)}</td>
                    <td className="px-6 py-4 text-white/70">{parseFloat(kpi.peak_kwh || 0).toFixed(1)}</td>
                    <td className="px-6 py-4 text-white/70">{parseFloat(kpi.p95_kwh || 0).toFixed(1)}</td>
                    <td className="px-6 py-4 text-right font-bold ${getRateColor(kpi.anomaly_rate_pct || 0)}">
                      {((kpi.anomaly_rate_pct || 0) * 100).toFixed(1)}%
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

function getRateColor(rate) {
    const p = rate * 100;
    if (p < 2) return 'text-success';
    if (p < 5) return 'text-warning';
    return 'text-danger';
}

export default SparkKPIPanel;
