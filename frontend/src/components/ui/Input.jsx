import { forwardRef } from 'react'
import cn from '../../lib/cn'

const base =
  'w-full rounded-lg border bg-surface px-3 text-sm text-ink placeholder:text-ink-muted ' +
  'transition-colors duration-150 outline-none focus:border-brand-500 ' +
  'focus:ring-3 focus:ring-brand-500/15 disabled:bg-surface-muted disabled:text-ink-muted'

export const Input = forwardRef(function Input({ className, invalid, ...rest }, ref) {
  return (
    <input
      ref={ref}
      aria-invalid={invalid || undefined}
      className={cn(base, 'h-9.5', invalid ? 'border-danger' : 'border-line', className)}
      {...rest}
    />
  )
})

export const Textarea = forwardRef(function Textarea(
  { className, invalid, rows = 4, ...rest },
  ref,
) {
  return (
    <textarea
      ref={ref}
      rows={rows}
      aria-invalid={invalid || undefined}
      className={cn(
        base,
        'py-2.5 resize-y leading-relaxed',
        invalid ? 'border-danger' : 'border-line',
        className,
      )}
      {...rest}
    />
  )
})

export const Select = forwardRef(function Select({ className, children, ...rest }, ref) {
  return (
    <select
      ref={ref}
      className={cn(base, 'h-9.5 border-line cursor-pointer pr-8', className)}
      {...rest}
    >
      {children}
    </select>
  )
})

/** Label + control + error message, so forms line up consistently. */
export function Field({ label, error, hint, htmlFor, children, className }) {
  return (
    <div className={cn('space-y-1.5', className)}>
      {label && (
        <label htmlFor={htmlFor} className="block text-[13px] font-medium text-ink-soft">
          {label}
        </label>
      )}
      {children}
      {error ? (
        <p className="text-[12.5px] text-danger">{error}</p>
      ) : hint ? (
        <p className="text-[12.5px] text-ink-muted">{hint}</p>
      ) : null}
    </div>
  )
}
