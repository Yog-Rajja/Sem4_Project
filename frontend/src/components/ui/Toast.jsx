import { createContext, useCallback, useContext, useMemo, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { AlertIcon, CheckSquareIcon } from './Icons'

const ToastContext = createContext(null)

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used inside <ToastProvider>')
  return ctx
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])

  const dismiss = useCallback((id) => {
    setToasts((current) => current.filter((t) => t.id !== id))
  }, [])

  const push = useCallback(
    (message, tone = 'success') => {
      const id = crypto.randomUUID()
      setToasts((current) => [...current, { id, message, tone }])
      setTimeout(() => dismiss(id), 3800)
    },
    [dismiss],
  )

  const value = useMemo(
    () => ({
      success: (m) => push(m, 'success'),
      error: (m) => push(m, 'error'),
    }),
    [push],
  )

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed bottom-4 left-1/2 z-[60] flex w-full max-w-sm -translate-x-1/2 flex-col gap-2 px-4 sm:left-auto sm:right-4 sm:translate-x-0">
        <AnimatePresence initial={false}>
          {toasts.map((toast) => (
            <motion.div
              key={toast.id}
              layout
              initial={{ opacity: 0, y: 12, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 6, scale: 0.98 }}
              transition={{ type: 'spring', stiffness: 320, damping: 28 }}
              className="pointer-events-auto flex items-start gap-2.5 rounded-xl border border-line bg-surface px-3.5 py-3 shadow-pop"
            >
              <span
                className={
                  toast.tone === 'error'
                    ? 'mt-0.5 text-danger'
                    : 'mt-0.5 text-success'
                }
              >
                {toast.tone === 'error' ? (
                  <AlertIcon size={16} />
                ) : (
                  <CheckSquareIcon size={16} />
                )}
              </span>
              <p className="flex-1 text-[13px] leading-relaxed text-ink">{toast.message}</p>
              <button
                type="button"
                onClick={() => dismiss(toast.id)}
                className="text-[12px] font-medium text-ink-muted hover:text-ink"
              >
                Close
              </button>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  )
}
