import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import PageShell from '../components/layout/PageShell'
import RoadmapEditor from '../components/goals/RoadmapEditor'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import { Field, Input, Textarea } from '../components/ui/Input'
import { ErrorBanner } from '../components/ui/ErrorState'
import Spinner from '../components/ui/Spinner'
import { useToast } from '../components/ui/Toast'
import { SparklesIcon } from '../components/ui/Icons'
import api, { errorMessage } from '../lib/api'
import { todayISO } from '../lib/format'

const EXAMPLES = [
  'Crack GATE in 8 months',
  'Get a software engineering job',
  'Learn React and build a portfolio',
  'Save 2 lakh rupees for a bike in 10 months',
]

const GENERATING_STEPS = [
  'Reading your goal…',
  'Breaking it into milestones…',
  'Setting realistic dates…',
]

/** Normalise a generated roadmap into the editor's shape. */
function normalise(milestones) {
  return (milestones || []).map((m) => ({
    title: m.title || '',
    target_date: m.target_date || '',
    search_query: m.search_query || '',
    tasks: (m.tasks || []).map((t) => ({
      title: t.title || '',
      due_date: t.due_date || '',
    })),
  }))
}

export default function NewGoal() {
  const navigate = useNavigate()
  const location = useLocation()
  const toast = useToast()

  const [step, setStep] = useState(
    () => (location.state?.preview ? 'preview' : 'input'), // input | preview
  )
  const [generating, setGenerating] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  // A roadmap generated from an uploaded document arrives through router
  // state, so it lands in the same editable preview as an AI-generated one.
  const handoff = location.state?.preview

  const [text, setText] = useState(handoff?.raw_input_text || '')
  const [targetDate, setTargetDate] = useState(handoff?.target_date || '')
  const [title, setTitle] = useState(handoff?.title || '')
  const [milestones, setMilestones] = useState(() => normalise(handoff?.milestones))
  const [sourceDocument] = useState(handoff?.source_document || '')

  async function generate() {
    if (text.trim().length < 5) {
      setError('Describe your goal in a few more words so we can plan it properly.')
      return
    }
    setError('')
    setGenerating(true)
    try {
      const { data } = await api.post('/goals/generate/', {
        text: text.trim(),
        ...(targetDate ? { target_date: targetDate } : {}),
      })
      setTitle(data.title || text.trim())
      setMilestones(normalise(data.milestones))
      setStep('preview')
    } catch (err) {
      setError(errorMessage(err, 'We could not generate a roadmap right now.'))
    } finally {
      setGenerating(false)
    }
  }

  /** Escape hatch when generation keeps failing — start an empty roadmap. */
  function buildManually() {
    setError('')
    setTitle(text.trim() || 'My goal')
    setMilestones([
      { title: '', target_date: targetDate || '', search_query: '', tasks: [] },
    ])
    setStep('preview')
  }

  async function save() {
    // Drop anything the user left blank rather than rejecting the whole save.
    const cleaned = milestones
      .filter((m) => m.title.trim())
      .map((m, index) => ({
        title: m.title.trim(),
        target_date: m.target_date || null,
        search_query: (m.search_query || '').trim() || m.title.trim(),
        order: index,
        tasks: m.tasks
          .filter((t) => t.title.trim())
          .map((t, tIndex) => ({
            title: t.title.trim(),
            due_date: t.due_date || null,
            order: tIndex,
          })),
      }))

    if (!title.trim()) {
      setError('Give your goal a title before saving.')
      return
    }
    if (!cleaned.length) {
      setError('Add at least one milestone before saving.')
      return
    }

    setError('')
    setSaving(true)
    try {
      const { data } = await api.post('/goals/', {
        title: title.trim(),
        raw_input_text: text.trim(),
        target_date: targetDate || null,
        milestones: cleaned,
      })
      toast.success('Goal saved. Your roadmap is ready.')
      navigate(`/goals/${data.id}`, { replace: true })
    } catch (err) {
      setError(errorMessage(err, 'Could not save this goal.'))
    } finally {
      setSaving(false)
    }
  }

  const taskCount = milestones.reduce(
    (sum, m) => sum + m.tasks.filter((t) => t.title.trim()).length,
    0,
  )

  return (
    <PageShell
      title="New goal"
      subtitle={
        step === 'input'
          ? 'Describe what you want to achieve. We will turn it into a dated plan.'
          : 'Edit anything that does not fit, then save your roadmap.'
      }
    >
      {/* Deliberately not wrapped in AnimatePresence: these panes have no exit
          animation, and `mode="wait"` around a subtree that owns its own
          presence children deadlocks the swap. Each pane animates in on mount. */}
      <>
        {step === 'input' ? (
          <motion.div
            key="input"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2 }}
            className="mx-auto max-w-2xl"
          >
            <Card className="p-5 sm:p-6">
              <div className="space-y-4">
                {error && <ErrorBanner message={error} onDismiss={() => setError('')} />}

                <Field
                  label="What do you want to achieve?"
                  htmlFor="goal-text"
                  hint="Plain English is fine. Include a rough timeframe if you have one."
                >
                  <Textarea
                    id="goal-text"
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    placeholder="e.g. Crack GATE in 8 months while finishing my final year"
                    rows={4}
                    autoFocus
                    disabled={generating}
                  />
                </Field>

                <div className="flex flex-wrap gap-1.5">
                  {EXAMPLES.map((example) => (
                    <button
                      key={example}
                      type="button"
                      disabled={generating}
                      onClick={() => setText(example)}
                      className="rounded-full border border-line bg-surface px-2.5 py-1 text-[12.5px] text-ink-soft transition-colors hover:border-brand-200 hover:bg-brand-50 hover:text-brand-700 disabled:opacity-50"
                    >
                      {example}
                    </button>
                  ))}
                </div>

                <Field
                  label="Target date"
                  htmlFor="goal-date"
                  hint="Optional. We will pick a sensible horizon if you leave this empty."
                  className="max-w-56"
                >
                  <Input
                    id="goal-date"
                    type="date"
                    min={todayISO()}
                    value={targetDate}
                    onChange={(e) => setTargetDate(e.target.value)}
                    disabled={generating}
                  />
                </Field>

                <div className="flex flex-wrap items-center gap-2 pt-1">
                  <Button size="lg" onClick={generate} loading={generating}>
                    {!generating && <SparklesIcon size={16} />}
                    {generating ? 'Generating…' : 'Generate roadmap'}
                  </Button>
                  <Button variant="ghost" onClick={buildManually} disabled={generating}>
                    Build it manually
                  </Button>
                </div>

                {/* Plain conditional with a CSS pulse, deliberately not a
                    nested AnimatePresence: an exiting child with an infinite
                    animation deadlocks the `mode="wait"` step transition. */}
                {generating && (
                  <ul className="space-y-2 pt-1">
                    {GENERATING_STEPS.map((label, i) => (
                      <li
                        key={label}
                        className="flex animate-pulse items-center gap-2 text-[13px] text-ink-muted"
                        style={{ animationDelay: `${i * 450}ms` }}
                      >
                        <Spinner size={13} />
                        {label}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </Card>
          </motion.div>
        ) : (
          <motion.div
            key="preview"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2 }}
            className="space-y-4"
          >
            {error && <ErrorBanner message={error} onDismiss={() => setError('')} />}

            <Card className="p-5">
              <Field label="Goal title" htmlFor="goal-title">
                <Input
                  id="goal-title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Name this goal"
                  className="text-[15px] font-medium"
                />
              </Field>
              <p className="mt-3 text-[13px] text-ink-muted">
                {milestones.length} milestone{milestones.length === 1 ? '' : 's'} ·{' '}
                {taskCount} task{taskCount === 1 ? '' : 's'}
                {sourceDocument && (
                  <> · built from {sourceDocument}</>
                )}
              </p>
            </Card>

            <RoadmapEditor milestones={milestones} onChange={setMilestones} />

            <div className="sticky bottom-0 -mx-4 flex flex-wrap items-center gap-2 border-t border-line bg-canvas/90 px-4 py-3 backdrop-blur-md sm:-mx-6 sm:px-6">
              <Button size="lg" onClick={save} loading={saving}>
                Save goal
              </Button>
              <Button
                variant="secondary"
                onClick={generate}
                loading={generating}
                disabled={saving}
              >
                <SparklesIcon size={15} />
                Regenerate
              </Button>
              <Button
                variant="ghost"
                onClick={() => setStep('input')}
                disabled={saving || generating}
              >
                Back
              </Button>
            </div>
          </motion.div>
        )}
      </>
    </PageShell>
  )
}
