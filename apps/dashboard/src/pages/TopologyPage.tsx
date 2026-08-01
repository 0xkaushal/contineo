import { useCallback, useMemo, useState } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  BackgroundVariant,
  Panel,
} from '@xyflow/react';
import type { Connection } from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { buildTopologyGraph } from '../data/topology';
import type { AgentNodeData, ToolNodeData } from '../data/topology';
import { AgentNode, ToolNode } from '../components/TopologyNodes';
import { OffsetBezierEdge } from '../components/TopologyEdge';
import { PageHeader } from '../components/PageHeader';
import { useTheme } from '../lib/theme';

const nodeTypes = {
  agentNode: AgentNode,
  toolNode:  ToolNode,
};

const edgeTypes = {
  default: OffsetBezierEdge,
};

// ── Detail panel shown on node click ─────────────────────────────

function DetailPanel({
  data,
  type,
  onClose,
}: {
  data: AgentNodeData | ToolNodeData;
  type: 'agent' | 'tool';
  onClose: () => void;
}) {
  return (
    <div
      className="absolute right-4 top-4 rounded-xl p-5 z-10"
      style={{
        background: 'var(--bg-2)',
        border: '1px solid var(--border-md)',
        width: 240,
        boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
      }}
    >
      <div className="flex items-center justify-between mb-4">
        <p className="text-[12px] font-semibold" style={{ color: 'var(--text-secondary)' }}>
          {type === 'agent' ? 'Agent' : 'Tool'}
        </p>
        <button
          onClick={onClose}
          className="text-[18px] leading-none"
          style={{ color: 'var(--text-muted)' }}
        >
          ×
        </button>
      </div>

      {type === 'agent' && (() => {
        const d = data as AgentNodeData;
        const successRate = d.sessionCount > 0
          ? Math.round((d.successCount / d.sessionCount) * 100)
          : 0;
        return (
          <div className="space-y-2.5">
            {[
              ['Agent',        d.agentName],
              ['Framework',    d.framework],
              ['Sessions',     d.sessionCount],
              ['Success rate', `${successRate}%`],
              ['Failed',       d.failedCount],
              ['Running',      d.runningCount],
              ['LLM calls',    d.llmCalls],
              ['Tool calls',   d.toolCalls],
            ].map(([k, v]) => (
              <div key={String(k)} className="flex items-center justify-between">
                <span className="text-[12px]" style={{ color: 'var(--text-muted)' }}>{k}</span>
                <span className="text-[12px] font-medium" style={{ color: 'var(--text-primary)' }}>{String(v)}</span>
              </div>
            ))}
          </div>
        );
      })()}

      {type === 'tool' && (() => {
        const d = data as ToolNodeData;
        return (
          <div className="space-y-2.5">
            {[
              ['Tool',         d.toolName],
              ['Total calls',  d.callCount],
              ['Success rate', `${d.successRate}%`],
              ['Used by',      d.agentNames.join(', ')],
            ].map(([k, v]) => (
              <div key={String(k)} className="flex items-start justify-between gap-3">
                <span className="text-[12px] flex-shrink-0" style={{ color: 'var(--text-muted)' }}>{k}</span>
                <span className="text-[12px] font-medium text-right" style={{ color: 'var(--text-primary)' }}>{String(v)}</span>
              </div>
            ))}
          </div>
        );
      })()}
    </div>
  );
}

// ── Legend ────────────────────────────────────────────────────────

function Legend() {
  const items = [
    { color: '#34d399', label: 'Healthy edge (≥95%)' },
    { color: '#f59e0b', label: 'Degraded (80–94%)' },
    { color: '#ef4444', label: 'Error prone (<80%)' },
    { color: '#fbbf24', label: 'Agent running', pulse: true },
  ];
  return (
    <div
      className="flex flex-col gap-2 px-4 py-3 rounded-xl"
      style={{ background: 'var(--bg-2)', border: '1px solid var(--border)' }}
    >
      <p className="text-[10px] font-semibold tracking-widest uppercase mb-1" style={{ color: 'var(--text-muted)' }}>
        Legend
      </p>
      {items.map(({ color, label, pulse }) => (
        <div key={label} className="flex items-center gap-2">
          <span
            className="w-2.5 h-2.5 rounded-full flex-shrink-0"
            style={{ background: color, boxShadow: pulse ? `0 0 6px ${color}` : 'none' }}
          />
          <span className="text-[11px]" style={{ color: 'var(--text-secondary)' }}>{label}</span>
        </div>
      ))}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────

export function TopologyPage() {
  const { theme } = useTheme();

  const { nodes: initNodes, edges: initEdges } = useMemo(() => buildTopologyGraph(), []);
  const [nodes, , onNodesChange] = useNodesState(initNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initEdges);
  const onConnect = useCallback((c: Connection) => setEdges((es) => addEdge(c, es)), [setEdges]);

  const [selected, setSelected] = useState<{ type: 'agent' | 'tool'; data: AgentNodeData | ToolNodeData } | null>(null);

  const isDark = theme === 'dark';

  const bgColor   = isDark ? '#0d0d12' : '#f5f5f7';
  const dotColor  = isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,0,0,0.08)';
  const miniMapBg = isDark ? '#13131a' : '#ffffff';
  const miniMapNode = isDark ? '#7c6af7' : '#6452e9';

  return (
    <div className="flex flex-col" style={{ height: 'calc(100vh - 0px)' }}>
      {/* Header */}
      <div className="px-8 pt-8 pb-4 flex-shrink-0">
        <PageHeader
          title="Topology"
          description="Agent and tool dependency graph — nodes, connections, and health"
        />
        <div className="flex items-center gap-4 text-[12px]" style={{ color: 'var(--text-tertiary)' }}>
          <span>{nodes.filter((n) => n.type === 'agentNode').length} agents</span>
          <span style={{ color: 'var(--border-md)' }}>·</span>
          <span>{nodes.filter((n) => n.type === 'toolNode').length} tools</span>
          <span style={{ color: 'var(--border-md)' }}>·</span>
          <span>{edges.length} connections</span>
          <span style={{ color: 'var(--border-md)' }}>·</span>
          <span style={{ color: 'var(--text-muted)' }}>Click a node for details · Drag to rearrange · Scroll to zoom</span>
        </div>
      </div>

      {/* Canvas */}
      <div className="flex-1 mx-8 mb-8 rounded-xl overflow-hidden relative"
        style={{ border: '1px solid var(--border)' }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          fitView
          fitViewOptions={{ padding: 0.25 }}
          minZoom={0.3}
          maxZoom={2}
          style={{ background: bgColor }}
          onNodeClick={(_, node) => {
            const type = node.type === 'agentNode' ? 'agent' : 'tool';
            setSelected({ type, data: node.data as AgentNodeData | ToolNodeData });
          }}
          onPaneClick={() => setSelected(null)}
          proOptions={{ hideAttribution: true }}
        >
          <Background
            variant={BackgroundVariant.Dots}
            gap={20}
            size={1}
            color={dotColor}
          />
          <Controls
            style={{
              background: 'var(--bg-2)',
              border: '1px solid var(--border)',
              borderRadius: 8,
            }}
          />
          <MiniMap
            style={{
              background: miniMapBg,
              border: '1px solid var(--border)',
              borderRadius: 8,
            }}
            nodeColor={miniMapNode}
            maskColor={isDark ? 'rgba(13,13,18,0.7)' : 'rgba(245,245,247,0.7)'}
          />
          <Panel position="top-left">
            <Legend />
          </Panel>
        </ReactFlow>

        {/* Detail panel */}
        {selected && (
          <DetailPanel
            data={selected.data}
            type={selected.type}
            onClose={() => setSelected(null)}
          />
        )}
      </div>
    </div>
  );
}
