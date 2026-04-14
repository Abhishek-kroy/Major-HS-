import React, { useEffect, useRef } from 'react';
import useStore from '../../store/useStore';
import AnsiToHtml from 'ansi-to-html';

const converter = new AnsiToHtml();

const SparkConsole = ({ onClose }) => {
  const logs = useStore(state => state.sparkLogs);
  const scrollRef = useRef();

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div className="h-full bg-black border-t border-border flex flex-col font-mono text-[10px]">
      <div className="flex items-center justify-between px-4 py-1.5 bg-surface border-b border-border">
        <span className="text-white/40 font-bold uppercase tracking-widest text-[9px]">Spark Execution Console</span>
        <button onClick={onClose} className="text-white/20 hover:text-white">✕</button>
      </div>
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-4 custom-scrollbar"
      >
        {logs.length === 0 ? (
          <div className="text-white/20">Waiting for Spark execution...</div>
        ) : (
          logs.map((log, i) => (
            <div 
              key={i} 
              className={`mb-1 ${log.type === 'stderr' ? 'text-danger' : 'text-success/80'}`}
              dangerouslySetInnerHTML={{ __html: converter.parse(log.line) }}
            />
          ))
        )}
      </div>
    </div>
  );
};

export default SparkConsole;
