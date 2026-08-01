import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { mockSessions, mockReplays } from '../data/mock';
import { FrameworkBadge } from '../components/Badge';
import { PageHeader, Card } from '../components/PageHeader';
import { formatTimestamp } from '../lib/utils';
import { cn } from '../lib/utils';
import type { EventType } from '../types';
import { ChevronDown, ChevronRight } from 'lucide-react';

const EVENT_ACCENT: Record<string, string> = {
  'session.started':  '#7c6af7',
  'session.finished': '#7c6af7',
  'llm.started':      '#3b82f6',
  'llm.completed':    '#60a5fa',
  'tool.called':      '#f59e0b',
  'tool.completed':   '#fbbf24',
  'tool.failed':      '#ef4444',
  'memory.read':      '#ec4899',
  'memory.write':     '#ec4899',
  'context.loaded':   '#14b8a6',
  'tts.started':      '#6366f1',
  'tts.completed':    '#818cf8',
  'stt.started':      '#0ea5e9',
  'stt.completed':    '#38bdf8',
  error:              '#ef4444',
};

type EventCardEvent = {
  event_id: string;
  sequence: number;
  timestamp: string;
  event_type: EventType;
  metadata: Record<string, unknown>;
  span_id: string;
};

function EventCard({ event, isLast }: { event: EventCardEvent; isLast: boolean }) {
  const [open, setOpen] = useState(false);
  const hasMetadata = Object.keys(event.metadata).length > 0;
  const accent = EVENT_ACCENT[event.event_type] ?? 'rgba(255,255,255,0.3)';

  return (
    <div className="relative flex gap-3">
      {/* Connector line + dot */}
      <div className="flex flex-col items-center flex-shrink-0 mt-0.5" style={{ width: 20 }}>
        <div
          className="w-2.5 h-2.5 rounded-full flex-shrink-0 mt-2.5"
          style={{ background: accent, boxShadow: `0 0 6px ${accent}55` }}
        />
        {!isLast && (
          <div className="flex-1 w-px mt-1" style={{ background: 'rgba(255,255,255,0.06)' }} />
        )}
      </div>

      {/* Card */}
      <div
        className="flex-1 mb-2 rounded-lg overflow-hidden"
        style={{ border: `1px solid rgba(255,255,255,0.06)`, background: '#13131a' }}
      >
        <div
          className={cn('flex items-center justify-between px-4 py-2.5', hasMetadata && 'cursor-pointer')}
          onClick={() => hasMetadata && setOpen(!open)}
          style={hasMetadata ? undefined : undefined}
        >
          <div className="flex items-center gap-3 min-w-0">
            <span className="text-[11px] font-mono flex-shrink-0" style={{ color: 'rgba(255,255,255,0.2)', width: 18, textAlign: 'right' }}>
              {event.sequence}
            </span>
            <div
              className="w-1 h-3.5 rounded-full flex-shrink-0"
              style={{ background: accent, opacity: 0.7 }}
            />
            <code className="text-[12px] font-medium" style={{ color: accent }}>
              {event.event_type}
            </code>
            <code className="text-[11px] font-mono truncate hidden sm:block" style={{ color: 'rgba(255,255,255,0.18)' }}>
              {event.span_id}
            </code>
          </div>
          <div className="flex items-center gap-3 flex-shrink-0">
            <span className="text-[11px] font-mono" style={{ color: 'rgba(255,255,255,0.2)' }}>
              {formatTimestamp(event.timestamp)}
            </span>
            {hasMetadata && (
              <span style={{ color: 'rgba(255,255,255,0.2)' }}>
                {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
              </span>
            )}
          </div>
        </div>

        {open && hasMetadata && (
          <div
            className="px-5 py-3 grid grid-cols-2 gap-x-8 gap-y-1.5"
            style={{ borderTop: '1px solid rgba(255,255,255,0.05)', background: 'rgba(255,255,255,0.015)' }}
          >
            {Object.entries(event.metadata).map(([k, v]) => (
              <div key={k} className="text-[12px]">
                <span style={{ color: 'rgba(255,255,255,0.25)' }}>{k}: </span>
                <code style={{ color: 'rgba(255,255,255,0.6)' }}>{String(v)}</code>
              </div>
            ))}
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
    <div className="px-8 py-8 max-w-[1400px]">
      <PageHeader title="Replay" description="Reconstruct event sequences from past sessions" />

      {/* Session Picker */}
      <div className="mb-6">
        <label className="block text-[10px] font-semibold tracking-widest uppercase mb-2" style={{ color: 'rgba(255,255,255,0.2)' }}>
          Session
        </label>
        <select
          value={selectedId}
          onChange={(e) => setSearchParams({ session: e.target.value })}
          className="rounded-lg px-4 py-2.5 text-[13px] outline-none max-w-lg w-full"
          style={{ background: '#13131a', border: '1px solid rgba(255,255,255,0.07)', color: '#e2e2ea' }}
        >
          {sessionsWithReplay.map((s) => (
            <option key={s.session_id} value={s.session_id} style={{ background: '#1a1a24' }}>
              {s.agent_name} · {s.framework} · {s.session_id.slice(5, 21)}…
            </option>
          ))}
        </select>
      </div>

      {replay && session ? (
        <div className="grid grid-cols-5 gap-5">
          {/* Events */}
          <div className="col-span-3">
            <p className="text-[12px] font-medium mb-4" style={{ color: 'rgba(255,255,255,0.3)' }}>
              {replay.events.length} events
            </p>
            <div>
              {replay.events.map((evt, i) => (
                <EventCard key={evt.event_id} event={evt} isLast={i === replay.events.length - 1} />
              ))}
            </div>
          </div>

          {/* Side panel */}
          <div className="col-span-2 space-y-3">
            {/* Session info */}
            <Card className="p-5">
              <p className="text-[10px] font-semibold tracking-widest uppercase mb-4" style={{ color: 'rgba(255,255,255,0.2)' }}>
                Session Info
              </p>
              <div className="space-y-3">
                {[
                  { k: 'Agent', v: <span className="font-medium text-[13px]" style={{ color: '#e2e2ea' }}>{session.agent_name}</span> },
                  { k: 'Framework', v: <FrameworkBadge framework={session.framework} /> },
                  { k: 'Events', v: <span className="text-[13px]" style={{ color: 'rgba(255,255,255,0.5)' }}>{replay.events.length}</span> },
                ].map(({ k, v }) => (
                  <div key={k} className="flex items-center justify-between">
                    <span className="text-[12px]" style={{ color: 'rgba(255,255,255,0.3)' }}>{k}</span>
                    {v}
                  </div>
                ))}
              </div>
            </Card>

            {replay.prompt && (
              <Card className="p-5">
                <p className="text-[10px] font-semibold tracking-widest uppercase mb-3" style={{ color: 'rgba(255,255,255,0.2)' }}>
                  Input
                </p>
                <p className="text-[13px] leading-relaxed" style={{ color: 'rgba(255,255,255,0.55)' }}>
                  {replay.prompt}
                </p>
              </Card>
            )}

            {replay.output && (
              <Card
                className="p-5"
                style={{ background: '#13131a', border: '1px solid rgba(52,211,153,0.15)' }}
              >
                <p className="text-[10px] font-semibold tracking-widest uppercase mb-3" style={{ color: 'rgba(52,211,153,0.5)' }}>
                  Output
                </p>
                <p className="text-[13px] leading-relaxed" style={{ color: 'rgba(255,255,255,0.55)' }}>
                  {replay.output}
                </p>
              </Card>
            )}
          </div>
        </div>
      ) : (
        <Card className="py-20 text-center">
          <p className="text-[13px]" style={{ color: 'rgba(255,255,255,0.2)' }}>
            No replay data for this session
          </p>
        </Card>
      )}
    </div>
  );
}
