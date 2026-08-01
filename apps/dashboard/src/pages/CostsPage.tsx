import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell,
} from 'recharts';
import { mockCosts } from '../data/mock';
import { StatCard } from '../components/StatCard';
import { PageHeader, Card } from '../components/PageHeader';
import { formatCost, formatTokens, formatDate } from '../lib/utils';

const PALETTE = ['#3b82f6', '#7c6af7', '#10b981', '#f59e0b'];

const tooltip = {
  backgroundColor: '#13131a',
  border: '1px solid rgba(255,255,255,0.07)',
  borderRadius: 8,
  color: '#e2e2ea',
  fontSize: 12,
  boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
};

const axis = { fontSize: 11, fill: 'rgba(255,255,255,0.2)' };

const TH = 'px-5 py-3 text-left text-[10px] font-semibold tracking-widest uppercase';
const TD = 'px-5 py-3.5';

export function CostsPage() {
  const data = mockCosts;

  return (
    <div className="px-8 py-8 max-w-[1400px]">
      <PageHeader title="Costs" description="Token usage and cost tracking across providers · Last 7 days" />

      {/* KPIs */}
      <div className="grid grid-cols-4 gap-3 mb-6">
        <StatCard label="Total Cost" value={`$${data.total_cost_usd.toFixed(3)}`} sub="Last 7 days" />
        <StatCard
          label="LLM Cost"
          value={`$${data.llm_cost_usd.toFixed(3)}`}
          sub={`${((data.llm_cost_usd / data.total_cost_usd) * 100).toFixed(0)}% of total`}
        />
        <StatCard
          label="Total Tokens"
          value={formatTokens(data.total_tokens)}
          sub={`${formatTokens(data.prompt_tokens)} in / ${formatTokens(data.completion_tokens)} out`}
        />
        <StatCard
          label="Voice"
          value={`$${(data.tts_cost_usd + data.stt_cost_usd).toFixed(3)}`}
          sub={`TTS $${data.tts_cost_usd.toFixed(3)} · STT $${data.stt_cost_usd.toFixed(3)}`}
        />
      </div>

      {/* Charts row 1 */}
      <div className="grid grid-cols-3 gap-4 mb-4">
        <Card className="col-span-2 p-5">
          <p className="text-[12px] font-medium mb-5" style={{ color: 'rgba(255,255,255,0.4)' }}>Cost Over Time</p>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={data.cost_over_time} margin={{ top: 0, right: 4, bottom: 0, left: -16 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
              <XAxis dataKey="date" tick={axis} axisLine={false} tickLine={false} />
              <YAxis tick={axis} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={tooltip} formatter={(v) => [`$${Number(v).toFixed(3)}`, 'Cost']} />
              <defs>
                <linearGradient id="costLine" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor="#7c6af7" />
                  <stop offset="100%" stopColor="#a78bfa" />
                </linearGradient>
              </defs>
              <Line
                type="monotone"
                dataKey="cost"
                stroke="url(#costLine)"
                strokeWidth={2}
                dot={{ fill: '#7c6af7', r: 3, strokeWidth: 0 }}
                activeDot={{ r: 5, fill: '#a78bfa', strokeWidth: 0 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </Card>

        <Card className="p-5">
          <p className="text-[12px] font-medium mb-3" style={{ color: 'rgba(255,255,255,0.4)' }}>By Provider</p>
          <ResponsiveContainer width="100%" height={180}>
            <PieChart>
              <Pie
                data={data.cost_by_provider}
                dataKey="cost"
                nameKey="provider"
                cx="50%"
                cy="50%"
                innerRadius={40}
                outerRadius={62}
                paddingAngle={3}
                label={({ provider, percent }: { provider?: string; percent?: number }) =>
                  `${provider ?? ''} ${((percent ?? 0) * 100).toFixed(0)}%`
                }
                labelLine={false}
              >
                {data.cost_by_provider.map((_, i) => (
                  <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
                ))}
              </Pie>
              <Tooltip contentStyle={tooltip} formatter={(v) => [`$${Number(v).toFixed(3)}`, 'Cost']} />
            </PieChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* Charts row 2 */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <Card className="p-5">
          <p className="text-[12px] font-medium mb-5" style={{ color: 'rgba(255,255,255,0.4)' }}>Cost by Model</p>
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={data.cost_by_model} layout="vertical" margin={{ top: 0, right: 16, bottom: 0, left: 8 }} barSize={10}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" horizontal={false} />
              <XAxis type="number" tick={axis} axisLine={false} tickLine={false} />
              <YAxis dataKey="model" type="category" tick={axis} width={110} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={tooltip} formatter={(v) => [`$${Number(v).toFixed(4)}`, 'Cost']} />
              <Bar dataKey="cost" fill="#7c6af7" radius={[0, 4, 4, 0]} opacity={0.8} />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card className="p-5">
          <p className="text-[12px] font-medium mb-5" style={{ color: 'rgba(255,255,255,0.4)' }}>Tokens by Model</p>
          <div className="space-y-4 mt-1">
            {data.cost_by_model.map((m, i) => (
              <div key={m.model}>
                <div className="flex justify-between items-center mb-1.5">
                  <code className="text-[12px]" style={{ color: 'rgba(255,255,255,0.55)' }}>{m.model}</code>
                  <span className="text-[11px]" style={{ color: 'rgba(255,255,255,0.25)' }}>
                    {formatTokens(m.tokens)} · ${m.cost.toFixed(4)}
                  </span>
                </div>
                <div className="h-1 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.05)' }}>
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${(m.tokens / data.total_tokens) * 100}%`,
                      background: PALETTE[i % PALETTE.length],
                      opacity: 0.7,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Session table */}
      <Card>
        <div className="px-5 py-4" style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
          <p className="text-[13px] font-medium" style={{ color: 'rgba(255,255,255,0.5)' }}>Session Breakdown</p>
        </div>
        <table className="w-full">
          <thead>
            <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
              {['Session', 'Agent', 'Model', 'Tokens', 'LLM', 'Voice', 'Total', 'Date'].map((h, i) => (
                <th
                  key={h}
                  className={TH}
                  style={{
                    color: 'rgba(255,255,255,0.2)',
                    textAlign: i >= 3 && i <= 6 ? 'right' : 'left',
                  }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.entries.map((entry, i) => (
              <tr
                key={entry.session_id}
                style={{ borderBottom: i < data.entries.length - 1 ? '1px solid rgba(255,255,255,0.04)' : 'none' }}
                onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255,255,255,0.025)')}
                onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
              >
                <td className={TD}>
                  <code className="text-[11px] font-mono" style={{ color: 'rgba(167,139,250,0.7)' }}>
                    {entry.session_id.slice(5, 21)}…
                  </code>
                </td>
                <td className={TD}>
                  <span className="text-[13px]" style={{ color: 'rgba(255,255,255,0.6)' }}>{entry.agent_name}</span>
                </td>
                <td className={TD}>
                  <code className="text-[12px]" style={{ color: 'rgba(255,255,255,0.35)' }}>{entry.model}</code>
                </td>
                <td className={`${TD} text-right`}>
                  <span className="text-[12px] font-mono" style={{ color: 'rgba(255,255,255,0.45)' }}>
                    {formatTokens(entry.total_tokens)}
                  </span>
                </td>
                <td className={`${TD} text-right`}>
                  <span className="text-[12px] font-mono" style={{ color: 'rgba(255,255,255,0.45)' }}>
                    {formatCost(entry.llm_cost_usd)}
                  </span>
                </td>
                <td className={`${TD} text-right`}>
                  <span className="text-[12px] font-mono" style={{ color: 'rgba(255,255,255,0.3)' }}>
                    {entry.tts_cost_usd + entry.stt_cost_usd > 0
                      ? formatCost(entry.tts_cost_usd + entry.stt_cost_usd)
                      : '—'}
                  </span>
                </td>
                <td className={`${TD} text-right`}>
                  <span className="text-[13px] font-semibold" style={{ color: '#e2e2ea' }}>
                    {formatCost(entry.total_cost_usd)}
                  </span>
                </td>
                <td className={TD}>
                  <span className="text-[12px]" style={{ color: 'rgba(255,255,255,0.25)' }}>
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
