import { cn } from '../lib/utils';

interface PageHeaderProps {
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export function PageHeader({ title, description, action }: PageHeaderProps) {
  return (
    <div className="flex items-start justify-between mb-8">
      <div>
        <h1 className="text-xl font-semibold tracking-tight" style={{ color: 'var(--text-primary)' }}>
          {title}
        </h1>
        {description && (
          <p className="mt-1 text-[13px]" style={{ color: 'var(--text-tertiary)' }}>
            {description}
          </p>
        )}
      </div>
      {action && <div>{action}</div>}
    </div>
  );
}

interface CardProps {
  className?: string;
  children: React.ReactNode;
  style?: React.CSSProperties;
}

export function Card({ className, children, style }: CardProps) {
  return (
    <div className={cn('card', className)} style={style}>
      {children}
    </div>
  );
}

export function CardHeader({ title, sub }: { title: string; sub?: string }) {
  return (
    <div className="px-5 pt-5 pb-4" style={{ borderBottom: '1px solid var(--border)' }}>
      <p className="text-[13px] font-medium" style={{ color: 'var(--text-secondary)' }}>{title}</p>
      {sub && <p className="text-[11px] mt-0.5" style={{ color: 'var(--text-tertiary)' }}>{sub}</p>}
    </div>
  );
}
