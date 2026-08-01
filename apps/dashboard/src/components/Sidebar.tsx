import { NavLink } from 'react-router-dom';
import {
  LayoutGrid,
  GitBranch,
  PlayCircle,
  BarChart2,
  DollarSign,
  Zap,
} from 'lucide-react';
import { cn } from '../lib/utils';

const navItems = [
  { to: '/', label: 'Sessions', icon: LayoutGrid, end: true },
  { to: '/timeline', label: 'Timeline', icon: GitBranch },
  { to: '/replay', label: 'Replay', icon: PlayCircle },
  { to: '/analytics', label: 'Analytics', icon: BarChart2 },
  { to: '/costs', label: 'Costs', icon: DollarSign },
];

export function Sidebar() {
  return (
    <aside
      className="fixed left-0 top-0 h-screen w-56 flex flex-col z-20"
      style={{
        background: '#0d0d12',
        borderRight: '1px solid rgba(255,255,255,0.05)',
      }}
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
            <p className="text-sm font-semibold tracking-tight" style={{ color: '#e2e2ea' }}>Contineo</p>
            <p className="text-[10px] font-medium tracking-widest uppercase" style={{ color: 'rgba(255,255,255,0.3)' }}>Observe</p>
          </div>
        </div>
      </div>

      {/* Divider */}
      <div className="mx-5 mb-4" style={{ height: '1px', background: 'rgba(255,255,255,0.05)' }} />

      {/* Nav label */}
      <p className="px-5 mb-2 text-[10px] font-semibold tracking-widest uppercase" style={{ color: 'rgba(255,255,255,0.2)' }}>
        Views
      </p>

      {/* Nav */}
      <nav className="flex-1 px-3 space-y-0.5">
        {navItems.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 px-3 py-2 rounded-lg text-[13px] font-medium transition-all duration-150 group relative',
                isActive
                  ? 'text-white'
                  : 'hover:text-white'
              )
            }
            style={({ isActive }) => isActive
              ? { background: 'rgba(124,106,247,0.15)', color: '#c4b5fd' }
              : { color: 'rgba(255,255,255,0.35)' }
            }
          >
            {({ isActive }) => (
              <>
                {isActive && (
                  <span
                    className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-4 rounded-r"
                    style={{ background: '#7c6af7' }}
                  />
                )}
                <Icon
                  size={15}
                  strokeWidth={isActive ? 2 : 1.75}
                  style={{ color: isActive ? '#a78bfa' : 'inherit', flexShrink: 0 }}
                />
                <span>{label}</span>
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-5 py-5">
        <div
          className="flex items-center gap-2 px-3 py-2.5 rounded-lg"
          style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.05)' }}
        >
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-[11px]" style={{ color: 'rgba(255,255,255,0.3)' }}>
            v0.1.1 · read-only
          </span>
        </div>
      </div>
    </aside>
  );
}
