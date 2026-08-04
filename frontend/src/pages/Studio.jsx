import { useCallback, useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import PageShell from '../components/layout/PageShell'
import ArtifactPreview from '../components/studio/ArtifactPreview'
import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import Card, { CardHeader } from '../components/ui/Card'
import ConfirmDialog from '../components/ui/ConfirmDialog'
import EmptyState from '../components/ui/EmptyState'
import { Field, Textarea } from '../components/ui/Input'
import { ErrorBanner } from '../components/ui/ErrorState'
import Spinner from '../components/ui/Spinner'
import { useToast } from '../components/ui/Toast'
import { FileIcon, SparklesIcon, TrashIcon, WandIcon } from '../components/ui/Icons'
import cn from '../lib/cn'
import api, { errorMessage } from '../lib/api'
import { unwrapList } from '../lib/list'
import { formatDate } from '../lib/format'

const EXAMPLES = [
  'A resume for a backend developer internship: Python, Django, React, one internship and two projects',
  'A vegetarian diet chart for someone trying to gain muscle on a student budget',
  'A study timetable for GATE prep with college from 9 to 4 on weekdays',
  'A cover letter for a software engineering role at a product company',
  'A project report for my final-year AI goal-planning dashboard',
]

const STEPS = [
  'Working out what you need…',
  'Drafting the content…',
  'Laying it out…',
]

export default function Studio() {
  const toast = useToast()

  const [prompt, setPrompt] = useState('')
  const [kind, setKind] = useState('')
  const [kinds, setKinds] = useState([])

  const [artifacts, setArtifacts] = useState([])
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState('')
  const [confirmDelete, setConfirmDelete] = useState(null)
  const [deleting, setDeleting] = useState(false)

  const load = useCallback(async () => {
    try {
      const [listRes, kindRes] = await Promise.all([
        api.get('/artifacts/'),
        api.get('/artifacts/kinds/'),
      ])
      setArtifacts(unwrapList(listRes.data))
      setKinds(kindRes.data)
    } catch (err) {
      setError(errorMessage(err, 'Could not load your documents.'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  async function generate() {
    if (prompt.trim().length < 8) {
      setError('Tell us a bit more about what you need.')
      return
    }
    setError('')
    setGenerating(true)
    try {
      const { data } = await api.post('/artifacts/generate/', {
        prompt: prompt.trim(),
        ...(kind ? { kind } : {}),
      })
      setSelected(data)
      setArtifacts((current) => [data, ...current])
      toast.success(`${data.kind_label} ready.`)
    } catch (err) {
      setError(errorMessage(err, 'Could not build that document right now.'))
    } finally {
      setGenerating(false)
    }
  }

  async function open(row) {
    if (selected?.id === row.id) return
    setSelected(null)
    try {
      const { data } = await api.get(`/artifacts/${row.id}/`)
      setSelected(data)
    } catch (err) {
      toast.error(errorMessage(err, 'Could not open that document.'))
    }
  }

  async function remove() {
    setDeleting(true)
    try {
      await api.delete(`/artifacts/${confirmDelete.id}/`)
      setArtifacts((current) => current.filter((a) => a.id !== confirmDelete.id))
      if (selected?.id === confirmDelete.id) setSelected(null)
      setConfirmDelete(null)
    } catch (err) {
      toast.error(errorMessage(err, 'Could not delete that document.'))
    } finally {
      setDeleting(false)
    }
  }

  return (
    <PageShell
      title="Studio"
      subtitle="Describe what you need. We'll work out what it is and build it."
    >
      <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.85fr)]">
        {/* --- composer + history --- */}
        <div className="space-y-3">
          <Card className="p-5">
            <div className="space-y-4">
              {error && <ErrorBanner message={error} onDismiss={() => setError('')} />}

              <Field
                label="What do you need?"
                htmlFor="studio-prompt"
                hint="Include the details that matter: role, constraints, timeframe."
              >
                <Textarea
                  id="studio-prompt"
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="e.g. A resume for a backend internship, Python and Django, one internship and two projects"
                  rows={5}
                  disabled={generating}
                />
              </Field>

              <div>
                <p className="mb-1.5 text-[12.5px] text-ink-muted">
                  Type is detected automatically. Override it if you like.
                </p>
                <div className="flex flex-wrap gap-1.5">
                  <button
                    type="button"
                    onClick={() => setKind('')}
                    disabled={generating}
                    className={cn(
                      'rounded-full border px-2.5 py-1 text-[12.5px] font-medium transition-colors',
                      kind === ''
                        ? 'border-brand-200 bg-brand-50 text-brand-700'
                        : 'border-line bg-surface text-ink-soft hover:border-line-strong',
                    )}
                  >
                    Auto
                  </button>
                  {kinds.map((option) => (
                    <button
                      key={option.kind}
                      type="button"
                      onClick={() => setKind(option.kind)}
                      disabled={generating}
                      className={cn(
                        'rounded-full border px-2.5 py-1 text-[12.5px] font-medium transition-colors',
                        kind === option.kind
                          ? 'border-brand-200 bg-brand-50 text-brand-700'
                          : 'border-line bg-surface text-ink-soft hover:border-line-strong',
                      )}
                    >
                      {option.label}
                      <span className="ml-1 text-[10.5px] uppercase opacity-60">
                        {option.export_format}
                      </span>
                    </button>
                  ))}
                </div>
              </div>

              <Button size="lg" onClick={generate} loading={generating} className="w-full justify-center">
                {!generating && <WandIcon size={16} />}
                {generating ? 'Building…' : 'Build it'}
              </Button>

              {generating && (
                <ul className="space-y-2 pt-1">
                  {STEPS.map((label, index) => (
                    <li
                      key={label}
                      className="flex animate-pulse items-center gap-2 text-[13px] text-ink-muted"
                      style={{ animationDelay: `${index * 450}ms` }}
                    >
                      <Spinner size={13} />
                      {label}
                    </li>
                  ))}
                </ul>
              )}

              {!generating && !selected && (
                <div className="border-t border-line pt-3">
                  <p className="mb-1.5 text-[12px] font-medium text-ink-muted">
                    Try one of these
                  </p>
                  <div className="space-y-1">
                    {EXAMPLES.map((example) => (
                      <button
                        key={example}
                        type="button"
                        onClick={() => setPrompt(example)}
                        className="block w-full rounded-lg px-2 py-1.5 text-left text-[12.5px] leading-snug text-ink-soft transition-colors hover:bg-surface-muted hover:text-ink"
                      >
                        {example}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </Card>

          <Card>
            <CardHeader
              title="Your documents"
              subtitle={artifacts.length ? `${artifacts.length} saved` : undefined}
            />
            {loading ? (
              <div className="grid place-items-center py-8 text-brand-600">
                <Spinner size={18} />
              </div>
            ) : artifacts.length === 0 ? (
              <EmptyState
                icon={FileIcon}
                title="Nothing built yet"
                message="Whatever you generate is saved here so you can come back to it."
                className="py-8"
              />
            ) : (
              <ul className="px-3 pb-3">
                <AnimatePresence initial={false}>
                  {artifacts.map((row) => (
                    <motion.li
                      key={row.id}
                      layout
                      initial={{ opacity: 0, y: 4 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, height: 0 }}
                      className={cn(
                        'group flex items-center gap-2.5 rounded-lg px-2 py-2 transition-colors',
                        selected?.id === row.id ? 'bg-brand-50' : 'hover:bg-surface-muted',
                      )}
                    >
                      <button
                        type="button"
                        onClick={() => open(row)}
                        className="flex min-w-0 flex-1 items-center gap-2.5 text-left"
                      >
                        <span className="grid h-7 w-7 shrink-0 place-items-center rounded-lg border border-line bg-surface text-ink-muted">
                          <FileIcon size={14} />
                        </span>
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-[13px] font-medium text-ink">
                            {row.title}
                          </span>
                          <span className="text-[11.5px] text-ink-muted">
                            {row.kind_label} · {formatDate(row.updated_at)}
                          </span>
                        </span>
                      </button>
                      <Badge>{row.export_format.toUpperCase()}</Badge>
                      <button
                        type="button"
                        onClick={() => setConfirmDelete(row)}
                        aria-label={`Delete ${row.title}`}
                        className="rounded-md p-1.5 text-ink-muted opacity-0 transition-all group-hover:opacity-100 hover:bg-danger-soft hover:text-danger"
                      >
                        <TrashIcon size={14} />
                      </button>
                    </motion.li>
                  ))}
                </AnimatePresence>
              </ul>
            )}
          </Card>
        </div>

        {/* --- preview --- */}
        <div>
          {selected ? (
            <motion.div
              key={selected.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.22 }}
            >
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <div className="min-w-0">
                  <h2 className="truncate text-[16px] font-semibold tracking-[-0.01em] text-ink">
                    {selected.title}
                  </h2>
                  <p className="mt-0.5 text-[12.5px] text-ink-muted">
                    {selected.kind_label}
                  </p>
                </div>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={async () => {
                    try {
                      const { data } = await api.post(
                        `/artifacts/${selected.id}/regenerate/`,
                      )
                      setSelected(data)
                      toast.success('Rebuilt.')
                    } catch (err) {
                      toast.error(errorMessage(err, 'Could not rebuild that.'))
                    }
                  }}
                >
                  <SparklesIcon size={15} />
                  Rebuild
                </Button>
              </div>
              <ArtifactPreview artifact={selected} />
            </motion.div>
          ) : (
            <Card className="h-full">
              <EmptyState
                icon={WandIcon}
                title="Your document appears here"
                message="Describe a résumé, diet chart, timetable, cover letter or project report. Text documents download as a PDF with selectable text; visual ones as a PNG."
                className="py-24"
              />
            </Card>
          )}
        </div>
      </div>

      <ConfirmDialog
        open={Boolean(confirmDelete)}
        onClose={() => !deleting && setConfirmDelete(null)}
        onConfirm={remove}
        loading={deleting}
        title="Delete this document?"
        message={`“${confirmDelete?.title}” will be permanently removed.`}
      />
    </PageShell>
  )
}
