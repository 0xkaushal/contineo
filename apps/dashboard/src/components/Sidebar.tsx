import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Clock,
  PlayCircle,
  BarChart3,
  DollarSign,
  Activity,
  ChevronRight,
} from 'lucide-react';
import { cn } from '../lib/utils';

const navItems = [
  { to: '/', label: 'Sessions', icon: LayoutDashboard, end: true },
  { to: '/timeline', label: 'Timeline', icon: Clock },
  { to: '/replay', label: 'Replay', icon: PlayCircle },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/costs', label: 'Costs', icon: DollarSign },
];

export function Sidebar() {
  return (
    <aside className="fixed left-0 top-0 h-screen w-60 bg-gray-950 border-r border-gray-800 flex flex-col z-10">
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-5 py-5 border-b border-gray-800">
        <div className="w-7 h-7 rounded-lg bg-violet-600 flex items-center justify-center">
          <Activity size={14} className="text-white" />
        </div>
        <div>
          <span className="text-white font-semibold text-sm tracking-wide">Contineo</span>
          <span className="text-gray-500 text-xs block leading-none">Observe</span>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {navItems.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors group',
                isActive
                  ? 'bg-violet-600/20 text-violet-300'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/60'
              )
            }
          >
            {({ isActive }) => (
              <>
                <Icon size={16} className={cn(isActive ? 'text-violet-400' : 'text-gray-500 group-hover:text-gray-300')} />
                <span className="flex-1">{label}</span>
                {isActive && <ChevronRight size={12} className="text-violet-400" />}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-5 py-4 border-t border-gray-800">
        <p className="text-xs text-gray-600">v0.1.1 · read-only</p>
      </div>
    </aside>
  );
}
