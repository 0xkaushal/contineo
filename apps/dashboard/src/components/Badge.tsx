import type { SessionStatus, SpanStatus, Framework, SpanKind } from '../types';
import { cn } from '../lib/utils';

interface BadgeProps {
  className?: string;
  style?: React.CSSProperties;
  children: React.ReactNode;
}

export function Badge({ className, style, children }: BadgeProps) {
  return (
    <span
      className={cn('inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[11px] font-medium tracking-wide', className)}
      style={style}
    >
      {children}
    </span>
  );
}

export function StatusBadge({ status }: { status: SessionStatus | SpanStatus }) {
  const styles: Record<string, { bg: string; color: string; dot: string }> = {
    completed: { bg: 'rgba(52,211,153,0.1)', color: '#34d399', dot: '#34d399' },
    failed:    { bg: 'rgba(248,113,113,0.1)', color: '#f87171', dot: '#f87171' },
    running:   { bg: 'rgba(251,191,36,0.1)', color: '#fbbf24', dot: '#fbbf24' },
  };
  const s = styles[status] ?? { bg: 'rgba(255,255,255,0.06)', color: 'rgba(255,255,255,0.4)', dot: 'rgba(255,255,255,0.3)' };
  return (
    <Badge style={{ background: s.bg, color: s.color }}>
      <span
        className={cn('w-1.5 h-1.5 rounded-full flex-shrink-0', status === 'running' && 'animate-pulse')}
        style={{ background: s.dot }}
      />
      {status}
    </Badge>
  );
}

export function FrameworkBadge({ framework }: { framework: Framework }) {
  const styles: Record<string, { bg: string; color: string }> = {
    langgraph: { bg: 'rgba(59,130,246,0.1)', color: '#60a5fa' },
    pipecat:   { bg: 'rgba(168,85,247,0.1)', color: '#c084fc' },
    openai:    { bg: 'rgba(52,211,153,0.1)', color: '#34d399' },
    livekit:   { bg: 'rgba(6,182,212,0.1)', color: '#22d3ee' },
    mcp:       { bg: 'rgba(251,146,60,0.1)', color: '#fb923c' },
    custom:    { bg: 'rgba(255,255,255,0.06)', color: 'rgba(255,255,255,0.4)' },
    unknown:   { bg: 'rgba(255,255,255,0.04)', color: 'rgba(255,255,255,0.25)' },
  };
  const s = styles[framework] ?? styles.unknown;
  return <Badge style={{ background: s.bg, color: s.color }}>{framework}</Badge>;
}

export function KindBadge({ kind }: { kind: SpanKind }) {
  const styles: Record<string, { bg: string; color: string }> = {
    session: { bg: 'rgba(124,106,247,0.12)', color: '#a78bfa' },
    llm:     { bg: 'rgba(59,130,246,0.1)', color: '#60a5fa' },
    tool:    { bg: 'rgba(251,191,36,0.1)', color: '#fbbf24' },
    memory:  { bg: 'rgba(236,72,153,0.1)', color: '#f472b6' },
    context: { bg: 'rgba(20,184,166,0.1)', color: '#2dd4bf' },
    tts:     { bg: 'rgba(99,102,241,0.1)', color: '#818cf8' },
    stt:     { bg: 'rgba(14,165,233,0.1)', color: '#38bdf8' },
    error:   { bg: 'rgba(248,113,113,0.1)', color: '#f87171' },
  };
  const s = styles[kind] ?? { bg: 'rgba(255,255,255,0.06)', color: 'rgba(255,255,255,0.4)' };
  return <Badge style={{ background: s.bg, color: s.color }}>{kind}</Badge>;
}
