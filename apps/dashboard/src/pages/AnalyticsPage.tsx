import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend,
} from 'recharts';
import { mockAnalytics } from '../data/mock';
import { StatCard } from '../components/StatCard';
import { PageHeader, Card } from '../components/PageHeader';
import { formatDuration } from '../lib/utils';
import { useTheme } from '../lib/theme';

const PALETTE = ['#7c6af7', '#3b82f6', '#f59e0b', '#10b981', '#ec4899', '#06b6d4'];

export function AnalyticsPage() {
  const { theme } = useTheme();
  const data = mockAnalytics;

  const tooltipStyle = {
    backgroundColor: theme === 'dark' ? '#13131a' : '#ffffff',
    border: `1px solid ${theme === 'dark' ? 'rgba(255,255,255,0.07)' : 'rgba(0,0,0,0.09)'}`,
    borderRadius: 8,
    color: theme === 'dark' ? '#e2e2ea' : '#111118',
    fontSize: 12,
    boxShadow: '0 8px 24px rgba(0,0,0,0.2)',
  };

  const axisColor = theme === 'dark' ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.3)';
  const axis = { fontSize: 11, fill: axisColor };
  const cursorFill = theme === 'dark' ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.03)';

  return (
    <div className="px-8 py-8 max-w-[1400px]">
      <PageHeader title="Analytics" description="Aggregate metrics · Last 7 days" />

      <div className="grid grid-cols-4 gap-3 mb-4">
        <StatCard label="Sessions" value={data.total_sessions} trendValue="Last 7 days" trend="neutral" />
        <StatCard label="Success Rate" value={`${data.success_rate}%`} trendValue="↑ 2.1% vs prior week" trend="up" />
        <StatCard label="Avg Latency" value={formatDuration(data.avg_latency_ms)} sub={`p95: ${formatDuration(data.latency_p95)}`} />
        <StatCard label="Avg Tool Calls" value={data.avg_tool_calls.toFixed(1)} sub={`LLM avg: ${data.avg_llm_calls.toFixed(1)}`} />
      </div>

      <div className="grid grid-cols-3 gap-3 mb-6">
        <StatCard label="p50 Latency" value={formatDuration(data.latency_p50)} />
        <StatCard label="p95 Latency" value={formatDuration(data.latency_p95)} />
        <StatCard label="p99 Latency" value={formatDuration(data.latency_p99)} />
      </div>

      <div className="grid grid-cols-2 gap-4 mb-4">
        <Card className="p-5">
          <p className="text-[12px] font-medium mb-5" style={{ color: 'var(--text-secondary)' }}>Sessions Over Time</p>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={data.sessions_over_time} margin={{ top: 0, right: 4, bottom: 0, left: -24 }} barSize={14}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="date" tick={axis} axisLine={false} tickLine={false} />
              <YAxis tick={axis} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={tooltipStyle} cursor={{ fill: cursorFill }} />
              <Legend wrapperStyle={{ fontSize: 11, color: axisColor }} iconType="circle" iconSize={7} />
              <Bar dataKey="success" stackId="a" fill="#10b981" radius={[0,0,0,0]} name="Success" />
              <Bar dataKey="failed"  stackId="a" fill="#ef4444" radius={[3,3,0,0]} name="Failed" />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card className="p-5">
          <p className="text-[12px] font-medium mb-5" style={{ color: 'var(--text-secondary)' }}>Avg Latency Over Time</p>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={data.latency_over_time} margin={{ top: 0, right: 4, bottom: 0, left: -24 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="date" tick={axis} axisLine={false} tickLine={false} />
              <YAxis tick={axis} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={tooltipStyle} formatter={(v) => [`${v}ms`, 'Latency']} />
              <defs>
                <linearGradient id="latencyGrad" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor="#7c6af7" />
                  <stop offset="100%" stopColor="#a78bfa" />
                </linearGradient>
              </defs>
              <Line type="monotone" dataKey="avg_ms" stroke="url(#latencyGrad)" strokeWidth={2}
                dot={{ fill: '#7c6af7', r: 3, strokeWidth: 0 }}
                activeDot={{ r: 5, fill: '#a78bfa', strokeWidth: 0 }} />
            </LineChart>
          </ResponsiveContainer>
        </Card>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <Card className="p-5">
          <p className="text-[12px] font-medium mb-4" style={{ color: 'var(--text-secondary)' }}>Frameworks</p>
          <ResponsiveContainer width="100%" height={180}>
            <PieChart>
              <Pie data={data.framework_breakdown} dataKey="count" nameKey="framework"
                cx="50%" cy="50%" innerRadius={45} outerRadius={70} paddingAngle={3}
                label={({ framework, percent }: { framework?: string; percent?: number }) =>
                  `${framework ?? ''} ${((percent ?? 0) * 100).toFixed(0)}%`}
                labelLine={false}
              >
                {data.framework_breakdown.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}
              </Pie>
              <Tooltip contentStyle={tooltipStyle} />
            </PieChart>
          </ResponsiveContainer>
        </Card>

        <Card className="col-span-2 p-5">
          <p className="text-[12px] font-medium mb-5" style={{ color: 'var(--text-secondary)' }}>Top Tools</p>
          <div className="space-y-4">
            {data.top_tools.map((tool, i) => (
              <div key={tool.name}>
                <div className="flex items-center justify-between mb-1.5">
                  <code className="text-[12px]" style={{ color: 'var(--text-secondary)' }}>{tool.name}</code>
                  <div className="flex gap-4 text-[11px]">
                    <span style={{ color: 'var(--text-tertiary)' }}>{tool.count} calls</span>
                    <span style={{ color: tool.success_rate >= 95 ? 'var(--success)' : 'var(--warning)' }}>
                      {tool.success_rate}%
                    </span>
                  </div>
                </div>
                <div className="h-1 rounded-full overflow-hidden" style={{ background: 'var(--bg-3)' }}>
                  <div className="h-full rounded-full"
                    style={{
                      width: `${(tool.count / data.top_tools[0].count) * 100}%`,
                      background: PALETTE[i % PALETTE.length],
                      opacity: 0.72,
                    }} />
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
