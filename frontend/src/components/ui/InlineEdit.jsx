import { useEffect, useRef, useState } from 'react'
import cn from '../../lib/cn'

/**
 * Click-to-edit text. Commits on blur or Enter, reverts on Escape.
 * Empty values are rejected so a stray click can't blank a title.
 */
export default function InlineEdit({
  value,
  onCommit,
  placeholder = 'Untitled',
  className,
  inputClassName,
  as: Tag = 'span',
  ariaLabel,
  disabled = false,
}) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(value)
  const inputRef = useRef(null)

  useEffect(() => {
    if (!editing) setDraft(value)
  }, [value, editing])

  useEffect(() => {
    if (editing) inputRef.current?.select()
  }, [editing])

  function commit() {
    setEditing(false)
    const next = draft.trim()
    if (!next || next === value) {
      setDraft(value)
      return
    }
    onCommit(next)
  }

  if (editing) {
    return (
      <input
        ref={inputRef}
        value={draft}
        aria-label={ariaLabel}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === 'Enter') {
            e.preventDefault()
            commit()
          }
          if (e.key === 'Escape') {
            setDraft(value)
            setEditing(false)
          }
        }}
        className={cn(
          'w-full rounded-md border border-brand-500 bg-surface px-1.5 py-0.5',
          'outline-none ring-3 ring-brand-500/15',
          inputClassName,
        )}
      />
    )
  }

  return (
    <Tag
      role={disabled ? undefined : 'button'}
      tabIndex={disabled ? undefined : 0}
      aria-label={ariaLabel}
      onClick={() => !disabled && setEditing(true)}
      onKeyDown={(e) => {
        if (!disabled && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault()
          setEditing(true)
        }
      }}
      className={cn(
        'block truncate rounded-md px-1.5 py-0.5 -mx-1.5',
        !disabled && 'cursor-text hover:bg-surface-muted',
        !value && 'text-ink-muted',
        className,
      )}
      title={disabled ? undefined : 'Click to edit'}
    >
      {value || placeholder}
    </Tag>
  )
}
