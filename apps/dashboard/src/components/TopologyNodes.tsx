import { Handle, Position } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import type { AgentNodeData, ToolNodeData } from '../data/topology';
import { FrameworkBadge } from './Badge';
import type { Framework } from '../types';

// ─── Agent Node ────────────────────────────────────────────────────

export function AgentNode({ data, selected }: NodeProps) {
  const d = data as AgentNodeData;

  const statusColor =
    d.runningCount > 0 ? '#fbbf24'
    : d.failedCount > 0 ? '#f87171'
    : '#34d399';

  const successRate = d.sessionCount > 0
    ? Math.round((d.successCount / d.sessionCount) * 100)
    : 0;

  return (
    <div
      style={{
        background: 'var(--bg-2)',
        border: `1px solid ${selected ? 'var(--accent)' : 'var(--border-md)'}`,
        borderRadius: 12,
        padding: '14px 16px',
        minWidth: 200,
        boxShadow: selected
          ? '0 0 0 3px var(--accent-dim)'
          : '0 4px 20px rgba(0,0,0,0.25)',
        transition: 'border-color 0.15s, box-shadow 0.15s',
      }}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2 min-w-0">
          <span
            className="w-2 h-2 rounded-full flex-shrink-0"
            style={{
              background: statusColor,
              boxShadow: d.runningCount > 0 ? `0 0 6px ${statusColor}` : 'none',
            }}
          />
          <span
            className="text-[13px] font-semibold truncate"
            style={{ color: 'var(--text-primary)' }}
          >
            {d.agentName}
          </span>
        </div>
        <FrameworkBadge framework={d.framework as Framework} />
      </div>

      {/* Stats row */}
      <div
        className="grid grid-cols-3 gap-2 pt-3"
        style={{ borderTop: '1px solid var(--border)' }}
      >
        {[
          { label: 'Sessions', value: d.sessionCount },
          { label: 'Success',  value: `${successRate}%` },
          { label: 'LLM',      value: d.llmCalls },
        ].map(({ label, value }) => (
          <div key={label} className="text-center">
            <p
              className="text-[14px] font-semibold leading-none mb-1"
              style={{ color: 'var(--text-primary)' }}
            >
              {value}
            </p>
            <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>{label}</p>
          </div>
        ))}
      </div>

      {/* Right handle — connects to tools */}
      <Handle
        type="source"
        position={Position.Right}
        style={{
          background: 'var(--accent)',
          border: '2px solid var(--bg-2)',
          width: 10,
          height: 10,
        }}
      />
    </div>
  );
}

// ─── Tool Node ─────────────────────────────────────────────────────

export function ToolNode({ data, selected }: NodeProps) {
  const d = data as ToolNodeData;

  const srColor =
    d.successRate >= 95 ? '#34d399'
    : d.successRate >= 80 ? '#fbbf24'
    : '#f87171';

  return (
    <div
      style={{
        background: 'var(--bg-2)',
        border: `1px solid ${selected ? 'var(--accent)' : 'var(--border)'}`,
        borderRadius: 10,
        padding: '10px 14px',
        minWidth: 160,
        boxShadow: selected
          ? '0 0 0 3px var(--accent-dim)'
          : '0 2px 12px rgba(0,0,0,0.18)',
        transition: 'border-color 0.15s, box-shadow 0.15s',
      }}
    >
      {/* Left handle — receives from agents */}
      <Handle
        type="target"
        position={Position.Left}
        style={{
          background: 'var(--border-strong)',
          border: '2px solid var(--bg-2)',
          width: 8,
          height: 8,
        }}
      />

      {/* Tool name */}
      <div className="flex items-center gap-2 mb-2.5">
        <div
          className="w-5 h-5 rounded-md flex items-center justify-center flex-shrink-0 text-[10px]"
          style={{ background: 'rgba(251,191,36,0.12)', color: '#f59e0b' }}
        >
          ⚙
        </div>
        <code
          className="text-[12px] font-medium truncate"
          style={{ color: 'var(--text-primary)' }}
        >
          {d.toolName}
        </code>
      </div>

      {/* Metrics */}
      <div className="flex items-center justify-between">
        <span className="text-[11px]" style={{ color: 'var(--text-tertiary)' }}>
          {d.callCount.toLocaleString()} calls
        </span>
        <span
          className="text-[11px] font-medium"
          style={{ color: srColor }}
        >
          {d.successRate}%
        </span>
      </div>

      {/* Used-by agents */}
      {d.agentNames.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {d.agentNames.map((a) => (
            <span
              key={a}
              className="text-[9px] px-1.5 py-0.5 rounded"
              style={{
                background: 'var(--accent-dim)',
                color: 'var(--accent-light)',
              }}
            >
              {a.replace('-agent', '').replace('-bot', '')}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
