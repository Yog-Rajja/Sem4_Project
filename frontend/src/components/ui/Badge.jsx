import cn from '../../lib/cn'

const TONES = {
  neutral: 'bg-surface-muted text-ink-soft border-line',
  brand: 'bg-brand-50 text-brand-700 border-brand-100',
  success: 'bg-success-soft text-success border-success/20',
  warning: 'bg-warning-soft text-warning border-warning/25',
  danger: 'bg-danger-soft text-danger border-danger/20',
}

export default function Badge({ tone = 'neutral', className, children }) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full border px-2 py-0.5',
        'text-[11.5px] font-medium whitespace-nowrap',
        TONES[tone],
        className,
      )}
    >
      {children}
    </span>
  )
}
