import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { mockSessions, mockTimelines } from '../data/mock';
import { StatusBadge, FrameworkBadge, KindBadge } from '../components/Badge';
import { formatDuration, formatTimestamp } from '../lib/utils';
import type { TimelineEntry } from '../types';
import { ChevronDown, ChevronRight, Info } from 'lucide-react';
import { cn } from '../lib/utils';

const KIND_COLORS: Record<string, string> = {
  session: 'bg-violet-500',
  llm: 'bg-blue-500',
  tool: 'bg-amber-500',
  memory: 'bg-pink-500',
  context: 'bg-teal-500',
  tts: 'bg-indigo-500',
  stt: 'bg-sky-500',
  error: 'bg-red-500',
};

function WaterfallBar({ entry, totalMs }: { entry: TimelineEntry; totalMs: number }) {
  const sessionStart = new Date(mockTimelines[entry.session_id]?.entries[0]?.started_at ?? entry.started_at).getTime();
  const entryStart = new Date(entry.started_at).getTime();
  const offsetMs = entryStart - sessionStart;
  const durationMs = entry.duration_ms ?? 1;

  const left = totalMs > 0 ? (offsetMs / totalMs) * 100 : 0;
  const width = totalMs > 0 ? Math.max((durationMs / totalMs) * 100, 0.5) : 0.5;

  return (
    <div className="relative h-5 flex-1">
      <div className="absolute inset-y-0 w-full bg-gray-800/40 rounded" />
      <div
        className={cn('absolute inset-y-1 rounded', KIND_COLORS[entry.kind] ?? 'bg-gray-500')}
        style={{ left: `${left}%`, width: `${width}%`, opacity: entry.status === 'failed' ? 0.5 : 0.85 }}
        title={`${entry.label} — ${formatDuration(entry.duration_ms)}`}
      />
    </div>
  );
}

function SpanRow({ entry, totalMs }: { entry: TimelineEntry; totalMs: number }) {
  const [expanded, setExpanded] = useState(false);
  const hasDetails = Object.keys(entry.metadata).length > 0 || entry.error;

  return (
    <>
      <tr
        className={cn(
          'border-b border-gray-800/60 hover:bg-gray-800/30 transition-colors',
          entry.status === 'failed' && 'bg-red-950/10'
        )}
      >
        <td className="px-4 py-2.5 w-64">
          <div className="flex items-center gap-2">
            {hasDetails ? (
              <button onClick={() => setExpanded(!expanded)} className="text-gray-500 hover:text-gray-300">
                {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
              </button>
            ) : (
              <span className="w-4" />
            )}
            <KindBadge kind={entry.kind} />
            <span className="text-xs text-gray-300 truncate max-w-32" title={entry.label}>
              {entry.label.replace(/^[^:]+:\s*/, '')}
            </span>
          </div>
        </td>
        <td className="px-4 py-2.5 w-20">
          <StatusBadge status={entry.status} />
        </td>
        <td className="px-4 py-2.5 w-20 text-right">
          <span className="text-xs text-gray-400 font-mono">{formatDuration(entry.duration_ms)}</span>
        </td>
        <td className="px-4 py-2.5 w-20 text-xs text-gray-600 font-mono">
          {formatTimestamp(entry.started_at)}
        </td>
        <td className="px-4 py-2.5">
          <WaterfallBar entry={entry} totalMs={totalMs} />
        </td>
      </tr>
      {expanded && (
        <tr className="border-b border-gray-800/30 bg-gray-900/50">
          <td colSpan={5} className="px-8 py-3">
            {entry.error && (
              <div className="mb-2 flex items-start gap-2 text-xs text-red-400 bg-red-950/30 rounded-lg p-2.5">
                <Info size={12} className="mt-0.5 flex-shrink-0" />
                <code>{entry.error}</code>
              </div>
            )}
            {Object.keys(entry.metadata).length > 0 && (
              <div className="grid grid-cols-3 gap-2">
                {Object.entries(entry.metadata).map(([k, v]) => (
                  <div key={k} className="text-xs">
                    <span className="text-gray-600">{k}: </span>
                    <code className="text-gray-300">{String(v)}</code>
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

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Timeline</h1>
          <p className="text-gray-500 text-sm mt-1">Execution waterfall for agent sessions</p>
        </div>
      </div>

      {/* Session Picker */}
      <div className="mb-6">
        <label className="text-xs text-gray-500 uppercase tracking-wider font-medium mb-2 block">Session</label>
        <select
          value={session.session_id}
          onChange={(e) => setSearchParams({ session: e.target.value })}
          className="bg-gray-900 border border-gray-700 text-gray-200 text-sm rounded-lg px-4 py-2.5 focus:outline-none focus:border-violet-500 max-w-lg w-full"
        >
          {mockSessions.map((s) => (
            <option key={s.session_id} value={s.session_id}>
              {s.agent_name} · {s.framework} · {s.status} · {s.session_id.slice(0, 20)}…
            </option>
          ))}
        </select>
      </div>

      {/* Session Meta */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 mb-6 flex flex-wrap gap-6">
        <div>
          <p className="text-xs text-gray-600 mb-1">Agent</p>
          <p className="text-sm font-semibold text-white">{session.agent_name}</p>
        </div>
        <div>
          <p className="text-xs text-gray-600 mb-1">Framework</p>
          <FrameworkBadge framework={session.framework} />
        </div>
        <div>
          <p className="text-xs text-gray-600 mb-1">Status</p>
          <StatusBadge status={session.status} />
        </div>
        <div>
          <p className="text-xs text-gray-600 mb-1">Total Duration</p>
          <p className="text-sm text-gray-200">{formatDuration(session.duration_ms)}</p>
        </div>
        <div>
          <p className="text-xs text-gray-600 mb-1">Spans</p>
          <p className="text-sm text-gray-200">{session.span_count}</p>
        </div>
        <div>
          <p className="text-xs text-gray-600 mb-1">LLM Calls</p>
          <p className="text-sm text-gray-200">{session.llm_calls}</p>
        </div>
        <div>
          <p className="text-xs text-gray-600 mb-1">Tool Calls</p>
          <p className="text-sm text-gray-200">{session.tool_calls}</p>
        </div>
      </div>

      {/* Legend */}
      <div className="flex gap-4 mb-4 flex-wrap">
        {Object.entries(KIND_COLORS).map(([kind, color]) => (
          <div key={kind} className="flex items-center gap-1.5 text-xs text-gray-500">
            <div className={cn('w-2.5 h-2.5 rounded', color)} />
            {kind}
          </div>
        ))}
      </div>

      {/* Waterfall Table */}
      {timeline ? (
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800">
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider w-64">Span</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider w-20">Status</th>
                <th className="text-right px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider w-20">Duration</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider w-20">Time</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Waterfall</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => (
                <SpanRow key={entry.span_id} entry={entry} totalMs={timeline.total_ms} />
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-16 text-center text-gray-600">
          <p>No timeline data available for this session.</p>
          <p className="text-xs mt-1">Select a session with recorded spans.</p>
        </div>
      )}
    </div>
  );
}
