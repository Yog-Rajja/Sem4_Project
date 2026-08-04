import {
  differenceInCalendarDays,
  format,
  isValid,
  parseISO,
} from 'date-fns'

export function toDate(value) {
  if (!value) return null
  const date = typeof value === 'string' ? parseISO(value) : value
  return isValid(date) ? date : null
}

/** "12 Mar 2026" — or a fallback when there is no date. */
export function formatDate(value, fallback = 'No date') {
  const date = toDate(value)
  return date ? format(date, 'd MMM yyyy') : fallback
}

export function formatShortDate(value, fallback = '-') {
  const date = toDate(value)
  return date ? format(date, 'd MMM') : fallback
}

export function formatDayHeading(value) {
  const date = toDate(value)
  if (!date) return 'No date'
  const days = differenceInCalendarDays(date, new Date())
  if (days === 0) return 'Today'
  if (days === 1) return 'Tomorrow'
  if (days === -1) return 'Yesterday'
  return format(date, 'EEEE, d MMM')
}

/** Human phrasing for how a due date sits relative to today. */
export function dueLabel(value) {
  const date = toDate(value)
  if (!date) return { text: 'No due date', tone: 'neutral', days: null }

  const days = differenceInCalendarDays(date, new Date())
  if (days < 0) {
    const n = Math.abs(days)
    return { text: n === 1 ? '1 day overdue' : `${n} days overdue`, tone: 'danger', days }
  }
  if (days === 0) return { text: 'Due today', tone: 'warning', days }
  if (days === 1) return { text: 'Due tomorrow', tone: 'warning', days }
  if (days <= 7) return { text: `Due in ${days} days`, tone: 'neutral', days }
  return { text: formatDate(value), tone: 'neutral', days }
}

/** Today in YYYY-MM-DD, for date inputs. */
export function todayISO() {
  return format(new Date(), 'yyyy-MM-dd')
}

export function formatBytes(bytes) {
  if (!bytes) return '0 KB'
  const units = ['B', 'KB', 'MB', 'GB']
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
  const size = bytes / 1024 ** i
  return `${size >= 10 || i === 0 ? Math.round(size) : size.toFixed(1)} ${units[i]}`
}
