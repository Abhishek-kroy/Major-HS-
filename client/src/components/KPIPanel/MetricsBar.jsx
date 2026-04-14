import React from 'react';
import useStore from '../../store/useStore';

const MetricsBar = () => {
  const metrics = useStore(state => state.serverMetrics);

  const items = [
    { label: 'Total Requests', value: metrics.total_requests || 0 },
    { label: 'Anomalies', value: metrics.total_anomalies || 0 },
    { label: 'Anomaly Rate', value: `${(metrics.anomaly_rate_pct || 0).toFixed(2)}%` },
    { label: 'Avg Latency', value: `${(metrics.avg_latency_ms || 0).toFixed(2)}ms` },
    { label: 'Uptime', value: formatUptime(metrics.uptime_seconds) },
  ];

  return (
    <div className="grid grid-cols-5 gap-4 mb-6">
      {items.map((item, i) => (
        <div key={i} className="bg-surface border border-border p-4 rounded-lg">
          <div className="text-[10px] font-bold text-white/30 uppercase tracking-widest mb-1">{item.label}</div>
          <div className="text-xl font-mono font-bold text-primary">{item.value}</div>
        </div>
      ))}
    </div>
  );
};

function formatUptime(seconds) {
  if (!seconds) return '00:00:00';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return [h, m, s].map(v => v.toString().padStart(2, '0')).join(':');
}

export default MetricsBar;
