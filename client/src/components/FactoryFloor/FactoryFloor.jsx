import React from 'react';
import MachineNode from './MachineNode';
import useStore from '../../store/useStore';
import axios from 'axios';

const FactoryFloor = () => {
  const machinePositions = [
    { id: 0, x: 50, y: 50 },
    { id: 1, x: 200, y: 50 },
    { id: 2, x: 350, y: 50 },
    { id: 3, x: 125, y: 180 },
    { id: 4, x: 275, y: 180 },
  ];

  const handleInject = async (id) => {
    if (window.confirm(`Injecting artificial power spike into Machine M-${id}. This will simulate a motor bearing failure. Proceed?`)) {
      try {
        await axios.post('/api/simulate/breakdown', { machine_id: id });
      } catch (err) {
        console.error('Failed to inject breakdown', err);
      }
    }
  };

  return (
    <div className="flex-1 bg-surface p-6 flex flex-col min-h-0">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xs font-bold uppercase tracking-widest text-primary/70">Factory Floor Map</h2>
        <div className="flex gap-2">
            <span className="text-[10px] text-white/30 flex items-center gap-1">
                <div className="w-1.5 h-1.5 rounded-full bg-success"/> NORMAL
            </span>
            <span className="text-[10px] text-white/30 flex items-center gap-1">
                <div className="w-1.5 h-1.5 rounded-full bg-danger"/> ANOMALY
            </span>
        </div>
      </div>
      
      <div className="flex-1 border border-border rounded-xl relative scada-grid overflow-hidden group">
        {machinePositions.map(pos => (
          <div key={pos.id} className="relative group/machine">
             <MachineNode {...pos} />
             <div className="absolute opacity-0 group-hover/machine:opacity-100 transition-opacity" 
                  style={{ left: pos.x + 10, top: pos.y + 85 }}>
                <button 
                  onClick={() => handleInject(pos.id)}
                  className="bg-danger/80 hover:bg-danger text-white text-[9px] font-bold px-3 py-1 rounded-full border border-danger/50 shadow-lg shadow-danger/20"
                >
                  INJECT BREAKDOWN
                </button>
             </div>
          </div>
        ))}
        
        {/* Decorative Power Lines */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none opacity-20">
            <path d="M 90 90 L 125 180" stroke="currentColor" strokeWidth="1" fill="none" className="text-primary"/>
            <path d="M 240 90 L 165 180" stroke="currentColor" strokeWidth="1" fill="none" className="text-primary"/>
            <path d="M 390 90 L 315 180" stroke="currentColor" strokeWidth="1" fill="none" className="text-primary"/>
        </svg>

        <div className="absolute inset-0 pointer-events-none scanline" />
      </div>
    </div>
  );
};

export default FactoryFloor;
