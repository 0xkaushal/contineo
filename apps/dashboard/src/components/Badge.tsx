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

// Status badge — uses CSS vars for accessible light/dark colours
export function StatusBadge({ status }: { status: SessionStatus | SpanStatus }) {
  const cfg: Record<string, { bg: string; color: string; pulse?: boolean }> = {
    completed: { bg: 'var(--success-dim)',  color: 'var(--success)' },
    failed:    { bg: 'var(--danger-dim)',   color: 'var(--danger)' },
    running:   { bg: 'var(--warning-dim)',  color: 'var(--warning)', pulse: true },
  };
  const s = cfg[status] ?? { bg: 'var(--bg-3)', color: 'var(--text-tertiary)' };
  return (
    <Badge style={{ background: s.bg, color: s.color }}>
      <span
        className={cn('w-1.5 h-1.5 rounded-full flex-shrink-0', s.pulse && 'animate-pulse')}
        style={{ background: s.color }}
      />
      {status}
    </Badge>
  );
}

export function FrameworkBadge({ framework }: { framework: Framework }) {
  // Fixed colours that work on both light and dark (sufficient contrast both ways)
  const cfg: Record<string, { bg: string; color: string }> = {
    langgraph: { bg: 'rgba(59,130,246,0.12)',  color: '#3b82f6' },
    pipecat:   { bg: 'rgba(168,85,247,0.12)',  color: '#a855f7' },
    openai:    { bg: 'rgba(16,185,129,0.12)',  color: '#10b981' },
    livekit:   { bg: 'rgba(6,182,212,0.12)',   color: '#06b6d4' },
    mcp:       { bg: 'rgba(251,146,60,0.12)',  color: '#f97316' },
    custom:    { bg: 'var(--bg-3)',             color: 'var(--text-secondary)' },
    unknown:   { bg: 'var(--bg-3)',             color: 'var(--text-muted)' },
  };
  const s = cfg[framework] ?? cfg.unknown;
  return <Badge style={{ background: s.bg, color: s.color }}>{framework}</Badge>;
}

export function KindBadge({ kind }: { kind: SpanKind }) {
  const cfg: Record<string, { bg: string; color: string }> = {
    session: { bg: 'var(--accent-dim)',           color: 'var(--accent-light)' },
    llm:     { bg: 'rgba(59,130,246,0.12)',        color: '#3b82f6' },
    tool:    { bg: 'rgba(251,191,36,0.12)',         color: '#d97706' },
    memory:  { bg: 'rgba(236,72,153,0.12)',         color: '#ec4899' },
    context: { bg: 'rgba(20,184,166,0.12)',         color: '#14b8a6' },
    tts:     { bg: 'rgba(99,102,241,0.12)',         color: '#6366f1' },
    stt:     { bg: 'rgba(14,165,233,0.12)',         color: '#0ea5e9' },
    error:   { bg: 'var(--danger-dim)',             color: 'var(--danger)' },
  };
  const s = cfg[kind] ?? { bg: 'var(--bg-3)', color: 'var(--text-secondary)' };
  return <Badge style={{ background: s.bg, color: s.color }}>{kind}</Badge>;
}
