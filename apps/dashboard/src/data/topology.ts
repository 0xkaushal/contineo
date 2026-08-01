import type { Node, Edge } from '@xyflow/react';
import { mockSessions, mockAnalytics } from './mock';

// ─── Types ────────────────────────────────────────────────────────

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

// ─── Agent → Tool wiring ──────────────────────────────────────────

const AGENT_TOOLS: Record<string, string[]> = {
  'weather-agent':        ['get_weather', 'get_forecast', 'format_response'],
  'research-agent':       ['search_web', 'read_file'],
  'customer-support-bot': ['search_web', 'format_response', 'read_file', 'write_file'],
  'code-review-agent':    ['read_file', 'write_file', 'format_response', 'search_web'],
  'data-analysis-agent':  ['read_file', 'format_response'],
};

// ─── Node dimensions (must match rendered sizes) ──────────────────

const AGENT_W = 210;
const AGENT_H = 110;
const TOOL_H  = 90;

// ─── Build graph ─────────────────────────────────────────────────

export function buildTopologyGraph(): { nodes: Node[]; edges: Edge[] } {
  // ── Aggregate agent stats ──────────────────────────────────────
  const agentStats: Record<string, AgentNodeData> = {};
  for (const s of mockSessions) {
    if (!agentStats[s.agent_name]) {
      agentStats[s.agent_name] = {
        agentName: s.agent_name,
        framework: s.framework,
        sessionCount: 0, successCount: 0,
        failedCount: 0, runningCount: 0,
        llmCalls: 0, toolCalls: 0,
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

  const toolStats: Record<string, { callCount: number; successRate: number }> = {};
  for (const t of mockAnalytics.top_tools) {
    toolStats[t.name] = { callCount: t.count, successRate: t.success_rate };
  }

  const agentNames = Object.keys(agentStats);
  const usedTools  = new Set<string>();
  for (const a of agentNames) {
    for (const t of AGENT_TOOLS[a] ?? []) usedTools.add(t);
  }
  const toolList = Array.from(usedTools);

  // ── Layout: bipartite, agents left / tools right ───────────────
  //
  // Agent column: evenly spaced, centred vertically.
  // Tool column:  each tool Y = weighted centroid of agent rows that use it,
  //               then push apart if they still collide.

  const V_PAD   = 40;   // padding from canvas top
  const H_GAP   = 320;  // horizontal gap between columns

  const AGENT_X = 60;
  const TOOL_X  = AGENT_X + AGENT_W + H_GAP;

  // Place agents evenly
  const AGENT_Y_GAP = AGENT_H + 60;
  const agentY: Record<string, number> = {};
  agentNames.forEach((name, i) => {
    agentY[name] = V_PAD + i * AGENT_Y_GAP;
  });

  // For each tool, compute centroid of agents that use it (by agent centre Y)
  const toolCentroid: Record<string, number> = {};
  for (const toolName of toolList) {
    const users = agentNames.filter((a) => (AGENT_TOOLS[a] ?? []).includes(toolName));
    if (users.length === 0) {
      toolCentroid[toolName] = V_PAD;
    } else {
      const avgY = users.reduce((sum, a) => sum + agentY[a] + AGENT_H / 2, 0) / users.length;
      toolCentroid[toolName] = avgY - TOOL_H / 2;
    }
  }

  // Sort tools by centroid so push-apart runs top-to-bottom
  const sortedTools = [...toolList].sort((a, b) => toolCentroid[a] - toolCentroid[b]);

  // Push apart: ensure min spacing between consecutive tools
  const MIN_TOOL_GAP = TOOL_H + 28;
  const toolY: Record<string, number> = {};
  sortedTools.forEach((name, i) => {
    if (i === 0) {
      toolY[name] = Math.max(V_PAD, toolCentroid[name]);
    } else {
      const prev = sortedTools[i - 1];
      const minY = toolY[prev] + MIN_TOOL_GAP;
      toolY[name] = Math.max(toolCentroid[name], minY);
    }
  });

  // ── Build nodes ────────────────────────────────────────────────
  const nodes: Node[] = [];

  agentNames.forEach((name) => {
    nodes.push({
      id: `agent__${name}`,
      type: 'agentNode',
      position: { x: AGENT_X, y: agentY[name] },
      data: agentStats[name],
    });
  });

  for (const toolName of toolList) {
    const stat = toolStats[toolName] ?? { callCount: 0, successRate: 0 };
    const users = agentNames.filter((a) => (AGENT_TOOLS[a] ?? []).includes(toolName));
    nodes.push({
      id: `tool__${toolName}`,
      type: 'toolNode',
      position: { x: TOOL_X, y: toolY[toolName] },
      data: {
        toolName,
        callCount: stat.callCount,
        successRate: stat.successRate,
        agentNames: users,
      } satisfies ToolNodeData,
    });
  }

  // ── Build edges ────────────────────────────────────────────────
  //
  // Key anti-overlap tricks:
  //   1. Use bezier ('default') not smoothstep — bezier curves spread naturally.
  //   2. Give each edge a unique sourceY offset so N edges leaving the same
  //      agent exit at different vertical positions on the right handle.
  //   3. Give each edge a unique targetY offset so N edges arriving at the
  //      same tool arrive at different vertical positions on the left handle.
  //   4. No edge labels (they land on top of each other) — put call count
  //      only in the detail panel.

  const edges: Edge[] = [];
  let idx = 0;

  // Pre-compute per-node edge counts for offset spread
  const agentEdgeCount: Record<string, number>  = {};
  const agentEdgeCursor: Record<string, number> = {};
  const toolEdgeCount: Record<string, number>   = {};
  const toolEdgeCursor: Record<string, number>  = {};

  for (const agentName of agentNames) {
    agentEdgeCount[agentName] = (AGENT_TOOLS[agentName] ?? []).length;
    agentEdgeCursor[agentName] = 0;
  }
  for (const toolName of toolList) {
    toolEdgeCount[toolName] = agentNames.filter((a) =>
      (AGENT_TOOLS[a] ?? []).includes(toolName)).length;
    toolEdgeCursor[toolName] = 0;
  }

  for (const agentName of agentNames) {
    const tools = AGENT_TOOLS[agentName] ?? [];
    for (const toolName of tools) {
      if (!toolY[toolName]) continue;

      const stat = toolStats[toolName] ?? { callCount: 0, successRate: 100 };
      const agentCount = toolEdgeCount[toolName] ?? 1;
      const perAgentCalls = Math.round(stat.callCount / Math.max(agentCount, 1));

      // Compute vertical offset for source (agent right side)
      const aTotalEdges = agentEdgeCount[agentName];
      const aIdx        = agentEdgeCursor[agentName]++;
      // Spread across 60% of node height, centred
      const aSpread = Math.min(AGENT_H * 0.6, (aTotalEdges - 1) * 18);
      const aOffset = aTotalEdges > 1
        ? -aSpread / 2 + aIdx * (aSpread / (aTotalEdges - 1))
        : 0;

      // Compute vertical offset for target (tool left side)
      const tTotalEdges = toolEdgeCount[toolName];
      const tIdx        = toolEdgeCursor[toolName]++;
      const tSpread = Math.min(TOOL_H * 0.6, (tTotalEdges - 1) * 16);
      const tOffset = tTotalEdges > 1
        ? -tSpread / 2 + tIdx * (tSpread / (tTotalEdges - 1))
        : 0;

      const edgeColor =
        stat.successRate >= 95 ? '#7c6af7'
        : stat.successRate >= 80 ? '#f59e0b'
        : '#ef4444';

      const isRunning = (agentStats[agentName]?.runningCount ?? 0) > 0;

      edges.push({
        id: `e${idx++}`,
        source: `agent__${agentName}`,
        target: `tool__${toolName}`,
        // Use 'default' bezier — curves diverge naturally, avoid parallel overlap
        type: 'default',
        animated: isRunning,
        // Offset source/target handles using sourceY/targetY in markerEnd is
        // not supported directly — instead we embed offsets via data and let
        // a custom edge handle it. Here we use the simplest approach: unique
        // handle IDs per edge so React Flow treats each exit point separately.
        sourceHandle: null,
        targetHandle: null,
        // Embed the pixel offsets so TopologyPage can render custom edges
        data: {
          callCount: perAgentCalls,
          avgLatencyLabel: '~480ms',
          sourceOffset: aOffset,
          targetOffset: tOffset,
        } satisfies EdgeData & { sourceOffset: number; targetOffset: number },
        style: {
          stroke: edgeColor,
          strokeWidth: 1.5,
          opacity: 0.6,
        },
        markerEnd: {
          type: 'arrowclosed' as const,
          color: edgeColor,
          width: 10,
          height: 10,
        },
      });
    }
  }

  return { nodes, edges };
}
