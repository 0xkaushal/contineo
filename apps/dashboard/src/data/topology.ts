import type { Node, Edge } from '@xyflow/react';
import { mockSessions, mockAnalytics } from './mock';

// ─── Types attached to each node's `data` ─────────────────────────

export interface AgentNodeData extends Record<string, unknown> {
  agentName: string;
  framework: string;
  sessionCount: number;
  successCount: number;
  failedCount: number;
  runningCount: number;
  llmCalls: number;
  toolCalls: number;
}

export interface ToolNodeData extends Record<string, unknown> {
  toolName: string;
  callCount: number;
  successRate: number;
  agentNames: string[];
}

export interface EdgeData extends Record<string, unknown> {
  callCount: number;
  avgLatencyLabel: string;
}

// ─── Hardcoded agent→tool mapping (derived from mock sessions/analytics) ──

const AGENT_TOOLS: Record<string, string[]> = {
  'weather-agent':      ['get_weather', 'get_forecast', 'format_response'],
  'research-agent':     ['search_web', 'read_file'],
  'customer-support-bot': ['search_web', 'format_response', 'read_file', 'write_file'],
  'code-review-agent':  ['read_file', 'write_file', 'format_response', 'search_web'],
  'data-analysis-agent': ['read_file', 'format_response'],
};

// ─── Build graph ───────────────────────────────────────────────────

export function buildTopologyGraph(): { nodes: Node[]; edges: Edge[] } {
  // Aggregate per-agent stats from sessions
  const agentStats: Record<string, AgentNodeData> = {};
  for (const s of mockSessions) {
    if (!agentStats[s.agent_name]) {
      agentStats[s.agent_name] = {
        agentName: s.agent_name,
        framework: s.framework,
        sessionCount: 0,
        successCount: 0,
        failedCount: 0,
        runningCount: 0,
        llmCalls: 0,
        toolCalls: 0,
      };
    }
    const a = agentStats[s.agent_name];
    a.sessionCount++;
    if (s.status === 'completed') a.successCount++;
    if (s.status === 'failed')    a.failedCount++;
    if (s.status === 'running')   a.runningCount++;
    a.llmCalls  += s.llm_calls;
    a.toolCalls += s.tool_calls;
  }

  // Tool lookup from analytics
  const toolStats: Record<string, { callCount: number; successRate: number }> = {};
  for (const t of mockAnalytics.top_tools) {
    toolStats[t.name] = { callCount: t.count, successRate: t.success_rate };
  }

  // Collect all unique tools referenced by agents present in sessions
  const agentNames = Object.keys(agentStats);
  const usedTools = new Set<string>();
  for (const a of agentNames) {
    for (const t of AGENT_TOOLS[a] ?? []) usedTools.add(t);
  }

  // ── Layout ──────────────────────────────────────────────────────
  // Agents arranged in a vertical column on the left-centre.
  // Tools fanned out to the right, positioned by first-seen agent.

  const AGENT_X = 160;
  const AGENT_Y_START = 60;
  const AGENT_Y_GAP = 180;

  const TOOL_X = 560;
  const TOOL_Y_START = 40;
  const TOOL_Y_GAP = 110;

  const nodes: Node[] = [];
  const edges: Edge[] = [];

  // Agent nodes
  agentNames.forEach((name, i) => {
    nodes.push({
      id: `agent__${name}`,
      type: 'agentNode',
      position: { x: AGENT_X, y: AGENT_Y_START + i * AGENT_Y_GAP },
      data: agentStats[name],
    });
  });

  // Tool nodes — unique, positioned vertically on right side
  const toolList = Array.from(usedTools);
  toolList.forEach((toolName, i) => {
    const stat = toolStats[toolName] ?? { callCount: 0, successRate: 0 };
    const agentsThatUse = agentNames.filter((a) => (AGENT_TOOLS[a] ?? []).includes(toolName));
    nodes.push({
      id: `tool__${toolName}`,
      type: 'toolNode',
      position: { x: TOOL_X, y: TOOL_Y_START + i * TOOL_Y_GAP },
      data: {
        toolName,
        callCount: stat.callCount,
        successRate: stat.successRate,
        agentNames: agentsThatUse,
      } satisfies ToolNodeData,
    });
  });

  // Edges: agent → tool
  let edgeIdx = 0;
  for (const agentName of agentNames) {
    for (const toolName of AGENT_TOOLS[agentName] ?? []) {
      if (!usedTools.has(toolName)) continue;
      const stat = toolStats[toolName] ?? { callCount: 0, successRate: 100 };
      // Rough per-agent-tool call count (divide evenly among agents that use it)
      const agentCount = agentNames.filter((a) => (AGENT_TOOLS[a] ?? []).includes(toolName)).length;
      const perAgentCalls = Math.round(stat.callCount / Math.max(agentCount, 1));
      edges.push({
        id: `e${edgeIdx++}`,
        source: `agent__${agentName}`,
        target: `tool__${toolName}`,
        type: 'smoothstep',
        animated: agentStats[agentName]?.runningCount > 0,
        label: `${perAgentCalls} calls`,
        labelStyle: { fontSize: 10, fill: 'var(--text-muted)' },
        labelBgStyle: { fill: 'var(--bg-2)', fillOpacity: 0.85 },
        labelBgPadding: [4, 6] as [number, number],
        labelBgBorderRadius: 4,
        style: {
          stroke: stat.successRate >= 95 ? '#7c6af7' : stat.successRate >= 80 ? '#f59e0b' : '#ef4444',
          strokeWidth: 1.5,
          opacity: 0.55,
        },
        data: {
          callCount: perAgentCalls,
          avgLatencyLabel: '~480ms',
        } satisfies EdgeData,
      });
    }
  }

  return { nodes, edges };
}
