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
  const trendColor =
    trend === 'up'
      ? 'var(--success)'
      : trend === 'down'
      ? 'var(--danger)'
      : 'var(--text-tertiary)';

  return (
    <div className={cn('card p-5 flex flex-col gap-3', className)}>
      <p className="label-xs">{label}</p>
      <p className="text-[26px] font-semibold tracking-tight leading-none" style={{ color: 'var(--text-primary)' }}>
        {value}
      </p>
      {(sub || trendValue) && (
        <p className="text-[12px]" style={{ color: trendValue ? trendColor : 'var(--text-tertiary)' }}>
          {trendValue ?? sub}
        </p>
      )}
    </div>
  );
}
