import type { SessionStatus, SpanStatus, Framework, SpanKind } from '../types';
import { cn } from '../lib/utils';

interface BadgeProps {
  className?: string;
  children: React.ReactNode;
}

export function Badge({ className, children }: BadgeProps) {
  return (
    <span className={cn('inline-flex items-center px-2 py-0.5 rounded text-xs font-medium', className)}>
      {children}
    </span>
  );
}

export function StatusBadge({ status }: { status: SessionStatus | SpanStatus }) {
  const map: Record<string, string> = {
    completed: 'bg-emerald-500/15 text-emerald-400',
    failed: 'bg-red-500/15 text-red-400',
    running: 'bg-amber-500/15 text-amber-400',
  };
  const dot: Record<string, string> = {
    completed: 'bg-emerald-400',
    failed: 'bg-red-400',
    running: 'bg-amber-400 animate-pulse',
  };
  return (
    <Badge className={map[status] ?? 'bg-gray-700 text-gray-400'}>
      <span className={cn('w-1.5 h-1.5 rounded-full mr-1.5 inline-block', dot[status])} />
      {status}
    </Badge>
  );
}

export function FrameworkBadge({ framework }: { framework: Framework }) {
  const map: Record<string, string> = {
    langgraph: 'bg-blue-500/15 text-blue-400',
    pipecat: 'bg-purple-500/15 text-purple-400',
    openai: 'bg-green-500/15 text-green-400',
    livekit: 'bg-cyan-500/15 text-cyan-400',
    mcp: 'bg-orange-500/15 text-orange-400',
    custom: 'bg-gray-500/15 text-gray-400',
    unknown: 'bg-gray-700/30 text-gray-500',
  };
  return <Badge className={map[framework] ?? 'bg-gray-700 text-gray-400'}>{framework}</Badge>;
}

export function KindBadge({ kind }: { kind: SpanKind }) {
  const map: Record<string, string> = {
    session: 'bg-violet-500/15 text-violet-400',
    llm: 'bg-blue-500/15 text-blue-400',
    tool: 'bg-amber-500/15 text-amber-400',
    memory: 'bg-pink-500/15 text-pink-400',
    context: 'bg-teal-500/15 text-teal-400',
    tts: 'bg-indigo-500/15 text-indigo-400',
    stt: 'bg-sky-500/15 text-sky-400',
    error: 'bg-red-500/15 text-red-400',
  };
  return <Badge className={map[kind] ?? 'bg-gray-700 text-gray-400'}>{kind}</Badge>;
}
