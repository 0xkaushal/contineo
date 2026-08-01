import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, RefreshCw, Bot, Cpu, Clock, AlertCircle } from 'lucide-react';
import { mockSessions } from '../data/mock';
import { StatusBadge, FrameworkBadge } from '../components/Badge';
import { StatCard } from '../components/StatCard';
import { formatDuration, formatTimestamp, formatDate } from '../lib/utils';
import type { Session } from '../types';

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

  const handleRowClick = (s: Session) => {
    navigate(`/timeline?session=${s.session_id}`);
  };

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Sessions</h1>
          <p className="text-gray-500 text-sm mt-1">All agent execution sessions</p>
        </div>
        <button className="flex items-center gap-2 px-3 py-2 bg-gray-800 hover:bg-gray-700 text-gray-400 hover:text-gray-200 rounded-lg text-sm transition-colors">
          <RefreshCw size={14} />
          Refresh
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <StatCard label="Total Sessions" value={total} sub="All time" />
        <StatCard label="Completed" value={completed} sub={`${((completed / total) * 100).toFixed(0)}% success rate`} trend="up" trendValue={`${((completed / total) * 100).toFixed(1)}% success`} />
        <StatCard label="Failed" value={failed} sub="Requires attention" />
        <StatCard label="Running" value={running} sub="Active now" trend={running > 0 ? 'neutral' : undefined} trendValue={running > 0 ? 'Live' : undefined} />
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 mb-5">
        <div className="relative flex-1 max-w-sm">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
          <input
            type="text"
            placeholder="Search sessions, agents..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-sm text-gray-200 placeholder:text-gray-600 focus:outline-none focus:border-violet-500 transition-colors"
          />
        </div>
        <div className="flex gap-2">
          {(['all', 'completed', 'failed', 'running'] as const).map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                statusFilter === s
                  ? 'bg-violet-600 text-white'
                  : 'bg-gray-800 text-gray-400 hover:text-gray-200 hover:bg-gray-700'
              }`}
            >
              {s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800">
              <th className="text-left px-5 py-3.5 text-xs font-medium text-gray-500 uppercase tracking-wider">Session ID</th>
              <th className="text-left px-5 py-3.5 text-xs font-medium text-gray-500 uppercase tracking-wider">Agent</th>
              <th className="text-left px-5 py-3.5 text-xs font-medium text-gray-500 uppercase tracking-wider">Framework</th>
              <th className="text-left px-5 py-3.5 text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
              <th className="text-left px-5 py-3.5 text-xs font-medium text-gray-500 uppercase tracking-wider">Duration</th>
              <th className="text-left px-5 py-3.5 text-xs font-medium text-gray-500 uppercase tracking-wider">LLM Calls</th>
              <th className="text-left px-5 py-3.5 text-xs font-medium text-gray-500 uppercase tracking-wider">Tool Calls</th>
              <th className="text-left px-5 py-3.5 text-xs font-medium text-gray-500 uppercase tracking-wider">Started</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800/60">
            {filtered.map((session) => (
              <tr
                key={session.session_id}
                onClick={() => handleRowClick(session)}
                className="hover:bg-gray-800/40 cursor-pointer transition-colors group"
              >
                <td className="px-5 py-3.5">
                  <code className="text-xs text-violet-400 font-mono group-hover:text-violet-300">
                    {session.session_id.slice(0, 24)}…
                  </code>
                </td>
                <td className="px-5 py-3.5">
                  <div className="flex items-center gap-2">
                    <Bot size={13} className="text-gray-500" />
                    <span className="text-gray-200 font-medium">{session.agent_name}</span>
                  </div>
                </td>
                <td className="px-5 py-3.5">
                  <FrameworkBadge framework={session.framework} />
                </td>
                <td className="px-5 py-3.5">
                  <StatusBadge status={session.status} />
                </td>
                <td className="px-5 py-3.5">
                  <div className="flex items-center gap-1.5 text-gray-300">
                    <Clock size={12} className="text-gray-600" />
                    {formatDuration(session.duration_ms)}
                  </div>
                </td>
                <td className="px-5 py-3.5">
                  <div className="flex items-center gap-1.5 text-gray-300">
                    <Cpu size={12} className="text-blue-500" />
                    {session.llm_calls}
                  </div>
                </td>
                <td className="px-5 py-3.5">
                  <div className="flex items-center gap-1.5 text-gray-300">
                    {session.error_count > 0 ? (
                      <AlertCircle size={12} className="text-red-500" />
                    ) : (
                      <span className="w-3 h-3" />
                    )}
                    {session.tool_calls}
                    {session.error_count > 0 && (
                      <span className="text-xs text-red-400">({session.error_count} err)</span>
                    )}
                  </div>
                </td>
                <td className="px-5 py-3.5 text-gray-500 text-xs">
                  <div>{formatDate(session.started_at)}</div>
                  <div className="text-gray-600">{formatTimestamp(session.started_at)}</div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length === 0 && (
          <div className="py-16 text-center text-gray-600">
            <Search size={24} className="mx-auto mb-2 opacity-40" />
            <p>No sessions match your search</p>
          </div>
        )}
      </div>
    </div>
  );
}
