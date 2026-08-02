import { AnimatePresence, motion } from 'framer-motion'
import Button from '../ui/Button'
import { Input } from '../ui/Input'
import {
  ArrowDownIcon,
  ArrowUpIcon,
  PlusIcon,
  SearchIcon,
  TrashIcon,
} from '../ui/Icons'

/**
 * Fully controlled editor for a roadmap that hasn't been saved yet.
 *
 * Everything here is local state owned by the parent — nothing hits the API
 * until the user accepts the plan, so they can freely rewrite what the AI
 * produced (or throw milestones away) before committing to it.
 */
export default function RoadmapEditor({ milestones, onChange }) {
  const replaceAt = (index, next) =>
    onChange(milestones.map((m, i) => (i === index ? next : m)))

  const updateMilestone = (index, patch) =>
    replaceAt(index, { ...milestones[index], ...patch })

  const removeMilestone = (index) =>
    onChange(milestones.filter((_, i) => i !== index))

  const moveMilestone = (index, direction) => {
    const target = index + direction
    if (target < 0 || target >= milestones.length) return
    const next = [...milestones]
    ;[next[index], next[target]] = [next[target], next[index]]
    onChange(next)
  }

  const addMilestone = () =>
    onChange([
      ...milestones,
      { title: '', target_date: '', search_query: '', tasks: [] },
    ])

  const updateTask = (mIndex, tIndex, patch) => {
    const milestone = milestones[mIndex]
    updateMilestone(mIndex, {
      tasks: milestone.tasks.map((t, i) => (i === tIndex ? { ...t, ...patch } : t)),
    })
  }

  const removeTask = (mIndex, tIndex) =>
    updateMilestone(mIndex, {
      tasks: milestones[mIndex].tasks.filter((_, i) => i !== tIndex),
    })

  const addTask = (mIndex) =>
    updateMilestone(mIndex, {
      tasks: [...milestones[mIndex].tasks, { title: '', due_date: '' }],
    })

  return (
    <div className="space-y-3">
      <AnimatePresence initial={false}>
        {milestones.map((milestone, mIndex) => (
          <motion.div
            key={mIndex}
            layout
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, height: 0, marginBottom: 0 }}
            transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}
            className="overflow-hidden rounded-card border border-line bg-surface shadow-card"
          >
            {/* Milestone header */}
            <div className="flex items-start gap-3 border-b border-line bg-surface-muted px-4 py-3">
              <span className="mt-1.5 grid h-6 w-6 shrink-0 place-items-center rounded-md bg-brand-100 text-[12px] font-semibold text-brand-700">
                {mIndex + 1}
              </span>

              <div className="min-w-0 flex-1 space-y-2">
                <Input
                  value={milestone.title}
                  onChange={(e) => updateMilestone(mIndex, { title: e.target.value })}
                  placeholder="Milestone title"
                  aria-label={`Milestone ${mIndex + 1} title`}
                  className="font-medium"
                />
                <div className="flex flex-col gap-2 sm:flex-row">
                  <label className="flex flex-1 items-center gap-2 text-[12.5px] text-ink-muted">
                    <span className="shrink-0">Target</span>
                    <Input
                      type="date"
                      value={milestone.target_date || ''}
                      onChange={(e) =>
                        updateMilestone(mIndex, { target_date: e.target.value })
                      }
                      aria-label={`Milestone ${mIndex + 1} target date`}
                    />
                  </label>
                  <label className="flex flex-[1.4] items-center gap-2 text-[12.5px] text-ink-muted">
                    <SearchIcon size={14} className="shrink-0" />
                    <Input
                      value={milestone.search_query || ''}
                      onChange={(e) =>
                        updateMilestone(mIndex, { search_query: e.target.value })
                      }
                      placeholder="Topic to find resources for"
                      aria-label={`Milestone ${mIndex + 1} resource topic`}
                    />
                  </label>
                </div>
              </div>

              <div className="flex shrink-0 items-center gap-0.5">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => moveMilestone(mIndex, -1)}
                  disabled={mIndex === 0}
                  aria-label="Move milestone up"
                >
                  <ArrowUpIcon size={15} />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => moveMilestone(mIndex, 1)}
                  disabled={mIndex === milestones.length - 1}
                  aria-label="Move milestone down"
                >
                  <ArrowDownIcon size={15} />
                </Button>
                <Button
                  variant="dangerGhost"
                  size="icon"
                  onClick={() => removeMilestone(mIndex)}
                  aria-label="Delete milestone"
                >
                  <TrashIcon size={15} />
                </Button>
              </div>
            </div>

            {/* Tasks */}
            <div className="space-y-1.5 px-4 py-3">
              <AnimatePresence initial={false}>
                {milestone.tasks.map((task, tIndex) => (
                  <motion.div
                    key={tIndex}
                    layout
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.15 }}
                    className="flex items-center gap-2"
                  >
                    <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-line-strong" />
                    <Input
                      value={task.title}
                      onChange={(e) =>
                        updateTask(mIndex, tIndex, { title: e.target.value })
                      }
                      placeholder="Task"
                      aria-label="Task title"
                      className="flex-1"
                    />
                    <Input
                      type="date"
                      value={task.due_date || ''}
                      onChange={(e) =>
                        updateTask(mIndex, tIndex, { due_date: e.target.value })
                      }
                      aria-label="Task due date"
                      className="w-36 shrink-0"
                    />
                    <Button
                      variant="dangerGhost"
                      size="icon"
                      onClick={() => removeTask(mIndex, tIndex)}
                      aria-label="Delete task"
                    >
                      <TrashIcon size={14} />
                    </Button>
                  </motion.div>
                ))}
              </AnimatePresence>

              <Button
                variant="ghost"
                size="sm"
                className="mt-1"
                onClick={() => addTask(mIndex)}
              >
                <PlusIcon size={14} />
                Add task
              </Button>
            </div>
          </motion.div>
        ))}
      </AnimatePresence>

      <Button variant="secondary" className="w-full justify-center" onClick={addMilestone}>
        <PlusIcon size={15} />
        Add milestone
      </Button>
    </div>
  )
}
