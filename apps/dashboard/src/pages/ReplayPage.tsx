import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { mockSessions, mockReplays } from '../data/mock';
import { FrameworkBadge } from '../components/Badge';
import { formatTimestamp } from '../lib/utils';
import { cn } from '../lib/utils';
import type { EventType } from '../types';
import { ChevronDown, ChevronRight } from 'lucide-react';

const EVENT_COLORS: Record<EventType | string, string> = {
  'session.started': 'border-violet-500 bg-violet-500/10',
  'session.finished': 'border-violet-500 bg-violet-500/10',
  'llm.started': 'border-blue-500 bg-blue-500/10',
  'llm.completed': 'border-blue-400 bg-blue-500/10',
  'tool.called': 'border-amber-500 bg-amber-500/10',
  'tool.completed': 'border-amber-400 bg-amber-500/10',
  'tool.failed': 'border-red-500 bg-red-500/10',
  'memory.read': 'border-pink-500 bg-pink-500/10',
  'memory.write': 'border-pink-500 bg-pink-500/10',
  'context.loaded': 'border-teal-500 bg-teal-500/10',
  'tts.started': 'border-indigo-500 bg-indigo-500/10',
  'tts.completed': 'border-indigo-400 bg-indigo-500/10',
  'stt.started': 'border-sky-500 bg-sky-500/10',
  'stt.completed': 'border-sky-400 bg-sky-500/10',
  error: 'border-red-500 bg-red-500/10',
};

const EVENT_DOT: Record<EventType | string, string> = {
  'session.started': 'bg-violet-500',
  'session.finished': 'bg-violet-400',
  'llm.started': 'bg-blue-500',
  'llm.completed': 'bg-blue-400',
  'tool.called': 'bg-amber-500',
  'tool.completed': 'bg-amber-400',
  'tool.failed': 'bg-red-500',
  error: 'bg-red-500',
};

function EventCard({ event, index }: { event: { event_id: string; sequence: number; timestamp: string; event_type: EventType; metadata: Record<string, unknown>; span_id: string }; index: number }) {
  const [open, setOpen] = useState(false);
  const hasMetadata = Object.keys(event.metadata).length > 0;
  const borderClass = EVENT_COLORS[event.event_type] ?? 'border-gray-700 bg-gray-800/30';
  const dotClass = EVENT_DOT[event.event_type] ?? 'bg-gray-500';

  return (
    <div className="relative flex gap-4">
      {/* Timeline line */}
      <div className="flex flex-col items-center">
        <div className={cn('w-3 h-3 rounded-full mt-3.5 flex-shrink-0 ring-2 ring-gray-900', dotClass)} />
        {index < 11 && <div className="w-0.5 flex-1 bg-gray-800 mt-1" />}
      </div>
      {/* Card */}
      <div className={cn('flex-1 mb-3 border rounded-lg', borderClass)}>
        <div
          className="flex items-center justify-between px-4 py-2.5 cursor-pointer"
          onClick={() => hasMetadata && setOpen(!open)}
        >
          <div className="flex items-center gap-3">
            <span className="text-xs text-gray-600 font-mono w-5 text-right">{event.sequence}</span>
            <code className="text-xs font-medium text-gray-200">{event.event_type}</code>
            <code className="text-xs text-gray-600 font-mono hidden sm:block">{event.span_id}</code>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs text-gray-600 font-mono">{formatTimestamp(event.timestamp)}</span>
            {hasMetadata && (
              <span className="text-gray-600">
                {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
              </span>
            )}
          </div>
        </div>
        {open && hasMetadata && (
          <div className="border-t border-gray-800/50 px-4 py-3">
            <div className="grid grid-cols-2 gap-x-6 gap-y-1.5">
              {Object.entries(event.metadata).map(([k, v]) => (
                <div key={k} className="text-xs">
                  <span className="text-gray-600">{k}: </span>
                  <code className="text-gray-300">{String(v)}</code>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export function ReplayPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const sessionsWithReplay = mockSessions.filter((s) => mockReplays[s.session_id]);
  const selectedId = searchParams.get('session') ?? sessionsWithReplay[0]?.session_id ?? '';
  const session = mockSessions.find((s) => s.session_id === selectedId);
  const replay = mockReplays[selectedId];

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Replay</h1>
          <p className="text-gray-500 text-sm mt-1">Reconstruct event sequences from past sessions</p>
        </div>
      </div>

      {/* Session Picker */}
      <div className="mb-6">
        <label className="text-xs text-gray-500 uppercase tracking-wider font-medium mb-2 block">Session</label>
        <select
          value={selectedId}
          onChange={(e) => setSearchParams({ session: e.target.value })}
          className="bg-gray-900 border border-gray-700 text-gray-200 text-sm rounded-lg px-4 py-2.5 focus:outline-none focus:border-violet-500 max-w-lg w-full"
        >
          {sessionsWithReplay.map((s) => (
            <option key={s.session_id} value={s.session_id}>
              {s.agent_name} · {s.framework} · {s.session_id.slice(0, 20)}…
            </option>
          ))}
        </select>
      </div>

      {replay && session ? (
        <div className="grid grid-cols-5 gap-6">
          {/* Event sequence */}
          <div className="col-span-3">
            <h2 className="text-sm font-semibold text-gray-300 mb-4">Event Sequence ({replay.events.length} events)</h2>
            <div className="space-y-0">
              {replay.events.map((evt, i) => (
                <EventCard key={evt.event_id} event={evt} index={i} />
              ))}
            </div>
          </div>

          {/* Sidebar: prompt/output + meta */}
          <div className="col-span-2 space-y-4">
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
              <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">Session Info</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Agent</span>
                  <span className="text-gray-200 font-medium">{session.agent_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Framework</span>
                  <FrameworkBadge framework={session.framework} />
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Events</span>
                  <span className="text-gray-200">{replay.events.length}</span>
                </div>
              </div>
            </div>

            {replay.prompt && (
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
                <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">Input Prompt</h3>
                <p className="text-sm text-gray-300 leading-relaxed">{replay.prompt}</p>
              </div>
            )}
            {replay.output && (
              <div className="bg-gray-900 border border-emerald-900/40 rounded-xl p-5">
                <h3 className="text-xs font-medium text-emerald-600 uppercase tracking-wider mb-3">Final Output</h3>
                <p className="text-sm text-gray-300 leading-relaxed">{replay.output}</p>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-16 text-center text-gray-600">
          <p>No replay data available for this session.</p>
        </div>
      )}
    </div>
  );
}
