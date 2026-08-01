import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { mockSessions, mockTimelines } from '../data/mock';
import { StatusBadge, FrameworkBadge, KindBadge } from '../components/Badge';
import { PageHeader, Card } from '../components/PageHeader';
import { formatDuration, formatTimestamp } from '../lib/utils';
import type { TimelineEntry } from '../types';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { cn } from '../lib/utils';

const KIND_BAR: Record<string, string> = {
  session: '#7c6af7',
  llm:     '#3b82f6',
  tool:    '#f59e0b',
  memory:  '#ec4899',
  context: '#14b8a6',
  tts:     '#6366f1',
  stt:     '#0ea5e9',
  error:   '#ef4444',
};

function WaterfallBar({ entry, sessionStartMs, totalMs }: { entry: TimelineEntry; sessionStartMs: number; totalMs: number }) {
  const offsetMs = new Date(entry.started_at).getTime() - sessionStartMs;
  const durationMs = entry.duration_ms ?? 2;
  const left  = totalMs > 0 ? (offsetMs / totalMs) * 100 : 0;
  const width = totalMs > 0 ? Math.max((durationMs / totalMs) * 100, 0.8) : 0.8;
  const color = KIND_BAR[entry.kind] ?? '#6b7280';

  return (
    <div className="relative flex-1 h-4 rounded" style={{ background: 'var(--bg-3)' }}>
      <div
        style={{
          position: 'absolute',
          left: `${left}%`,
          width: `${width}%`,
          top: 2, bottom: 2,
          borderRadius: 3,
          background: color,
          opacity: entry.status === 'failed' ? 0.4 : 0.72,
        }}
        title={`${entry.label} — ${formatDuration(entry.duration_ms)}`}
      />
    </div>
  );
}

function SpanRow({ entry, sessionStartMs, totalMs }: { entry: TimelineEntry; sessionStartMs: number; totalMs: number }) {
  const [expanded, setExpanded] = useState(false);
  const hasDetails = Object.keys(entry.metadata).length > 0 || !!entry.error;

  return (
    <>
      <tr
        className={cn(entry.status === 'failed' && 'bg-red-500/[0.03]')}
        style={{ borderBottom: '1px solid var(--border)' }}
        onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-hover)')}
        onMouseLeave={(e) => (e.currentTarget.style.background = entry.status === 'failed' ? 'rgba(239,68,68,0.03)' : 'transparent')}
      >
        <td className="px-4 py-2.5" style={{ width: 260 }}>
          <div className="flex items-center gap-2">
            {hasDetails ? (
              <button
                onClick={() => setExpanded(!expanded)}
                className="flex-shrink-0 transition-colors"
                style={{ color: 'var(--text-muted)' }}
              >
                {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
              </button>
            ) : (
              <span className="w-4 flex-shrink-0" />
            )}
            <KindBadge kind={entry.kind} />
            <span
              className="text-[12px] truncate"
              style={{ color: 'var(--text-secondary)', maxWidth: 100 }}
              title={entry.label}
            >
              {entry.label.replace(/^[^:]+:\s*/, '')}
            </span>
          </div>
        </td>
        <td className="px-4 py-2.5" style={{ width: 90 }}>
          <StatusBadge status={entry.status} />
        </td>
        <td className="px-4 py-2.5 text-right" style={{ width: 72 }}>
          <span className="text-[12px] font-mono" style={{ color: 'var(--text-tertiary)' }}>
            {formatDuration(entry.duration_ms)}
          </span>
        </td>
        <td className="px-4 py-2.5" style={{ width: 72 }}>
          <span className="text-[11px] font-mono" style={{ color: 'var(--text-muted)' }}>
            {formatTimestamp(entry.started_at)}
          </span>
        </td>
        <td className="px-4 py-2.5 pr-5">
          <WaterfallBar entry={entry} sessionStartMs={sessionStartMs} totalMs={totalMs} />
        </td>
      </tr>
      {expanded && (
        <tr style={{ background: 'var(--bg-hover)', borderBottom: '1px solid var(--border)' }}>
          <td colSpan={5} className="px-10 py-3">
            {entry.error && (
              <div
                className="mb-2.5 flex items-start gap-2 text-[12px] rounded-lg px-3 py-2.5"
                style={{ background: 'var(--danger-dim)', color: 'var(--danger)' }}
              >
                <code className="leading-relaxed">{entry.error}</code>
              </div>
            )}
            {Object.keys(entry.metadata).length > 0 && (
              <div className="grid grid-cols-3 gap-x-6 gap-y-1.5">
                {Object.entries(entry.metadata).map(([k, v]) => (
                  <div key={k} className="text-[12px]">
                    <span style={{ color: 'var(--text-muted)' }}>{k}: </span>
                    <code style={{ color: 'var(--text-secondary)' }}>{String(v)}</code>
                  </div>
                ))}
              </div>
            )}
          </td>
        </tr>
      )}
    </>
  );
}

export function TimelinePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedId = searchParams.get('session') ?? mockSessions[0].session_id;
  const session = mockSessions.find((s) => s.session_id === selectedId) ?? mockSessions[0];
  const timeline = mockTimelines[session.session_id];

  const entries = timeline
    ? [...timeline.entries].sort((a, b) => new Date(a.started_at).getTime() - new Date(b.started_at).getTime())
    : [];
  const sessionStartMs = entries.length > 0 ? new Date(entries[0].started_at).getTime() : 0;

  return (
    <div className="px-8 py-8 max-w-[1400px]">
      <PageHeader title="Timeline" description="Execution waterfall for agent sessions" />

      {/* Session picker */}
      <div className="mb-6">
        <label className="block label-xs mb-2">Session</label>
        <select
          value={session.session_id}
          onChange={(e) => setSearchParams({ session: e.target.value })}
          className="rounded-lg px-4 py-2.5 text-[13px] outline-none max-w-lg w-full"
          style={{
            background: 'var(--bg-2)',
            border: '1px solid var(--border)',
            color: 'var(--text-primary)',
          }}
        >
          {mockSessions.map((s) => (
            <option key={s.session_id} value={s.session_id}>
              {s.agent_name} · {s.framework} · {s.status} · {s.session_id.slice(5, 21)}…
            </option>
          ))}
        </select>
      </div>

      {/* Meta pills */}
      <div className="card flex flex-wrap gap-6 px-5 py-4 mb-6">
        {[
          { label: 'Agent',    value: <span className="text-[13px] font-medium" style={{ color: 'var(--text-primary)' }}>{session.agent_name}</span> },
          { label: 'Framework', value: <FrameworkBadge framework={session.framework} /> },
          { label: 'Status',   value: <StatusBadge status={session.status} /> },
          { label: 'Duration', value: <span className="text-[13px]" style={{ color: 'var(--text-secondary)' }}>{formatDuration(session.duration_ms)}</span> },
          { label: 'Spans',    value: <span className="text-[13px]" style={{ color: 'var(--text-secondary)' }}>{session.span_count}</span> },
          { label: 'LLM',      value: <span className="text-[13px]" style={{ color: 'var(--text-secondary)' }}>{session.llm_calls}</span> },
          { label: 'Tools',    value: <span className="text-[13px]" style={{ color: 'var(--text-secondary)' }}>{session.tool_calls}</span> },
        ].map(({ label, value }) => (
          <div key={label}>
            <p className="label-xs mb-1.5">{label}</p>
            {value}
          </div>
        ))}
      </div>

      {/* Legend */}
      <div className="flex gap-4 flex-wrap mb-4">
        {Object.entries(KIND_BAR).map(([kind, color]) => (
          <div key={kind} className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-sm flex-shrink-0" style={{ background: color, opacity: 0.75 }} />
            <span className="text-[11px]" style={{ color: 'var(--text-muted)' }}>{kind}</span>
          </div>
        ))}
      </div>

      {/* Waterfall */}
      {timeline ? (
        <Card>
          <table className="w-full">
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                {['Span', 'Status', 'Duration', 'Time', 'Waterfall'].map((h, i) => (
                  <th key={h} className="th" style={{ textAlign: i === 2 ? 'right' : 'left',
                    width: i === 0 ? 260 : i === 1 ? 90 : i === 2 ? 72 : i === 3 ? 72 : undefined }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => (
                <SpanRow key={entry.span_id} entry={entry} sessionStartMs={sessionStartMs} totalMs={timeline.total_ms} />
              ))}
            </tbody>
          </table>
        </Card>
      ) : (
        <Card className="py-20 text-center">
          <p className="text-[13px]" style={{ color: 'var(--text-tertiary)' }}>No timeline data for this session</p>
        </Card>
      )}
    </div>
  );
}
