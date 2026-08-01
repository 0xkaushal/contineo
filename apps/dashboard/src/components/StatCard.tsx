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
    trend === 'up' ? '#34d399' : trend === 'down' ? '#f87171' : 'rgba(255,255,255,0.3)';

  return (
    <div
      className={cn('rounded-xl p-5 flex flex-col gap-3', className)}
      style={{
        background: '#13131a',
        border: '1px solid rgba(255,255,255,0.06)',
      }}
    >
      <p
        className="text-[11px] font-semibold tracking-widest uppercase"
        style={{ color: 'rgba(255,255,255,0.3)' }}
      >
        {label}
      </p>
      <p className="text-[26px] font-semibold tracking-tight leading-none" style={{ color: '#e2e2ea' }}>
        {value}
      </p>
      {(sub || trendValue) && (
        <p className="text-[12px]" style={{ color: trendValue ? trendColor : 'rgba(255,255,255,0.3)' }}>
          {trendValue ?? sub}
        </p>
      )}
    </div>
  );
}
