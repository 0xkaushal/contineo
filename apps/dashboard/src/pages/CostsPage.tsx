import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell,
} from 'recharts';
import { mockCosts } from '../data/mock';
import { StatCard } from '../components/StatCard';
import { formatCost, formatTokens, formatDate } from '../lib/utils';

const COLORS = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b'];

const tooltipStyle = {
  backgroundColor: '#111827',
  border: '1px solid #1f2937',
  borderRadius: '8px',
  color: '#e5e7eb',
  fontSize: 12,
};

export function CostsPage() {
  const data = mockCosts;

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">Costs</h1>
        <p className="text-gray-500 text-sm mt-1">Token usage and cost tracking across providers · Last 7 days</p>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <StatCard label="Total Cost" value={`$${data.total_cost_usd.toFixed(3)}`} sub="Last 7 days" />
        <StatCard label="LLM Cost" value={`$${data.llm_cost_usd.toFixed(3)}`} sub={`${((data.llm_cost_usd / data.total_cost_usd) * 100).toFixed(0)}% of total`} />
        <StatCard label="Total Tokens" value={formatTokens(data.total_tokens)} sub={`${formatTokens(data.prompt_tokens)} prompt / ${formatTokens(data.completion_tokens)} completion`} />
        <StatCard label="Voice Costs" value={`$${(data.tts_cost_usd + data.stt_cost_usd).toFixed(3)}`} sub={`TTS $${data.tts_cost_usd.toFixed(3)} · STT $${data.stt_cost_usd.toFixed(3)}`} />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-3 gap-6 mb-6">
        {/* Cost over time */}
        <div className="col-span-2 bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-300 mb-4">Cost Over Time</h3>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={data.cost_over_time} margin={{ top: 4, right: 4, bottom: 0, left: -10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#6b7280' }} />
              <YAxis tick={{ fontSize: 11, fill: '#6b7280' }} />
              <Tooltip contentStyle={tooltipStyle} formatter={(v) => [`$${Number(v).toFixed(3)}`, 'Cost']} />
              <Line type="monotone" dataKey="cost" stroke="#8b5cf6" strokeWidth={2} dot={{ fill: '#8b5cf6', r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Cost by provider */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-300 mb-4">By Provider</h3>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie
                data={data.cost_by_provider}
                dataKey="cost"
                nameKey="provider"
                cx="50%"
                cy="50%"
                outerRadius={65}
                label={({ provider, percent }: { provider?: string; percent?: number }) => `${provider ?? ''} ${((percent ?? 0) * 100).toFixed(0)}%`}
                labelLine={false}
              >
                {data.cost_by_provider.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip contentStyle={tooltipStyle} formatter={(v) => [`$${Number(v).toFixed(3)}`, 'Cost']} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Cost by model */}
      <div className="grid grid-cols-2 gap-6 mb-6">
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-300 mb-4">Cost by Model</h3>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={data.cost_by_model} layout="vertical" margin={{ top: 0, right: 20, bottom: 0, left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 11, fill: '#6b7280' }} />
              <YAxis dataKey="model" type="category" tick={{ fontSize: 11, fill: '#6b7280' }} width={120} />
              <Tooltip contentStyle={tooltipStyle} formatter={(v) => [`$${Number(v).toFixed(4)}`, 'Cost']} />
              <Bar dataKey="cost" fill="#8b5cf6" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Token breakdown */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gray-300 mb-4">Token Breakdown by Model</h3>
          <div className="space-y-3 mt-2">
            {data.cost_by_model.map((m, i) => (
              <div key={m.model}>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-gray-300 font-mono">{m.model}</span>
                  <span className="text-gray-500">{formatTokens(m.tokens)} tokens · ${m.cost.toFixed(4)}</span>
                </div>
                <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${(m.tokens / data.total_tokens) * 100}%`,
                      backgroundColor: COLORS[i % COLORS.length],
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Per-session table */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-800">
          <h3 className="text-sm font-semibold text-gray-300">Session Cost Breakdown</h3>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800">
              <th className="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Session</th>
              <th className="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Agent</th>
              <th className="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Model</th>
              <th className="text-right px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Tokens</th>
              <th className="text-right px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">LLM</th>
              <th className="text-right px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Voice</th>
              <th className="text-right px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Total</th>
              <th className="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800/60">
            {data.entries.map((entry) => (
              <tr key={entry.session_id} className="hover:bg-gray-800/30 transition-colors">
                <td className="px-5 py-3">
                  <code className="text-xs text-violet-400 font-mono">{entry.session_id.slice(0, 20)}…</code>
                </td>
                <td className="px-5 py-3 text-gray-200">{entry.agent_name}</td>
                <td className="px-5 py-3">
                  <code className="text-xs text-gray-400">{entry.model}</code>
                </td>
                <td className="px-5 py-3 text-right text-gray-300 font-mono text-xs">
                  {formatTokens(entry.total_tokens)}
                </td>
                <td className="px-5 py-3 text-right text-gray-300 font-mono text-xs">
                  {formatCost(entry.llm_cost_usd)}
                </td>
                <td className="px-5 py-3 text-right text-gray-300 font-mono text-xs">
                  {entry.tts_cost_usd + entry.stt_cost_usd > 0
                    ? formatCost(entry.tts_cost_usd + entry.stt_cost_usd)
                    : '—'}
                </td>
                <td className="px-5 py-3 text-right">
                  <span className="text-white font-semibold text-xs">{formatCost(entry.total_cost_usd)}</span>
                </td>
                <td className="px-5 py-3 text-gray-500 text-xs">{formatDate(entry.timestamp)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
