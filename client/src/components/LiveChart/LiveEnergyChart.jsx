import React from 'react';
import { 
  ComposedChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer, 
  ReferenceLine,
  Scatter,
  Area
} from 'recharts';
import useStore from '../../store/useStore';

const LiveEnergyChart = () => {
  const selectedMachine = useStore(state => state.selectedMachine);
  const data = useStore(state => state.machineTimeSeries[selectedMachine] || []);
  const threshold = 0.0979; // Hardcoded as per spec or fetched from somewhere

  const lastReading = data[data.length - 1];

  return (
    <div className="flex-1 bg-surface border-x border-border p-6 flex flex-col min-h-0">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-bold font-mono text-white/90">
            Machine M-{selectedMachine} › Live Feed
          </h2>
          <div className="flex items-center gap-2 px-2 py-0.5 bg-success/10 border border-success/30 rounded">
            <div className="w-1.5 h-1.5 rounded-full bg-success animate-pulse" />
            <span className="text-[10px] font-bold text-success uppercase">Live</span>
          </div>
        </div>
        <div className="flex items-center gap-6">
          <div className="flex flex-col items-end leading-none">
            <span className="text-[10px] text-white/40 uppercase font-bold">Threshold</span>
            <span className="text-xs font-mono font-bold text-warning">{threshold}</span>
          </div>
          <div className="flex flex-col items-end leading-none">
            <span className="text-[10px] text-white/40 uppercase font-bold">Readings</span>
            <span className="text-xs font-mono font-bold text-primary">{data.length}</span>
          </div>
        </div>
      </div>

      <div className="flex-1 flex flex-col gap-4">
        {/* kWh Chart */}
        <div className="flex-[0.7] relative">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e2530" vertical={false} />
              <XAxis 
                dataKey="timestamp" 
                hide 
              />
              <YAxis 
                stroke="#4a5568" 
                fontSize={10} 
                tickFormatter={(val) => val.toFixed(0)}
                domain={['auto', 'auto']}
              />
              <Tooltip 
                contentStyle={{ backgroundColor: '#0f1318', border: '1px solid #1e2530', fontSize: '12px' }}
                itemStyle={{ color: '#00d4ff' }}
              />
              <Area 
                type="monotone" 
                dataKey="kwh" 
                stroke="#00d4ff" 
                fill="url(#colorKwh)" 
                strokeWidth={2}
                isAnimationActive={false}
              />
              <Scatter 
                data={data.filter(d => d.is_anomaly)} 
                fill="#ff3b3b" 
                r={4}
              />
              <defs>
                <linearGradient id="colorKwh" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#00d4ff" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#00d4ff" stopOpacity={0}/>
                </linearGradient>
              </defs>
            </ComposedChart>
          </ResponsiveContainer>
          <div className="absolute top-2 left-2 text-[10px] font-bold text-white/30 uppercase tracking-tighter">Energy Consumption (kWh)</div>
        </div>

        {/* Recon Error Chart */}
        <div className="flex-[0.3] relative border-t border-border pt-4">
           <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e2530" vertical={false} />
              <XAxis dataKey="timestamp" hide />
              <YAxis 
                stroke="#4a5568" 
                fontSize={10} 
                tickFormatter={(val) => val.toFixed(3)}
              />
              <Tooltip 
                contentStyle={{ backgroundColor: '#0f1318', border: '1px solid #1e2530', fontSize: '12px' }}
              />
              <Line 
                type="monotone" 
                dataKey="recon_error" 
                stroke="#7b61ff" 
                strokeWidth={1} 
                dot={false}
                isAnimationActive={false}
              />
              <ReferenceLine y={threshold} stroke="#ffab00" strokeDasharray="3 3" />
            </ComposedChart>
          </ResponsiveContainer>
          <div className="absolute top-6 left-2 text-[10px] font-bold text-white/30 uppercase tracking-tighter text-purple-400">Reconstruction Error</div>
        </div>
      </div>
    </div>
  );
};

export default LiveEnergyChart;
