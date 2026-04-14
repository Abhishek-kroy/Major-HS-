import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';

const CustomNode = ({ data }) => {
  return (
    <div className={`px-4 py-3 shadow-md rounded-md bg-surface border-2 ${data.isAnomaly ? 'border-danger animate-anomaly' : 'border-border'} min-w-[150px]`}>
      <div className="flex items-center">
        <div className="rounded-full w-8 h-8 flex items-center justify-center bg-black/30 text-lg mr-2">
          {data.icon}
        </div>
        <div className="ml-2">
          <div className="text-xs font-bold text-white/90 uppercase tracking-tighter">{data.label}</div>
          <div className={`text-[9px] font-bold ${data.statusColor || 'text-success'}`}>
             {data.status || 'ACTIVE'}
          </div>
        </div>
      </div>
      
      {data.preview && (
        <div className="mt-2 pt-2 border-t border-white/5 font-mono text-[8px] text-white/40 truncate">
          {data.preview}
        </div>
      )}

      {data.inputs && data.inputs.map((input, i) => (
        <Handle
          key={i}
          type="target"
          position={Position.Left}
          id={input.id}
          style={{ background: '#555' }}
        />
      ))}
      
      {data.outputs && data.outputs.map((output, i) => (
        <Handle
          key={i}
          type="source"
          position={Position.Right}
          id={output.id}
          style={{ background: '#555' }}
        />
      ))}
    </div>
  );
};

export default memo(CustomNode);
