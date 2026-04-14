import React, { useCallback, useMemo, useEffect, useState } from 'react';
import ReactFlow, { 
  addEdge, 
  Background, 
  Controls, 
  useNodesState, 
  useEdgesState,
  MarkerType
} from 'reactflow';
import 'reactflow/dist/style.css';
import CustomNode from './nodes/CustomNode';
import useStore from '../../store/useStore';
import SparkConsole from './SparkConsole';
import axios from 'axios';

const nodeTypes = {
  custom: CustomNode,
};

const initialNodes = [
  { id: 'esp32', type: 'custom', position: { x: 0, y: 50 }, data: { label: 'ESP32 Sensor', icon: '🔌', outputs: [{id: 'out'}] } },
  { id: 'tinyml', type: 'custom', position: { x: 200, y: 50 }, data: { label: 'TinyML LSTM', icon: '🧠', inputs: [{id: 'in'}], outputs: [{id: 'out'}] } },
  { id: 'fastapi', type: 'custom', position: { x: 400, y: 50 }, data: { label: 'FastAPI /predict', icon: '⚡', inputs: [{id: 'in'}], outputs: [{id: 'log'}, {id: 'slack'}, {id: 'ws'}] } },
  { id: 'log-csv', type: 'custom', position: { x: 600, y: -50 }, data: { label: 'Anomaly Log CSV', icon: '📄', inputs: [{id: 'in'}], outputs: [{id: 'out'}] } },
  { id: 'slack', type: 'custom', position: { x: 600, y: 50 }, data: { label: 'Slack Webhook', icon: '💬', inputs: [{id: 'in'}] } },
  { id: 'ws', type: 'custom', position: { x: 600, y: 150 }, data: { label: 'WebSocket /ws', icon: '📡', inputs: [{id: 'in'}], outputs: [{id: 'out'}] } },
  { id: 'spark', type: 'custom', position: { x: 800, y: -50 }, data: { label: 'Spark Pipeline', icon: '🔥', inputs: [{id: 'in'}], outputs: [{id: 'kpi'}, {id: 'gbt'}] } },
  { id: 'dashboard-out', type: 'custom', position: { x: 800, y: 150 }, data: { label: 'React Dashboard', icon: '🖥️', inputs: [{id: 'in'}] } },
  { id: 'kpi-dash', type: 'custom', position: { x: 1000, y: -100 }, data: { label: 'KPI Dashboard', icon: '📊', inputs: [{id: 'in'}] } },
  { id: 'gbt-model', type: 'custom', position: { x: 1000, y: 0 }, data: { label: 'GBT Forecasting', icon: '📈', inputs: [{id: 'in'}] } },
];

const initialEdges = [
  { id: 'e1-2', source: 'esp32', target: 'tinyml', animated: true, markerEnd: { type: MarkerType.ArrowClosed, color: '#00d4ff' }, style: { stroke: '#00d4ff' } },
  { id: 'e2-3', source: 'tinyml', target: 'fastapi', animated: true, markerEnd: { type: MarkerType.ArrowClosed, color: '#00d4ff' }, style: { stroke: '#00d4ff' } },
  { id: 'e3-4', source: 'fastapi', sourceHandle: 'log', target: 'log-csv', animated: true, style: { stroke: '#00d4ff' } },
  { id: 'e3-5', source: 'fastapi', sourceHandle: 'slack', target: 'slack', animated: true, style: { stroke: '#00d4ff' } },
  { id: 'e3-6', source: 'fastapi', sourceHandle: 'ws', target: 'ws', animated: true, style: { stroke: '#00d4ff' } },
  { id: 'e4-7', source: 'log-csv', target: 'spark', animated: true, style: { stroke: '#00d4ff' } },
  { id: 'e6-8', source: 'ws', target: 'dashboard-out', animated: true, style: { stroke: '#00d4ff' } },
  { id: 'e7-9', source: 'spark', sourceHandle: 'kpi', target: 'kpi-dash', animated: true, style: { stroke: '#00d4ff' } },
  { id: 'e7-10', source: 'spark', sourceHandle: 'gbt', target: 'gbt-model', animated: true, style: { stroke: '#00d4ff' } },
];

const PipelineFlow = () => {
    const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
    const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
    const { sparkRunning, sparkLogs, machines, anomalyEvents } = useStore();
    const [showConsole, setShowConsole] = useState(false);

    // Update nodes based on state
    useEffect(() => {
        const lastAnomaly = anomalyEvents[0];
        const hasAnomaly = lastAnomaly && (new Date() - new Date(lastAnomaly.timestamp)) < 5000;

        setNodes(nds => nds.map(node => {
            if (node.id === 'spark') {
                return { 
                    ...node, 
                    data: { 
                        ...node.data, 
                        status: sparkRunning ? 'PROCESSING' : 'IDLE',
                        statusColor: sparkRunning ? 'text-warning' : 'text-primary'
                    }
                };
            }
            if (node.id === 'fastapi') {
                return {
                    ...node,
                    data: {
                        ...node.data,
                        isAnomaly: hasAnomaly,
                        preview: hasAnomaly ? `ALERT: M-${lastAnomaly.machine_id} spiked` : 'Healthy'
                    }
                };
            }
            return node;
        }));

        setEdges(eds => eds.map(edge => {
            if (hasAnomaly) {
                return { ...edge, style: { ...edge.style, stroke: '#ff3b3b' }, animated: true };
            }
            return { ...edge, style: { ...edge.style, stroke: '#00d4ff' } };
        }));
    }, [sparkRunning, anomalyEvents]);

    const runSpark = async () => {
        try {
            setShowConsole(true);
            await axios.post('/api/spark/run');
        } catch (err) {
            console.error('Failed to run Spark', err);
        }
    };

    return (
        <div className="h-[400px] border-y border-border relative bg-black/20">
            <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                nodeTypes={nodeTypes}
                fitView
            >
                <Background color="#12161d" gap={20} />
            </ReactFlow>

            <div className="absolute top-4 left-4 z-10">
                <h3 className="text-[10px] font-bold text-white/30 uppercase tracking-[0.2em]">End-to-End Data Pipeline</h3>
            </div>

            <div className="absolute bottom-4 right-4 z-10 flex gap-2">
                <button 
                  onClick={() => setShowConsole(!showConsole)}
                  className="bg-surface border border-border text-[10px] font-bold px-3 py-1.5 rounded hover:bg-white/5 transition-colors"
                >
                  {showConsole ? 'HIDE CONSOLE' : 'SHOW CONSOLE'}
                </button>
                <button 
                    onClick={runSpark}
                    disabled={sparkRunning}
                    className={`text-[10px] font-bold px-4 py-1.5 rounded border flex items-center gap-2 transition-all
                        ${sparkRunning ? 'bg-warning/20 border-warning text-warning cursor-not-allowed' : 'bg-primary/20 border-primary text-primary hover:bg-primary hover:text-black'}
                    `}
                >
                    {sparkRunning ? <div className="w-3 h-3 border-2 border-warning border-t-transparent rounded-full animate-spin"/> : '🔥'} 
                    RUN SPARK PIPELINE
                </button>
            </div>

            {showConsole && (
                <div className="absolute inset-x-0 bottom-0 top-[60%] z-20">
                   <SparkConsole onClose={() => setShowConsole(false)} />
                </div>
            )}
        </div>
    );
};

export default PipelineFlow;
