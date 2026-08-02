import { useEffect } from 'react'
import { createPortal } from 'react-dom'
import { AnimatePresence, motion } from 'framer-motion'
import cn from '../../lib/cn'
import { XIcon } from './Icons'

const SIZES = {
  sm: 'max-w-md',
  md: 'max-w-lg',
  lg: 'max-w-2xl',
  xl: 'max-w-4xl',
}

export default function Modal({
  open,
  onClose,
  title,
  description,
  size = 'md',
  footer,
  children,
}) {
  // Close on Escape and lock body scroll while the dialog is up.
  useEffect(() => {
    if (!open) return
    const onKey = (e) => e.key === 'Escape' && onClose?.()
    document.addEventListener('keydown', onKey)
    const previous = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = previous
    }
  }, [open, onClose])

  return createPortal(
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50 flex items-end justify-center p-0 sm:items-center sm:p-4">
          <motion.div
            className="absolute inset-0 bg-ink/25 backdrop-blur-[2px]"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            onClick={onClose}
          />
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-label={title}
            className={cn(
              'relative w-full overflow-hidden rounded-t-2xl bg-surface shadow-pop sm:rounded-2xl',
              SIZES[size],
            )}
            initial={{ opacity: 0, y: 16, scale: 0.985 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.99 }}
            transition={{ type: 'spring', stiffness: 300, damping: 28 }}
          >
            {(title || onClose) && (
              <div className="flex items-start justify-between gap-4 border-b border-line px-5 py-4">
                <div className="min-w-0">
                  {title && (
                    <h2 className="text-[15px] font-semibold tracking-[-0.01em] text-ink">
                      {title}
                    </h2>
                  )}
                  {description && (
                    <p className="mt-1 text-[13px] text-ink-muted">{description}</p>
                  )}
                </div>
                <button
                  type="button"
                  onClick={onClose}
                  aria-label="Close dialog"
                  className="-mr-1 -mt-1 rounded-lg p-1.5 text-ink-muted transition-colors hover:bg-surface-muted hover:text-ink"
                >
                  <XIcon size={17} />
                </button>
              </div>
            )}

            <div className="max-h-[70vh] overflow-y-auto px-5 py-4 scrollbar-thin">
              {children}
            </div>

            {footer && (
              <div className="flex justify-end gap-2 border-t border-line bg-surface-muted px-5 py-3.5">
                {footer}
              </div>
            )}
          </motion.div>
        </div>
      )}
    </AnimatePresence>,
    document.body,
  )
}
