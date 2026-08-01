import { NavLink } from 'react-router-dom';
import { LayoutGrid, GitBranch, PlayCircle, BarChart2, DollarSign, Zap, Sun, Moon } from 'lucide-react';
import { cn } from '../lib/utils';
import { useTheme } from '../lib/theme';

const navItems = [
  { to: '/', label: 'Sessions', icon: LayoutGrid, end: true },
  { to: '/timeline', label: 'Timeline', icon: GitBranch },
  { to: '/replay', label: 'Replay', icon: PlayCircle },
  { to: '/analytics', label: 'Analytics', icon: BarChart2 },
  { to: '/costs', label: 'Costs', icon: DollarSign },
];

export function Sidebar() {
  const { theme, toggle } = useTheme();

  return (
    <aside
      className="fixed left-0 top-0 h-screen w-56 flex flex-col z-20"
      style={{ background: 'var(--bg-2)', borderRight: '1px solid var(--border)' }}
    >
      {/* Logo */}
      <div className="px-5 pt-6 pb-5">
        <div className="flex items-center gap-2.5">
          <div
            className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
            style={{ background: 'linear-gradient(135deg, #7c6af7 0%, #a78bfa 100%)' }}
          >
            <Zap size={13} className="text-white" strokeWidth={2.5} />
          </div>
          <div className="leading-tight">
            <p className="text-sm font-semibold tracking-tight" style={{ color: 'var(--text-primary)' }}>
              Contineo
            </p>
            <p className="text-[10px] font-medium tracking-widest uppercase" style={{ color: 'var(--text-muted)' }}>
              Observe
            </p>
          </div>
        </div>
      </div>

      {/* Divider */}
      <div className="mx-5 mb-4" style={{ height: '1px', background: 'var(--border)' }} />

      {/* Nav label */}
      <p className="px-5 mb-2 label-xs">Views</p>

      {/* Nav */}
      <nav className="flex-1 px-3 space-y-0.5">
        {navItems.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className="flex items-center gap-3 px-3 py-2 rounded-lg text-[13px] font-medium transition-all duration-150 group relative"
            style={({ isActive }) =>
              isActive
                ? { background: 'var(--accent-dim)', color: 'var(--accent-light)' }
                : { color: 'var(--text-tertiary)' }
            }
          >
            {({ isActive }) => (
              <>
                {isActive && (
                  <span
                    className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-4 rounded-r"
                    style={{ background: 'var(--accent)' }}
                  />
                )}
                <Icon
                  size={15}
                  strokeWidth={isActive ? 2 : 1.75}
                  style={{ color: isActive ? 'var(--accent-light)' : 'inherit', flexShrink: 0 }}
                />
                <span className={cn(!isActive && 'group-hover:text-[var(--text-primary)]')}>{label}</span>
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-4 py-4 space-y-2">
        {/* Theme toggle */}
        <button
          onClick={toggle}
          className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg transition-all"
          style={{
            background: 'var(--bg-3)',
            border: '1px solid var(--border)',
            color: 'var(--text-secondary)',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'var(--border-md)')}
          onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'var(--border)')}
        >
          {theme === 'dark' ? (
            <Sun size={13} strokeWidth={1.75} style={{ color: 'var(--warning)' }} />
          ) : (
            <Moon size={13} strokeWidth={1.75} style={{ color: 'var(--accent)' }} />
          )}
          <span className="text-[12px] font-medium">
            {theme === 'dark' ? 'Light mode' : 'Dark mode'}
          </span>
        </button>

        {/* Status */}
        <div
          className="flex items-center gap-2 px-3 py-2"
          style={{ color: 'var(--text-muted)' }}
        >
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-[11px]">v0.1.1 · read-only</span>
        </div>
      </div>
    </aside>
  );
}
