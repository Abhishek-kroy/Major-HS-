import React from 'react';
import HeaderBar from './components/HeaderBar';
import FactoryFloor from './components/FactoryFloor/FactoryFloor';
import LiveEnergyChart from './components/LiveChart/LiveEnergyChart';
import AnomalyFeed from './components/AnomalyFeed/AnomalyFeed';
import PipelineFlow from './components/PipelineFlow/PipelineFlow';
import SparkKPIPanel from './components/KPIPanel/SparkKPIPanel';
import useSocket from './hooks/useSocket';
import useHealthPoll from './hooks/useHealthPoll';
import useMetricsPoll from './hooks/useMetricsPoll';
import useStore from './store/useStore';

function App() {
  // Initialize hooks
  useSocket();
  useHealthPoll();
  useMetricsPoll();

  const fastApiOnline = useStore(state => state.fastApiOnline);

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-background">
      <HeaderBar />
      
      <main className="flex-1 flex flex-col min-h-0 relative">
        {/* Connection Overlay */}
        {!fastApiOnline && (
          <div className="absolute inset-x-0 top-0 bottom-0 z-[100] bg-background/80 backdrop-blur-sm flex items-center justify-center">
            <div className="bg-surface border border-danger/50 p-8 rounded-xl shadow-2xl flex flex-col items-center gap-4 text-center">
              <div className="w-12 h-12 border-4 border-danger border-t-transparent rounded-full animate-spin" />
              <div className="flex flex-col gap-1">
                <h2 className="text-xl font-bold text-danger uppercase tracking-tighter">System Disconnected</h2>
                <p className="text-white/40 text-xs">Awaiting connection to FastAPI Inference Server...</p>
              </div>
              <div className="mt-4 px-4 py-2 bg-danger/10 border border-danger/20 rounded text-[10px] font-mono text-danger">
                ws://localhost:8000/ws
              </div>
            </div>
          </div>
        )}

        <div className="flex-1 flex overflow-hidden">
          {/* Left + Center Area */}
          <div className="flex-1 flex flex-col overflow-hidden">
             <div className="flex-[0.6] flex overflow-hidden border-b border-border">
                <FactoryFloor />
                <LiveEnergyChart />
             </div>
             <div className="flex-[0.4] overflow-hidden">
                <PipelineFlow />
             </div>
          </div>

          {/* Right Panel */}
          <AnomalyFeed />
        </div>

        {/* Bottom Panel */}
        <div className="h-[300px] border-t border-border overflow-y-auto custom-scrollbar">
           <SparkKPIPanel />
        </div>
      </main>
    </div>
  );
}

export default App;
