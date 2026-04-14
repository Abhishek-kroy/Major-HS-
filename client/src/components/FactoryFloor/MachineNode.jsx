import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertCircle, Zap, Activity } from 'lucide-react';
import useStore from '../../store/useStore';

const MachineNode = ({ id, x, y }) => {
  const machine = useStore(state => state.machines[id]);
  const selected = useStore(state => state.selectedMachine === id);
  const setSelectedMachine = useStore(state => state.setSelectedMachine);
  const [pulse, setPulse] = useState(false);
  const [showShockwave, setShowShockwave] = useState(false);

  useEffect(() => {
    if (machine?.kwh !== 0) {
      setPulse(true);
      setTimeout(() => setPulse(false), 200);
    }
    if (machine?.is_anomaly) {
      setShowShockwave(true);
      setTimeout(() => setShowShockwave(false), 600);
    }
  }, [machine?.last_updated, machine?.is_anomaly]);

  const isAnomaly = machine?.is_anomaly;
  const isBreakdown = machine?.status === 'SPIKE INJECTING';

  return (
    <div 
      className="absolute"
      style={{ left: x, top: y }}
    >
      <AnimatePresence>
        {showShockwave && <div className="shockwave" style={{ left: '40px', top: '40px' }} />}
      </AnimatePresence>

      <motion.div
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={() => setSelectedMachine(id)}
        className={`w-20 h-20 rounded-xl border-2 flex flex-col items-center justify-center cursor-pointer transition-colors relative
          ${selected ? 'border-primary ring-2 ring-primary/30' : 'border-border'}
          ${isAnomaly ? 'bg-danger/10 border-danger animate-anomaly' : 'bg-surface'}
          ${isBreakdown ? 'animate-bounce' : ''}
        `}
      >
        <span className="text-[10px] font-bold text-white/50 absolute top-1 left-2">M-{id}</span>
        
        <div className={`transition-transform duration-200 ${pulse ? 'scale-110' : 'scale-100'}`}>
          {isAnomaly ? (
            <AlertCircle className="w-6 h-6 text-danger" />
          ) : (
            <Zap className={`w-6 h-6 ${pulse ? 'text-primary' : 'text-white/20'}`} />
          )}
        </div>

        <div className="mt-1 flex flex-col items-center">
          <span className="text-[12px] font-mono font-bold">
            {machine?.kwh?.toFixed(1) || '0.0'}
          </span>
          <span className={`text-[8px] font-bold uppercase tracking-tighter ${isAnomaly ? 'text-danger' : 'text-success'}`}>
            {machine?.status || 'IDLE'}
          </span>
        </div>

        {/* Breakdown Injection Hover Button */}
        <div className="absolute -bottom-8 opacity-0 group-hover:opacity-100 transition-opacity">
           <button className="bg-danger/20 border border-danger/50 text-danger text-[9px] font-bold px-2 py-1 rounded">
             INJECT
           </button>
        </div>
      </motion.div>
    </div>
  );
};

export default MachineNode;
