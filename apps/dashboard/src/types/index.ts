export type EventType =
  | 'session.started'
  | 'session.finished'
  | 'llm.started'
  | 'llm.completed'
  | 'tool.called'
  | 'tool.completed'
  | 'tool.failed'
  | 'memory.read'
  | 'memory.write'
  | 'context.loaded'
  | 'tts.started'
  | 'tts.completed'
  | 'stt.started'
  | 'stt.completed'
  | 'error';

export type SpanKind = 'session' | 'llm' | 'tool' | 'memory' | 'context' | 'tts' | 'stt' | 'error';
export type SpanStatus = 'running' | 'completed' | 'failed';
export type SessionStatus = 'running' | 'completed' | 'failed';
export type Framework = 'langgraph' | 'pipecat' | 'openai' | 'livekit' | 'mcp' | 'custom' | 'unknown';

export interface BaseEvent {
  event_id: string;
  timestamp: string;
  project_id: string;
  session_id: string;
  trace_id: string;
  span_id: string;
  agent_name: string;
  framework: Framework;
  event_type: EventType;
  metadata: Record<string, unknown>;
  version: number;
}

export interface TimelineEntry {
  span_id: string;
  trace_id: string;
  session_id: string;
  kind: SpanKind;
  label: string;
  status: SpanStatus;
  started_at: string;
  finished_at: string | null;
  duration_ms: number | null;
  metadata: Record<string, unknown>;
  error: string | null;
}

export interface Timeline {
  session_id: string;
  entries: TimelineEntry[];
  total_ms: number;
  is_complete: boolean;
}

export interface Session {
  session_id: string;
  project_id: string;
  agent_name: string;
  framework: Framework;
  status: SessionStatus;
  started_at: string;
  finished_at: string | null;
  duration_ms: number | null;
  span_count: number;
  error_count: number;
  llm_calls: number;
  tool_calls: number;
}

export interface ReplayEvent extends BaseEvent {
  sequence: number;
}

export interface Replay {
  session_id: string;
  agent_name: string;
  framework: Framework;
  events: ReplayEvent[];
  prompt?: string;
  output?: string;
}

export interface AnalyticsMetrics {
  period: string;
  total_sessions: number;
  success_rate: number;
  avg_latency_ms: number;
  avg_llm_calls: number;
  avg_tool_calls: number;
  latency_p50: number;
  latency_p95: number;
  latency_p99: number;
  top_tools: { name: string; count: number; success_rate: number }[];
  sessions_over_time: { date: string; count: number; success: number; failed: number }[];
  latency_over_time: { date: string; avg_ms: number }[];
  framework_breakdown: { framework: string; count: number }[];
}

export interface CostEntry {
  session_id: string;
  agent_name: string;
  framework: Framework;
  provider: string;
  model: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  llm_cost_usd: number;
  tts_cost_usd: number;
  stt_cost_usd: number;
  tool_cost_usd: number;
  total_cost_usd: number;
  timestamp: string;
}

export interface CostSummary {
  total_cost_usd: number;
  llm_cost_usd: number;
  tts_cost_usd: number;
  stt_cost_usd: number;
  tool_cost_usd: number;
  total_tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
  cost_by_provider: { provider: string; cost: number }[];
  cost_by_model: { model: string; cost: number; tokens: number }[];
  cost_over_time: { date: string; cost: number }[];
  entries: CostEntry[];
}
