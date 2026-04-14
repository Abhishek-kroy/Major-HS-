import React from 'react';
import { motion } from 'framer-motion';
import { AlertTriangle, Clock, Zap } from 'lucide-react';
import { format } from 'date-fns';

const AnomalyCard = ({ event }) => {
  return (
    <motion.div
      initial={{ x: 50, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      className={`p-4 border-l-4 rounded-r-md mb-3 relative overflow-hidden
        ${event.breakdown_simulated ? 'bg-purple-900/10 border-purple-500' : 'bg-danger/5 border-danger'}
        border-y border-r border-border/50
      `}
    >
      <div className="flex justify-between items-start mb-2">
        <div className="flex items-center gap-2">
          <AlertTriangle className={`w-4 h-4 ${event.breakdown_simulated ? 'text-purple-400' : 'text-danger'}`} />
          <span className={`text-xs font-bold uppercase tracking-wider ${event.breakdown_simulated ? 'text-purple-400' : 'text-danger'}`}>
             ANOMALY DETECTED
          </span>
        </div>
        <div className="flex items-center gap-1 text-[10px] text-white/40 font-mono">
          <Clock className="w-3 h-3" />
          {format(new Date(event.timestamp), 'HH:mm:ss')} UTC
        </div>
      </div>

      <div className="grid grid-cols-2 gap-y-2 text-[11px]">
        <div className="flex flex-col">
          <span className="text-white/30 uppercase font-bold text-[9px]">Machine</span>
          <span className="font-bold text-white/90">M-{event.machine_id}</span>
        </div>
        <div className="flex flex-col">
          <span className="text-white/30 uppercase font-bold text-[9px]">Actual kWh</span>
          <span className="font-bold text-white/90 font-mono">{event.kwh.toFixed(2)}</span>
        </div>
        <div className="flex flex-col">
          <span className="text-white/30 uppercase font-bold text-[9px]">Recon Error</span>
          <span className="font-bold text-warning font-mono">{event.recon_error.toFixed(4)}</span>
        </div>
        <div className="flex flex-col">
          <span className="text-white/30 uppercase font-bold text-[9px]">Threshold</span>
          <span className="font-bold text-white/50 font-mono">{event.threshold?.toFixed(4) || '0.0979'}</span>
        </div>
      </div>

      <div className="mt-3 pt-2 border-t border-white/5 flex items-center justify-between">
         <span className="text-[10px] text-white/40 italic">
           Reason: {event.recon_error.toFixed(4)} &gt; threshold
         </span>
         {event.breakdown_simulated && (
           <span className="bg-purple-500/20 text-purple-400 text-[8px] font-bold px-1.5 py-0.5 rounded border border-purple-500/30">
             🧪 SIMULATED
           </span>
         )}
      </div>
    </motion.div>
  );
};

export default AnomalyCard;
