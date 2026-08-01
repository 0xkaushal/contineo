import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend,
} from 'recharts';
import { mockAnalytics } from '../data/mock';
import { StatCard } from '../components/StatCard';
import { formatDuration } from '../lib/utils';

const COLORS = ['#8b5cf6', '#3b82f6', '#f59e0b', '#10b981', '#ec4899', '#06b6d4'];

const tooltipStyle = {
  backgroundColor: '#111827',
  border: '1px solid #1f2937',
  borderRadius: '8px',
  color: '#e5e7eb',
  fontSize: 12,
};

export function AnalyticsPage() {
  const data = mockAnalytics;

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">Analytics</h1>
        <p className="text-gray-500 text-sm mt-1">Aggregate metrics across all sessions · Last 7 days</p>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <StatCard
          label="Total Sessions"
          value={data.total_sessions}
          trendValue={`Last 7 days`}
          trend="neutral"
        />
        <StatCard
          label="Success Rate"
          value={`${data.success_rate}%`}
          trendValue="↑ 2.1% vs prior week"
          trend="up"
        />
        <StatCard
          label="Avg Latency"
          value={formatDuration(data.avg_latency_ms)}
          sub={`p95: ${formatDuration(data.latency_p95)}`}
        />
        <StatCard
          label="Avg Tool Calls"
          value={data.avg_tool_calls.toFixed(1)}
          sub={`Avg LLM calls: ${data.avg_llm_calls.toFixed(1)}`}
        />
      </div>

      {/* Latency percentiles */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        <StatCard label="p50 Latency" value={formatDuration(data.latency_p50)} />
        <StatCard label="p95 Latency" value={formatDuration(data.latency_p95)} />
        <StatCard label="p99 Latency" value={formatDuration(data.latency_p99)} />
      </div>

      {/* Charts row 1 */}
      <div className="grid grid-cols-2 gap-6 mb-6">
        {/* Sessions over time */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-300 mb-4">Sessions Over Time</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={data.sessions_over_time} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#6b7280' }} />
              <YAxis tick={{ fontSize: 11, fill: '#6b7280' }} />
              <Tooltip contentStyle={tooltipStyle} />
              <Legend wrapperStyle={{ fontSize: 11, color: '#6b7280' }} />
              <Bar dataKey="success" stackId="a" fill="#10b981" radius={[0, 0, 0, 0]} name="Success" />
              <Bar dataKey="failed" stackId="a" fill="#ef4444" radius={[3, 3, 0, 0]} name="Failed" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Latency over time */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-300 mb-4">Avg Latency Over Time</h3>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={data.latency_over_time} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#6b7280' }} />
              <YAxis tick={{ fontSize: 11, fill: '#6b7280' }} />
              <Tooltip contentStyle={tooltipStyle} formatter={(v) => [`${v}ms`, 'Avg Latency']} />
              <Line type="monotone" dataKey="avg_ms" stroke="#8b5cf6" strokeWidth={2} dot={{ fill: '#8b5cf6', r: 3 }} name="Avg ms" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Charts row 2 */}
      <div className="grid grid-cols-3 gap-6">
        {/* Framework breakdown */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-300 mb-4">Framework Breakdown</h3>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie
                data={data.framework_breakdown}
                dataKey="count"
                nameKey="framework"
                cx="50%"
                cy="50%"
                outerRadius={70}
                label={({ framework, percent }: { framework?: string; percent?: number }) => `${framework ?? ''} ${((percent ?? 0) * 100).toFixed(0)}%`}
                labelLine={false}
              >
                {data.framework_breakdown.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip contentStyle={tooltipStyle} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Top tools */}
        <div className="col-span-2 bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-300 mb-4">Top Tools</h3>
          <div className="space-y-3">
            {data.top_tools.map((tool) => (
              <div key={tool.name}>
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="text-gray-300 font-mono">{tool.name}</span>
                  <div className="flex gap-3">
                    <span className="text-gray-500">{tool.count} calls</span>
                    <span className={tool.success_rate >= 95 ? 'text-emerald-400' : 'text-amber-400'}>
                      {tool.success_rate}% success
                    </span>
                  </div>
                </div>
                <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-violet-500 rounded-full"
                    style={{ width: `${(tool.count / data.top_tools[0].count) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
