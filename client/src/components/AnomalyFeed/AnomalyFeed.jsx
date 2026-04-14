import React, { useState } from 'react';
import useStore from '../../store/useStore';
import AnomalyCard from './AnomalyCard';
import { Filter, Trash2 } from 'lucide-react';

const AnomalyFeed = () => {
  const [filter, setFilter] = useState('ALL');
  const events = useStore(state => state.anomalyEvents);

  const filteredEvents = filter === 'ALL' 
    ? events 
    : events.filter(e => e.machine_id.toString() === filter.replace('M-', ''));

  return (
    <div className="w-80 bg-surface flex flex-col border-l border-border min-h-0">
      <div className="p-4 border-b border-border flex items-center justify-between">
        <div className="flex items-center gap-2">
            <h2 className="text-xs font-bold uppercase tracking-widest text-white/50">Anomaly Feed</h2>
            <span className="bg-danger/20 text-danger text-[10px] font-bold px-2 py-0.5 rounded-full">
                {filteredEvents.length}
            </span>
        </div>
        <div className="flex items-center gap-2">
            <select 
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                className="bg-black/40 border border-border text-[10px] text-white/70 px-2 py-1 rounded outline-none cursor-pointer"
            >
                <option value="ALL">ALL MACHINES</option>
                <option value="M-0">M-0</option>
                <option value="M-1">M-1</option>
                <option value="M-2">M-2</option>
                <option value="M-3">M-3</option>
                <option value="M-4">M-4</option>
            </select>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
        {filteredEvents.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-white/10 gap-3">
             <Filter className="w-12 h-12" />
             <span className="text-[10px] font-bold uppercase tracking-widest">No anomalies detected</span>
          </div>
        ) : (
          filteredEvents.map((event, idx) => (
            <AnomalyCard key={`${event.timestamp}-${idx}`} event={event} />
          ))
        )}
      </div>
    </div>
  );
};

export default AnomalyFeed;
