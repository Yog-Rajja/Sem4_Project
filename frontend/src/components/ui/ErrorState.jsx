import Button from './Button'
import { AlertIcon } from './Icons'

/** Inline error with a retry affordance. Used wherever a fetch can fail. */
export default function ErrorState({ message, onRetry, retryLabel = 'Try again' }) {
  return (
    <div className="flex flex-col items-center px-6 py-10 text-center">
      <div className="mb-3.5 grid h-11 w-11 place-items-center rounded-xl border border-danger/20 bg-danger-soft text-danger">
        <AlertIcon size={20} />
      </div>
      <p className="text-sm font-semibold text-ink">Something went wrong</p>
      <p className="mt-1.5 max-w-md text-[13px] leading-relaxed text-ink-muted">
        {message}
      </p>
      {onRetry && (
        <Button variant="secondary" size="sm" className="mt-4" onClick={onRetry}>
          {retryLabel}
        </Button>
      )}
    </div>
  )
}

/** Compact banner variant for errors that sit above still-usable content. */
export function ErrorBanner({ message, onDismiss }) {
  if (!message) return null
  return (
    <div className="flex items-start gap-2.5 rounded-lg border border-danger/20 bg-danger-soft px-3.5 py-2.5">
      <AlertIcon size={16} className="mt-0.5 shrink-0 text-danger" />
      <p className="flex-1 text-[13px] leading-relaxed text-danger">{message}</p>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          className="text-[12px] font-medium text-danger/70 hover:text-danger"
        >
          Dismiss
        </button>
      )}
    </div>
  )
}
