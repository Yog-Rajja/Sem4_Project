import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useNavigate } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import cn from '../../lib/cn'
import api from '../../lib/api'
import { unwrapList } from '../../lib/list'
import { useTheme } from '../../context/ThemeContext'
import {
  CalendarIcon,
  ChartIcon,
  CheckSquareIcon,
  FileIcon,
  HomeIcon,
  MoonIcon,
  PlusIcon,
  SearchIcon,
  SunIcon,
  TargetIcon,
  TimerIcon,
  UsersIcon,
  WandIcon,
} from '../ui/Icons'

/** Rank a candidate against the query: prefix > word-start > substring. */
function score(text, query) {
  const haystack = text.toLowerCase()
  if (!query) return 0
  if (haystack.startsWith(query)) return 3
  if (haystack.includes(` ${query}`)) return 2
  return haystack.includes(query) ? 1 : -1
}

export default function CommandPalette({ open, onClose }) {
  const navigate = useNavigate()
  const { isDark, toggle } = useTheme()

  const [query, setQuery] = useState('')
  const [cursor, setCursor] = useState(0)
  const [goals, setGoals] = useState([])
  const [tasks, setTasks] = useState([])
  const listRef = useRef(null)

  // Content is fetched each time the palette opens, so results are never stale.
  useEffect(() => {
    if (!open) return
    setQuery('')
    setCursor(0)
    let cancelled = false
    Promise.all([
      api.get('/goals/'),
      api.get('/tasks/', { params: { status: 'pending' } }),
    ])
      .then(([goalRes, taskRes]) => {
        if (cancelled) return
        setGoals(unwrapList(goalRes.data))
        setTasks(unwrapList(taskRes.data))
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [open])

  const run = useCallback(
    (action) => {
      onClose()
      // Let the dialog close before navigating, so the exit animation plays.
      requestAnimationFrame(action)
    },
    [onClose],
  )

  const items = useMemo(() => {
    const q = query.trim().toLowerCase()

    const actions = [
      {
        id: 'new-goal',
        group: 'Actions',
        label: 'Create a new goal',
        hint: 'Describe it and let the AI plan it',
        icon: PlusIcon,
        run: () => navigate('/goals/new'),
      },
      {
        id: 'plan-day',
        group: 'Actions',
        label: 'Plan my day',
        hint: 'Pick today’s realistic workload',
        icon: WandIcon,
        run: () => navigate('/dashboard?plan=1'),
      },
      {
        id: 'focus',
        group: 'Actions',
        label: 'Start a focus session',
        hint: 'Pomodoro timer',
        icon: TimerIcon,
        run: () => navigate('/focus'),
      },
      {
        id: 'studio',
        group: 'Actions',
        label: 'Build a document',
        hint: 'Résumé, diet chart, timetable, cover letter',
        icon: FileIcon,
        run: () => navigate('/studio'),
      },
      {
        id: 'theme',
        group: 'Actions',
        label: isDark ? 'Switch to light mode' : 'Switch to dark mode',
        icon: isDark ? SunIcon : MoonIcon,
        run: toggle,
      },
    ]

    const pages = [
      { id: 'nav-dashboard', label: 'Dashboard', icon: HomeIcon, to: '/dashboard' },
      { id: 'nav-goals', label: 'Goals', icon: TargetIcon, to: '/goals' },
      { id: 'nav-tasks', label: 'Tasks', icon: CheckSquareIcon, to: '/tasks' },
      { id: 'nav-focus', label: 'Focus', icon: TimerIcon, to: '/focus' },
      { id: 'nav-studio', label: 'Studio', icon: WandIcon, to: '/studio' },
      { id: 'nav-circles', label: 'Circles', icon: UsersIcon, to: '/circles' },
      { id: 'nav-calendar', label: 'Calendar', icon: CalendarIcon, to: '/calendar' },
      { id: 'nav-analytics', label: 'Analytics', icon: ChartIcon, to: '/analytics' },
    ].map((page) => ({
      ...page,
      group: 'Go to',
      run: () => navigate(page.to),
    }))

    const goalItems = goals.map((goal) => ({
      id: `goal-${goal.id}`,
      group: 'Goals',
      label: goal.title,
      hint: `${goal.progress}% · ${goal.completed_tasks}/${goal.total_tasks} tasks`,
      icon: TargetIcon,
      run: () => navigate(`/goals/${goal.id}`),
    }))

    const taskItems = tasks.slice(0, 60).map((task) => ({
      id: `task-${task.id}`,
      group: 'Tasks',
      label: task.title,
      hint: task.goal_title,
      icon: CheckSquareIcon,
      run: () => navigate(`/goals/${task.goal_id}`),
    }))

    const all = [...actions, ...pages, ...goalItems, ...taskItems]
    if (!q) return all.filter((item) => item.group === 'Actions' || item.group === 'Go to')

    return all
      .map((item) => ({
        item,
        rank: Math.max(score(item.label, q), score(item.hint || '', q) - 1),
      }))
      .filter((entry) => entry.rank >= 0)
      .sort((a, b) => b.rank - a.rank)
      .slice(0, 24)
      .map((entry) => entry.item)
  }, [query, goals, tasks, navigate, isDark, toggle])

  useEffect(() => setCursor(0), [query])

  // Keep the highlighted row in view as the cursor moves.
  useEffect(() => {
    const node = listRef.current?.querySelector('[data-active="true"]')
    node?.scrollIntoView({ block: 'nearest' })
  }, [cursor, items])

  useEffect(() => {
    if (!open) return
    const onKey = (event) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        onClose()
      } else if (event.key === 'ArrowDown') {
        event.preventDefault()
        setCursor((c) => (items.length ? (c + 1) % items.length : 0))
      } else if (event.key === 'ArrowUp') {
        event.preventDefault()
        setCursor((c) => (items.length ? (c - 1 + items.length) % items.length : 0))
      } else if (event.key === 'Enter') {
        event.preventDefault()
        const item = items[cursor]
        if (item) run(item.run)
      }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, items, cursor, onClose, run])

  let lastGroup = null

  return createPortal(
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-[70] flex items-start justify-center p-4 pt-[12vh]">
          <motion.div
            className="absolute inset-0 bg-ink/30 backdrop-blur-[3px]"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.13 }}
            onClick={onClose}
          />
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-label="Command palette"
            className="relative w-full max-w-xl overflow-hidden rounded-2xl border border-line bg-surface shadow-pop"
            initial={{ opacity: 0, y: -8, scale: 0.985 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.99 }}
            transition={{ type: 'spring', stiffness: 380, damping: 30 }}
          >
            <div className="flex items-center gap-2.5 border-b border-line px-4">
              <SearchIcon size={17} className="shrink-0 text-ink-muted" />
              <input
                autoFocus
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search goals and tasks, or jump anywhere…"
                aria-label="Search commands"
                className="h-12 flex-1 bg-transparent text-[14px] text-ink outline-none placeholder:text-ink-muted"
              />
              <kbd className="hidden rounded border border-line bg-surface-muted px-1.5 py-0.5 text-[11px] text-ink-muted sm:block">
                Esc
              </kbd>
            </div>

            <div ref={listRef} className="max-h-[52vh] overflow-y-auto py-1.5 scrollbar-thin">
              {items.length === 0 ? (
                <p className="px-4 py-8 text-center text-[13px] text-ink-muted">
                  Nothing matches “{query}”.
                </p>
              ) : (
                items.map((item, index) => {
                  const showGroup = item.group !== lastGroup
                  lastGroup = item.group
                  const active = index === cursor
                  const Icon = item.icon

                  return (
                    <div key={item.id}>
                      {showGroup && (
                        <p className="px-4 pt-2.5 pb-1 text-[11px] font-semibold tracking-wide text-ink-muted uppercase">
                          {item.group}
                        </p>
                      )}
                      <button
                        type="button"
                        data-active={active}
                        onMouseMove={() => setCursor(index)}
                        onClick={() => run(item.run)}
                        className={cn(
                          'flex w-full items-center gap-3 px-4 py-2 text-left transition-colors',
                          active ? 'bg-brand-50' : 'hover:bg-surface-muted',
                        )}
                      >
                        <Icon
                          size={16}
                          className={active ? 'text-brand-600' : 'text-ink-muted'}
                        />
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-[13.5px] text-ink">
                            {item.label}
                          </span>
                          {item.hint && (
                            <span className="block truncate text-[12px] text-ink-muted">
                              {item.hint}
                            </span>
                          )}
                        </span>
                        {active && (
                          <kbd className="hidden rounded border border-line bg-surface px-1.5 py-0.5 text-[11px] text-ink-muted sm:block">
                            ↵
                          </kbd>
                        )}
                      </button>
                    </div>
                  )
                })
              )}
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>,
    document.body,
  )
}
