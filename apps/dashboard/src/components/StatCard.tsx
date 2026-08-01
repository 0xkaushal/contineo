import { cn } from '../lib/utils';

interface StatCardProps {
  label: string;
  value: string | number;
  sub?: string;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
  className?: string;
}

export function StatCard({ label, value, sub, trend, trendValue, className }: StatCardProps) {
  const trendColor = trend === 'up' ? 'text-emerald-400' : trend === 'down' ? 'text-red-400' : 'text-gray-500';
  return (
    <div className={cn('bg-gray-900 border border-gray-800 rounded-xl p-5', className)}>
      <p className="text-xs text-gray-500 font-medium uppercase tracking-wider mb-2">{label}</p>
      <p className="text-2xl font-bold text-white">{value}</p>
      {(sub || trendValue) && (
        <p className={cn('text-xs mt-1', trendValue ? trendColor : 'text-gray-500')}>
          {trendValue ?? sub}
        </p>
      )}
    </div>
  );
}
