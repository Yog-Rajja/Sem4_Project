import { motion } from 'framer-motion'
import cn from '../../lib/cn'

export default function Card({ className, as: Tag = motion.div, ...rest }) {
  return (
    <Tag
      whileHover={{ y: -2 }}
      transition={{ type: 'spring', stiffness: 400 }}
      className={cn(
        'rounded-3xl border border-line bg-surface shadow-card',
        className,
      )}
      {...rest}
    />
  )
}

export function CardHeader({ title, subtitle, action, className }) {
  return (
    <div className={cn('flex items-start justify-between gap-4 px-6 pt-6 pb-4 border-b border-line/50', className)}>
      <div className="min-w-0">
        <h2 className="font-heading text-[20px] font-bold text-ink">{title}</h2>
        {subtitle && <p className="mt-1 text-[14px] text-ink-soft">{subtitle}</p>}
      </div>
      {action}
    </div>
  )
}
