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
  const left = totalMs > 0 ? (offsetMs / totalMs) * 100 : 0;
  const width = totalMs > 0 ? Math.max((durationMs / totalMs) * 100, 0.8) : 0.8;
  const color = KIND_BAR[entry.kind] ?? '#6b7280';

  return (
    <div className="relative flex-1 h-4" style={{ background: 'rgba(255,255,255,0.03)', borderRadius: 4 }}>
      <div
        style={{
          position: 'absolute',
          left: `${left}%`,
          width: `${width}%`,
          top: 2,
          bottom: 2,
          borderRadius: 3,
          background: color,
          opacity: entry.status === 'failed' ? 0.45 : 0.75,
          transition: 'opacity 0.15s',
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
        style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}
        onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255,255,255,0.025)')}
        onMouseLeave={(e) => (e.currentTarget.style.background = entry.status === 'failed' ? 'rgba(239,68,68,0.03)' : 'transparent')}
      >
        <td className="px-4 py-2.5" style={{ width: 260 }}>
          <div className="flex items-center gap-2">
            {hasDetails ? (
              <button
                onClick={() => setExpanded(!expanded)}
                className="flex-shrink-0 transition-colors"
                style={{ color: 'rgba(255,255,255,0.25)' }}
              >
                {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
              </button>
            ) : (
              <span className="w-4 flex-shrink-0" />
            )}
            <KindBadge kind={entry.kind} />
            <span
              className="text-[12px] truncate"
              style={{ color: 'rgba(255,255,255,0.6)', maxWidth: 100 }}
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
          <span className="text-[12px] font-mono" style={{ color: 'rgba(255,255,255,0.4)' }}>
            {formatDuration(entry.duration_ms)}
          </span>
        </td>
        <td className="px-4 py-2.5" style={{ width: 72 }}>
          <span className="text-[11px] font-mono" style={{ color: 'rgba(255,255,255,0.2)' }}>
            {formatTimestamp(entry.started_at)}
          </span>
        </td>
        <td className="px-4 py-2.5 pr-5">
          <WaterfallBar entry={entry} sessionStartMs={sessionStartMs} totalMs={totalMs} />
        </td>
      </tr>
      {expanded && (
        <tr style={{ background: 'rgba(255,255,255,0.015)', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
          <td colSpan={5} className="px-10 py-3">
            {entry.error && (
              <div
                className="mb-2.5 flex items-start gap-2 text-[12px] rounded-lg px-3 py-2.5"
                style={{ background: 'rgba(239,68,68,0.08)', color: '#f87171' }}
              >
                <code className="leading-relaxed">{entry.error}</code>
              </div>
            )}
            {Object.keys(entry.metadata).length > 0 && (
              <div className="grid grid-cols-3 gap-x-6 gap-y-1.5">
                {Object.entries(entry.metadata).map(([k, v]) => (
                  <div key={k} className="text-[12px]">
                    <span style={{ color: 'rgba(255,255,255,0.25)' }}>{k}: </span>
                    <code style={{ color: 'rgba(255,255,255,0.6)' }}>{String(v)}</code>
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

      {/* Session Picker */}
      <div className="mb-6">
        <label className="block text-[10px] font-semibold tracking-widest uppercase mb-2" style={{ color: 'rgba(255,255,255,0.2)' }}>
          Session
        </label>
        <select
          value={session.session_id}
          onChange={(e) => setSearchParams({ session: e.target.value })}
          className="rounded-lg px-4 py-2.5 text-[13px] outline-none max-w-lg w-full"
          style={{
            background: '#13131a',
            border: '1px solid rgba(255,255,255,0.07)',
            color: '#e2e2ea',
          }}
        >
          {mockSessions.map((s) => (
            <option key={s.session_id} value={s.session_id}
              style={{ background: '#1a1a24' }}>
              {s.agent_name} · {s.framework} · {s.status} · {s.session_id.slice(5, 21)}…
            </option>
          ))}
        </select>
      </div>

      {/* Session Meta Pills */}
      <div
        className="flex flex-wrap gap-6 px-5 py-4 rounded-xl mb-6"
        style={{ background: '#13131a', border: '1px solid rgba(255,255,255,0.06)' }}
      >
        {[
          { label: 'Agent', value: <span className="text-[13px] font-medium" style={{ color: '#e2e2ea' }}>{session.agent_name}</span> },
          { label: 'Framework', value: <FrameworkBadge framework={session.framework} /> },
          { label: 'Status', value: <StatusBadge status={session.status} /> },
          { label: 'Duration', value: <span className="text-[13px]" style={{ color: 'rgba(255,255,255,0.6)' }}>{formatDuration(session.duration_ms)}</span> },
          { label: 'Spans', value: <span className="text-[13px]" style={{ color: 'rgba(255,255,255,0.6)' }}>{session.span_count}</span> },
          { label: 'LLM', value: <span className="text-[13px]" style={{ color: 'rgba(255,255,255,0.6)' }}>{session.llm_calls}</span> },
          { label: 'Tools', value: <span className="text-[13px]" style={{ color: 'rgba(255,255,255,0.6)' }}>{session.tool_calls}</span> },
        ].map(({ label, value }) => (
          <div key={label}>
            <p className="text-[10px] font-semibold tracking-widest uppercase mb-1.5" style={{ color: 'rgba(255,255,255,0.2)' }}>
              {label}
            </p>
            {value}
          </div>
        ))}
      </div>

      {/* Legend */}
      <div className="flex gap-4 flex-wrap mb-4">
        {Object.entries(KIND_BAR).map(([kind, color]) => (
          <div key={kind} className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-sm flex-shrink-0" style={{ background: color, opacity: 0.75 }} />
            <span className="text-[11px]" style={{ color: 'rgba(255,255,255,0.3)' }}>{kind}</span>
          </div>
        ))}
      </div>

      {/* Waterfall */}
      {timeline ? (
        <Card>
          <table className="w-full">
            <thead>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                {['Span', 'Status', 'Duration', 'Time', 'Waterfall'].map((h, i) => (
                  <th
                    key={h}
                    className="px-4 py-3 text-[10px] font-semibold tracking-widest uppercase"
                    style={{
                      color: 'rgba(255,255,255,0.2)',
                      textAlign: i === 2 ? 'right' : 'left',
                      width: i === 0 ? 260 : i === 1 ? 90 : i === 2 ? 72 : i === 3 ? 72 : undefined,
                    }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => (
                <SpanRow
                  key={entry.span_id}
                  entry={entry}
                  sessionStartMs={sessionStartMs}
                  totalMs={timeline.total_ms}
                />
              ))}
            </tbody>
          </table>
        </Card>
      ) : (
        <Card className="py-20 text-center">
          <p className="text-[13px]" style={{ color: 'rgba(255,255,255,0.2)' }}>
            No timeline data for this session
          </p>
        </Card>
      )}
    </div>
  );
}
