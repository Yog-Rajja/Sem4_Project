import cn from '../../lib/cn'

export default function Card({ className, as: Tag = 'div', ...rest }) {
  return (
    <Tag
      className={cn(
        'rounded-card border border-line bg-surface shadow-card',
        className,
      )}
      {...rest}
    />
  )
}

export function CardHeader({ title, subtitle, action, className }) {
  return (
    <div className={cn('flex items-start justify-between gap-4 px-5 pt-4 pb-3', className)}>
      <div className="min-w-0">
        <h2 className="text-[15px] font-semibold tracking-[-0.01em] text-ink">{title}</h2>
        {subtitle && <p className="mt-0.5 text-[13px] text-ink-muted">{subtitle}</p>}
      </div>
      {action}
    </div>
  )
}
