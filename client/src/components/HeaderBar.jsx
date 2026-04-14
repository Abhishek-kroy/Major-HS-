import React, { useState, useEffect } from 'react';
import { format } from 'date-fns';
import useStore from '../store/useStore';
import { Cpu, Activity, Zap, Radio } from 'lucide-react';

const HeaderBar = () => {
  const { wsConnected, fastApiOnline, sparkRunning } = useStore();
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="h-16 border-b border-border bg-surface flex items-center justify-between px-6 z-50">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded bg-primary/20 flex items-center justify-center border border-primary/50">
          <Zap className="text-primary w-5 h-5 fill-primary/20" />
        </div>
        <h1 className="text-xl font-bold font-mono tracking-tighter text-primary">
          ⬡ INDUSTRIAL DIGITAL TWIN
        </h1>
      </div>

      <div className="flex items-center gap-4">
        <StatusPill 
          label="EDGE AI" 
          status={fastApiOnline ? 'ONLINE' : 'OFFLINE'} 
          color={fastApiOnline ? 'text-success' : 'text-danger'}
          icon={<Cpu className="w-4 h-4" />}
        />
        <StatusPill 
          label="FASTAPI" 
          status={fastApiOnline ? 'ACTIVE' : 'DISCONNECTED'} 
          color={fastApiOnline ? 'text-success' : 'text-danger'}
          icon={<Activity className="w-4 h-4" />}
        />
        <StatusPill 
          label="SPARK" 
          status={sparkRunning ? 'RUNNING' : 'READY'} 
          color={sparkRunning ? 'text-warning animate-pulse' : 'text-primary'}
          icon={<Zap className="w-4 h-4" />}
        />
      </div>

      <div className="flex items-center gap-6">
        <div className="text-right">
          <div className="text-sm font-mono font-bold">
            {format(time, 'yyyy-MM-dd HH:mm:ss')} <span className="text-primary/70">UTC</span>
          </div>
        </div>
        <div className="flex items-center gap-2 bg-black/40 px-3 py-1.5 rounded-full border border-border">
          <div className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-success animate-pulse' : 'bg-danger'}`} />
          <span className="text-[10px] font-bold text-white/70 uppercase tracking-widest">
            {wsConnected ? 'Linked' : 'Offline'}
          </span>
        </div>
      </div>
    </div>
  );
};

const StatusPill = ({ label, status, color, icon }) => (
  <div className="flex items-center gap-2 bg-black/30 border border-border px-3 py-1.5 rounded-md">
    <div className={`${color} opacity-80`}>{icon}</div>
    <div className="flex flex-col leading-none">
      <span className="text-[9px] text-white/40 font-bold uppercase tracking-tighter">{label}</span>
      <span className={`text-[11px] font-bold font-mono ${color}`}>{status}</span>
    </div>
  </div>
);

export default HeaderBar;
