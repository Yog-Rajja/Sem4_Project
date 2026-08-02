import { motion } from 'framer-motion'
import cn from '../../lib/cn'

/** Standard page frame: title block, optional actions, animated content area. */
export default function PageShell({ title, subtitle, actions, children, className }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.24, ease: [0.22, 1, 0.36, 1] }}
      className={cn('mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 sm:py-8', className)}
    >
      {(title || actions) && (
        <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <h1 className="text-xl font-semibold tracking-[-0.02em] text-ink sm:text-[22px]">
              {title}
            </h1>
            {subtitle && (
              <p className="mt-1 text-[13.5px] text-ink-muted">{subtitle}</p>
            )}
          </div>
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </div>
      )}
      {children}
    </motion.div>
  )
}
