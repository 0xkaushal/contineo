import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, RefreshCw, Bot, Cpu, Wrench, AlertCircle, Clock } from 'lucide-react';
import { mockSessions } from '../data/mock';
import { StatusBadge, FrameworkBadge } from '../components/Badge';
import { StatCard } from '../components/StatCard';
import { PageHeader, Card } from '../components/PageHeader';
import { formatDuration, formatTimestamp, formatDate } from '../lib/utils';
import type { Session } from '../types';

const TH = 'px-5 py-3 text-left text-[10px] font-semibold tracking-widest uppercase';
const TD = 'px-5 py-3.5';

export function SessionsPage() {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  const filtered = mockSessions.filter((s) => {
    const matchSearch =
      s.session_id.includes(search) ||
      s.agent_name.toLowerCase().includes(search.toLowerCase()) ||
      s.framework.toLowerCase().includes(search.toLowerCase());
    const matchStatus = statusFilter === 'all' || s.status === statusFilter;
    return matchSearch && matchStatus;
  });

  const total = mockSessions.length;
  const completed = mockSessions.filter((s) => s.status === 'completed').length;
  const failed = mockSessions.filter((s) => s.status === 'failed').length;
  const running = mockSessions.filter((s) => s.status === 'running').length;

  const handleRowClick = (s: Session) => navigate(`/timeline?session=${s.session_id}`);

  return (
    <div className="px-8 py-8 max-w-[1400px]">
      <PageHeader
        title="Sessions"
        description="All agent execution sessions"
        action={
          <button
            className="flex items-center gap-2 px-3.5 py-2 rounded-lg text-[12px] font-medium transition-all"
            style={{
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid rgba(255,255,255,0.08)',
              color: 'rgba(255,255,255,0.45)',
            }}
          >
            <RefreshCw size={13} strokeWidth={1.75} />
            Refresh
          </button>
        }
      />

      {/* Stats */}
      <div className="grid grid-cols-4 gap-3 mb-8">
        <StatCard label="Total" value={total} />
        <StatCard
          label="Completed"
          value={completed}
          trendValue={`${((completed / total) * 100).toFixed(1)}% success rate`}
          trend="up"
        />
        <StatCard label="Failed" value={failed} sub={failed > 0 ? 'Requires attention' : 'None'} />
        <StatCard
          label="Running"
          value={running}
          trendValue={running > 0 ? 'Live now' : undefined}
          trend={running > 0 ? 'neutral' : undefined}
          sub={running === 0 ? 'None active' : undefined}
        />
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 mb-4">
        <div className="relative flex-1 max-w-xs">
          <Search
            size={13}
            strokeWidth={1.75}
            className="absolute left-3 top-1/2 -translate-y-1/2"
            style={{ color: 'rgba(255,255,255,0.25)' }}
          />
          <input
            type="text"
            placeholder="Search agent, session ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 rounded-lg text-[13px] transition-all outline-none"
            style={{
              background: '#13131a',
              border: '1px solid rgba(255,255,255,0.07)',
              color: '#e2e2ea',
            }}
            onFocus={(e) => (e.currentTarget.style.borderColor = 'rgba(124,106,247,0.5)')}
            onBlur={(e) => (e.currentTarget.style.borderColor = 'rgba(255,255,255,0.07)')}
          />
        </div>
        <div className="flex gap-1.5">
          {(['all', 'completed', 'failed', 'running'] as const).map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className="px-3 py-1.5 rounded-lg text-[12px] font-medium transition-all"
              style={
                statusFilter === s
                  ? { background: 'rgba(124,106,247,0.2)', color: '#a78bfa', border: '1px solid rgba(124,106,247,0.3)' }
                  : { background: 'rgba(255,255,255,0.04)', color: 'rgba(255,255,255,0.35)', border: '1px solid rgba(255,255,255,0.06)' }
              }
            >
              {s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <Card>
        <table className="w-full">
          <thead>
            <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
              <th className={TH} style={{ color: 'rgba(255,255,255,0.2)' }}>Session</th>
              <th className={TH} style={{ color: 'rgba(255,255,255,0.2)' }}>Agent</th>
              <th className={TH} style={{ color: 'rgba(255,255,255,0.2)' }}>Framework</th>
              <th className={TH} style={{ color: 'rgba(255,255,255,0.2)' }}>Status</th>
              <th className={TH} style={{ color: 'rgba(255,255,255,0.2)' }}>Duration</th>
              <th className={TH} style={{ color: 'rgba(255,255,255,0.2)' }}>LLM</th>
              <th className={TH} style={{ color: 'rgba(255,255,255,0.2)' }}>Tools</th>
              <th className={TH} style={{ color: 'rgba(255,255,255,0.2)' }}>Started</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((session, i) => (
              <tr
                key={session.session_id}
                onClick={() => handleRowClick(session)}
                className="cursor-pointer group transition-colors"
                style={{
                  borderBottom: i < filtered.length - 1 ? '1px solid rgba(255,255,255,0.04)' : 'none',
                }}
                onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255,255,255,0.025)')}
                onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
              >
                <td className={TD}>
                  <code
                    className="text-[11px] font-mono"
                    style={{ color: 'rgba(167,139,250,0.8)' }}
                  >
                    {session.session_id.slice(5, 21)}…
                  </code>
                </td>
                <td className={TD}>
                  <div className="flex items-center gap-2">
                    <Bot size={13} strokeWidth={1.5} style={{ color: 'rgba(255,255,255,0.25)', flexShrink: 0 }} />
                    <span className="text-[13px] font-medium" style={{ color: '#e2e2ea' }}>
                      {session.agent_name}
                    </span>
                  </div>
                </td>
                <td className={TD}>
                  <FrameworkBadge framework={session.framework} />
                </td>
                <td className={TD}>
                  <StatusBadge status={session.status} />
                </td>
                <td className={TD}>
                  <div className="flex items-center gap-1.5 text-[13px]" style={{ color: 'rgba(255,255,255,0.5)' }}>
                    <Clock size={12} strokeWidth={1.5} style={{ color: 'rgba(255,255,255,0.2)' }} />
                    {formatDuration(session.duration_ms)}
                  </div>
                </td>
                <td className={TD}>
                  <div className="flex items-center gap-1.5 text-[13px]" style={{ color: 'rgba(255,255,255,0.5)' }}>
                    <Cpu size={12} strokeWidth={1.5} style={{ color: '#60a5fa', opacity: 0.7 }} />
                    {session.llm_calls}
                  </div>
                </td>
                <td className={TD}>
                  <div className="flex items-center gap-1.5 text-[13px]" style={{ color: 'rgba(255,255,255,0.5)' }}>
                    {session.error_count > 0
                      ? <AlertCircle size={12} strokeWidth={1.5} style={{ color: '#f87171' }} />
                      : <Wrench size={12} strokeWidth={1.5} style={{ color: 'rgba(255,255,255,0.2)' }} />
                    }
                    {session.tool_calls}
                    {session.error_count > 0 && (
                      <span className="text-[11px]" style={{ color: '#f87171' }}>
                        {session.error_count} err
                      </span>
                    )}
                  </div>
                </td>
                <td className={TD}>
                  <div className="text-[12px]" style={{ color: 'rgba(255,255,255,0.35)' }}>
                    {formatDate(session.started_at)}
                    <span className="block text-[11px]" style={{ color: 'rgba(255,255,255,0.2)' }}>
                      {formatTimestamp(session.started_at)}
                    </span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length === 0 && (
          <div className="py-20 text-center">
            <Search size={20} strokeWidth={1.25} className="mx-auto mb-3" style={{ color: 'rgba(255,255,255,0.15)' }} />
            <p className="text-[13px]" style={{ color: 'rgba(255,255,255,0.25)' }}>No sessions match your filters</p>
          </div>
        )}
      </Card>
    </div>
  );
}
