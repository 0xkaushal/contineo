import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell,
} from 'recharts';
import { mockCosts } from '../data/mock';
import { StatCard } from '../components/StatCard';
import { PageHeader, Card } from '../components/PageHeader';
import { formatCost, formatTokens, formatDate } from '../lib/utils';
import { useTheme } from '../lib/theme';

const PALETTE = ['#3b82f6', '#7c6af7', '#10b981', '#f59e0b'];

export function CostsPage() {
  const { theme } = useTheme();
  const data = mockCosts;

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

  return (
    <div className="px-8 py-8 max-w-[1400px]">
      <PageHeader title="Costs" description="Token usage and cost tracking · Last 7 days" />

      <div className="grid grid-cols-4 gap-3 mb-6">
        <StatCard label="Total Cost" value={`$${data.total_cost_usd.toFixed(3)}`} sub="Last 7 days" />
        <StatCard label="LLM Cost" value={`$${data.llm_cost_usd.toFixed(3)}`}
          sub={`${((data.llm_cost_usd / data.total_cost_usd) * 100).toFixed(0)}% of total`} />
        <StatCard label="Total Tokens" value={formatTokens(data.total_tokens)}
          sub={`${formatTokens(data.prompt_tokens)} in / ${formatTokens(data.completion_tokens)} out`} />
        <StatCard label="Voice" value={`$${(data.tts_cost_usd + data.stt_cost_usd).toFixed(3)}`}
          sub={`TTS $${data.tts_cost_usd.toFixed(3)} · STT $${data.stt_cost_usd.toFixed(3)}`} />
      </div>

      <div className="grid grid-cols-3 gap-4 mb-4">
        <Card className="col-span-2 p-5">
          <p className="text-[12px] font-medium mb-5" style={{ color: 'var(--text-secondary)' }}>Cost Over Time</p>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={data.cost_over_time} margin={{ top: 0, right: 4, bottom: 0, left: -16 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="date" tick={axis} axisLine={false} tickLine={false} />
              <YAxis tick={axis} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={tooltipStyle} formatter={(v) => [`$${Number(v).toFixed(3)}`, 'Cost']} />
              <defs>
                <linearGradient id="costGrad" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor="#7c6af7" />
                  <stop offset="100%" stopColor="#a78bfa" />
                </linearGradient>
              </defs>
              <Line type="monotone" dataKey="cost" stroke="url(#costGrad)" strokeWidth={2}
                dot={{ fill: '#7c6af7', r: 3, strokeWidth: 0 }}
                activeDot={{ r: 5, fill: '#a78bfa', strokeWidth: 0 }} />
            </LineChart>
          </ResponsiveContainer>
        </Card>

        <Card className="p-5">
          <p className="text-[12px] font-medium mb-3" style={{ color: 'var(--text-secondary)' }}>By Provider</p>
          <ResponsiveContainer width="100%" height={180}>
            <PieChart>
              <Pie data={data.cost_by_provider} dataKey="cost" nameKey="provider"
                cx="50%" cy="50%" innerRadius={40} outerRadius={62} paddingAngle={3}
                label={({ provider, percent }: { provider?: string; percent?: number }) =>
                  `${provider ?? ''} ${((percent ?? 0) * 100).toFixed(0)}%`}
                labelLine={false}
              >
                {data.cost_by_provider.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}
              </Pie>
              <Tooltip contentStyle={tooltipStyle} formatter={(v) => [`$${Number(v).toFixed(3)}`, 'Cost']} />
            </PieChart>
          </ResponsiveContainer>
        </Card>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-6">
        <Card className="p-5">
          <p className="text-[12px] font-medium mb-5" style={{ color: 'var(--text-secondary)' }}>Cost by Model</p>
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={data.cost_by_model} layout="vertical" margin={{ top: 0, right: 16, bottom: 0, left: 8 }} barSize={10}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} />
              <XAxis type="number" tick={axis} axisLine={false} tickLine={false} />
              <YAxis dataKey="model" type="category" tick={axis} width={110} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={tooltipStyle} formatter={(v) => [`$${Number(v).toFixed(4)}`, 'Cost']} />
              <Bar dataKey="cost" fill="#7c6af7" radius={[0,4,4,0]} opacity={0.8} />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card className="p-5">
          <p className="text-[12px] font-medium mb-5" style={{ color: 'var(--text-secondary)' }}>Tokens by Model</p>
          <div className="space-y-4 mt-1">
            {data.cost_by_model.map((m, i) => (
              <div key={m.model}>
                <div className="flex justify-between items-center mb-1.5">
                  <code className="text-[12px]" style={{ color: 'var(--text-secondary)' }}>{m.model}</code>
                  <span className="text-[11px]" style={{ color: 'var(--text-tertiary)' }}>
                    {formatTokens(m.tokens)} · ${m.cost.toFixed(4)}
                  </span>
                </div>
                <div className="h-1 rounded-full overflow-hidden" style={{ background: 'var(--bg-3)' }}>
                  <div className="h-full rounded-full"
                    style={{
                      width: `${(m.tokens / data.total_tokens) * 100}%`,
                      background: PALETTE[i % PALETTE.length],
                      opacity: 0.72,
                    }} />
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Session table */}
      <Card>
        <div className="px-5 py-4" style={{ borderBottom: '1px solid var(--border)' }}>
          <p className="text-[13px] font-medium" style={{ color: 'var(--text-secondary)' }}>Session Breakdown</p>
        </div>
        <table className="w-full">
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border)' }}>
              {['Session', 'Agent', 'Model', 'Tokens', 'LLM', 'Voice', 'Total', 'Date'].map((h, i) => (
                <th key={h} className="th" style={{ textAlign: i >= 3 && i <= 6 ? 'right' : 'left' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.entries.map((entry, i) => (
              <tr
                key={entry.session_id}
                style={{ borderBottom: i < data.entries.length - 1 ? '1px solid var(--border)' : 'none' }}
                onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-hover)')}
                onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
              >
                <td className="px-5 py-3.5">
                  <code className="text-[11px] font-mono" style={{ color: 'var(--accent)' }}>
                    {entry.session_id.slice(5, 21)}…
                  </code>
                </td>
                <td className="px-5 py-3.5">
                  <span className="text-[13px]" style={{ color: 'var(--text-secondary)' }}>{entry.agent_name}</span>
                </td>
                <td className="px-5 py-3.5">
                  <code className="text-[12px]" style={{ color: 'var(--text-tertiary)' }}>{entry.model}</code>
                </td>
                <td className="px-5 py-3.5 text-right">
                  <span className="text-[12px] font-mono" style={{ color: 'var(--text-secondary)' }}>
                    {formatTokens(entry.total_tokens)}
                  </span>
                </td>
                <td className="px-5 py-3.5 text-right">
                  <span className="text-[12px] font-mono" style={{ color: 'var(--text-secondary)' }}>
                    {formatCost(entry.llm_cost_usd)}
                  </span>
                </td>
                <td className="px-5 py-3.5 text-right">
                  <span className="text-[12px] font-mono" style={{ color: 'var(--text-tertiary)' }}>
                    {entry.tts_cost_usd + entry.stt_cost_usd > 0
                      ? formatCost(entry.tts_cost_usd + entry.stt_cost_usd)
                      : '—'}
                  </span>
                </td>
                <td className="px-5 py-3.5 text-right">
                  <span className="text-[13px] font-semibold" style={{ color: 'var(--text-primary)' }}>
                    {formatCost(entry.total_cost_usd)}
                  </span>
                </td>
                <td className="px-5 py-3.5">
                  <span className="text-[12px]" style={{ color: 'var(--text-tertiary)' }}>
                    {formatDate(entry.timestamp)}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
