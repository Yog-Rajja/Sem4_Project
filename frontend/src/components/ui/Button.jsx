import { motion } from 'framer-motion'
import cn from '../../lib/cn'
import Spinner from './Spinner'

const VARIANTS = {
  primary:
    'bg-brand-500 text-white shadow-pop hover:shadow-glow',
  secondary:
    'bg-surface text-ink border border-line shadow-card hover:border-brand-500',
  ghost:
    'text-ink-soft hover:bg-surface hover:text-brand-500',
  danger:
    'bg-danger text-white shadow-pop hover:shadow-glow',
  dangerGhost:
    'text-danger hover:bg-danger-soft',
}

const HOVER = {
  primary: 'hover:bg-brand-400',
  secondary: 'hover:text-brand-500',
  ghost: '',
  danger: 'hover:bg-brand-400',
  dangerGhost: '',
}

const SIZES = {
  sm: 'h-8 px-4 text-[13px] gap-2 rounded-2xl',
  md: 'h-10 px-5 text-[15px] gap-2.5 rounded-2xl',
  lg: 'h-12 px-6 text-[16px] gap-3 rounded-2xl',
  icon: 'h-10 w-10 rounded-2xl justify-center',
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
    <motion.button
      whileHover={{ scale: disabled || loading ? 1 : 1.03, rotate: disabled || loading ? 0 : 1 }}
      whileTap={{ scale: disabled || loading ? 1 : 0.95, rotate: 0 }}
      transition={{ type: 'spring', stiffness: 500, damping: 15 }}
      disabled={disabled || loading}
      className={cn(
        'inline-flex items-center font-bold font-sans duration-200 transition-colors',
        'disabled:opacity-50 disabled:cursor-not-allowed select-none',
        VARIANTS[variant],
        HOVER[variant],
        SIZES[size],
        className,
      )}
      {...rest}
    >
      {loading && <Spinner size={size === 'lg' ? 16 : 14} />}
      {children}
    </motion.button>
  )
}
