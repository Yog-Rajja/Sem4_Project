import cn from '../../lib/cn'
import Spinner from './Spinner'

const VARIANTS = {
  primary:
    'bg-brand-600 text-white hover:bg-brand-700 disabled:hover:bg-brand-600 shadow-sm',
  secondary:
    'bg-surface text-ink border border-line hover:bg-surface-muted hover:border-line-strong',
  ghost: 'text-ink-soft hover:bg-surface-muted hover:text-ink',
  danger: 'bg-danger text-white hover:brightness-95',
  dangerGhost: 'text-ink-muted hover:bg-danger-soft hover:text-danger',
}

const SIZES = {
  sm: 'h-8 px-3 text-[13px] gap-1.5 rounded-lg',
  md: 'h-9.5 px-4 text-sm gap-2 rounded-lg',
  lg: 'h-11 px-5 text-[15px] gap-2 rounded-xl',
  icon: 'h-8 w-8 rounded-lg justify-center',
}

export default function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled,
  className,
  children,
  ...rest
}) {
  return (
    <button
      disabled={disabled || loading}
      className={cn(
        'inline-flex items-center font-medium transition-colors duration-150',
        'disabled:opacity-55 disabled:cursor-not-allowed select-none',
        VARIANTS[variant],
        SIZES[size],
        className,
      )}
      {...rest}
    >
      {loading && <Spinner size={size === 'lg' ? 16 : 14} />}
      {children}
    </button>
  )
}
