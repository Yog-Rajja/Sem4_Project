import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import Card, { CardHeader } from '../ui/Card'
import Badge from '../ui/Badge'
import Button from '../ui/Button'
import ConfirmDialog from '../ui/ConfirmDialog'
import EmptyState from '../ui/EmptyState'
import Spinner from '../ui/Spinner'
import { useToast } from '../ui/Toast'
import {
  DownloadIcon,
  FileIcon,
  SparklesIcon,
  TargetIcon,
  TrashIcon,
  UploadIcon,
} from '../ui/Icons'
import cn from '../../lib/cn'
import api, { errorMessage } from '../../lib/api'
import { unwrapList } from '../../lib/list'
import { formatBytes, formatDate } from '../../lib/format'

const MAX_BYTES = 10 * 1024 * 1024

/**
 * Document vault with the intelligence layer on top: upload, read, and turn
 * what was read into a plan.
 *
 * Analysis is explicit rather than automatic on upload — it costs an API call,
 * so the user decides when a file is worth reading.
 */
export default function DocumentVault({ goalId }) {
  const toast = useToast()
  const navigate = useNavigate()
  const inputRef = useRef(null)

  const [documents, setDocuments] = useState([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [busyId, setBusyId] = useState(null)
  const [expandedId, setExpandedId] = useState(null)
  const [confirmDoc, setConfirmDoc] = useState(null)
  const [deleting, setDeleting] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await api.get('/documents/', { params: { goal: goalId } })
      setDocuments(unwrapList(data))
    } catch {
      setDocuments([])
    } finally {
      setLoading(false)
    }
  }, [goalId])

  useEffect(() => {
    load()
  }, [load])

  async function upload(file) {
    if (!file) return
    if (file.size > MAX_BYTES) {
      toast.error('Files must be 10 MB or smaller.')
      return
    }

    const form = new FormData()
    form.append('goal', goalId)
    form.append('file', file)

    setUploading(true)
    try {
      const { data } = await api.post('/documents/', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setDocuments((current) => [data, ...current])
      toast.success(`Uploaded ${data.original_name}.`)
    } catch (err) {
      toast.error(errorMessage(err, 'Could not upload that file.'))
    } finally {
      setUploading(false)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  async function analyse(doc) {
    setBusyId(doc.id)
    try {
      const { data } = await api.post(`/documents/${doc.id}/analyse/`)
      setDocuments((current) => current.map((d) => (d.id === doc.id ? data : d)))
      setExpandedId(doc.id)
      toast.success(`Read ${data.doc_type || 'the document'}.`)
    } catch (err) {
      toast.error(errorMessage(err, 'Could not read that document.'))
    } finally {
      setBusyId(null)
    }
  }

  async function toGoal(doc) {
    setBusyId(doc.id)
    try {
      const { data } = await api.post(`/documents/${doc.id}/to-goal/`, {})
      // Hand the preview to the New Goal screen, which already knows how to
      // let the user edit and accept a generated roadmap.
      navigate('/goals/new', { state: { preview: data } })
    } catch (err) {
      toast.error(errorMessage(err, 'Could not build a roadmap from that.'))
    } finally {
      setBusyId(null)
    }
  }

  async function confirmDelete() {
    setDeleting(true)
    try {
      await api.delete(`/documents/${confirmDoc.id}/`)
      setDocuments((current) => current.filter((d) => d.id !== confirmDoc.id))
      setConfirmDoc(null)
    } catch (err) {
      toast.error(errorMessage(err, 'Could not delete that file.'))
    } finally {
      setDeleting(false)
    }
  }

  return (
    <Card className="mt-3">
      <CardHeader
        title="Documents"
        subtitle="Upload a syllabus, brief or notes — we can read it and plan from it"
        action={
          <>
            <input
              ref={inputRef}
              type="file"
              className="hidden"
              accept=".pdf,.png,.jpg,.jpeg,.webp,.txt,.md,.csv"
              onChange={(e) => upload(e.target.files?.[0])}
            />
            <Button
              variant="secondary"
              size="sm"
              loading={uploading}
              onClick={() => inputRef.current?.click()}
            >
              {!uploading && <UploadIcon size={15} />}
              Upload
            </Button>
          </>
        }
      />

      {loading ? (
        <div className="grid place-items-center py-8 text-brand-600">
          <Spinner size={18} />
        </div>
      ) : documents.length === 0 ? (
        <EmptyState
          icon={FileIcon}
          title="No documents yet"
          message="Attach a syllabus, job description or reference PDF. We can read it and turn it into a plan."
          className="py-8"
        />
      ) : (
        <ul className="px-3 pb-3">
          <AnimatePresence initial={false}>
            {documents.map((doc) => {
              const expanded = expandedId === doc.id
              const busy = busyId === doc.id

              return (
                <motion.li
                  key={doc.id}
                  layout
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.16 }}
                  className="rounded-lg transition-colors hover:bg-surface-muted"
                >
                  <div className="group flex items-center gap-3 px-2 py-2">
                    <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg border border-line bg-surface text-ink-muted">
                      <FileIcon size={15} />
                    </span>

                    <button
                      type="button"
                      onClick={() =>
                        doc.is_analysed ? setExpandedId(expanded ? null : doc.id) : analyse(doc)
                      }
                      className="min-w-0 flex-1 text-left"
                    >
                      <p className="truncate text-[13.5px] font-medium text-ink">
                        {doc.original_name}
                      </p>
                      <p className="text-[12px] text-ink-muted">
                        {formatBytes(doc.size_bytes)} · {formatDate(doc.uploaded_at)}
                        {doc.doc_type ? ` · ${doc.doc_type}` : ''}
                      </p>
                    </button>

                    {doc.is_analysed ? (
                      <Badge tone="brand">Read</Badge>
                    ) : (
                      <Button
                        size="sm"
                        variant="secondary"
                        loading={busy}
                        onClick={() => analyse(doc)}
                      >
                        {!busy && <SparklesIcon size={14} />}
                        Read it
                      </Button>
                    )}

                    <a
                      href={doc.file_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      download
                      aria-label={`Download ${doc.original_name}`}
                      className="rounded-md p-1.5 text-ink-muted opacity-0 transition-all group-hover:opacity-100 hover:bg-brand-50 hover:text-brand-600"
                    >
                      <DownloadIcon size={15} />
                    </a>
                    <button
                      type="button"
                      onClick={() => setConfirmDoc(doc)}
                      aria-label={`Delete ${doc.original_name}`}
                      className="rounded-md p-1.5 text-ink-muted opacity-0 transition-all group-hover:opacity-100 hover:bg-danger-soft hover:text-danger"
                    >
                      <TrashIcon size={15} />
                    </button>
                  </div>

                  <AnimatePresence initial={false}>
                    {expanded && doc.is_analysed && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="overflow-hidden"
                      >
                        <div className="mx-2 mb-2 rounded-lg border border-line bg-surface p-3.5">
                          <p className="text-[13px] leading-relaxed text-ink-soft">
                            {doc.summary}
                          </p>

                          {doc.key_points?.length > 0 && (
                            <div className="mt-3">
                              <p className="mb-1.5 text-[11.5px] font-semibold tracking-wide text-ink-muted uppercase">
                                Key points
                              </p>
                              <ul className="space-y-1">
                                {doc.key_points.map((point, index) => (
                                  <li
                                    key={index}
                                    className="flex gap-2 text-[12.5px] leading-relaxed text-ink-soft"
                                  >
                                    <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-line-strong" />
                                    {point}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {doc.suggested_actions?.length > 0 && (
                            <div className="mt-3">
                              <p className="mb-1.5 text-[11.5px] font-semibold tracking-wide text-ink-muted uppercase">
                                What you could do
                              </p>
                              <ul className="space-y-1">
                                {doc.suggested_actions.map((action, index) => (
                                  <li
                                    key={index}
                                    className="flex gap-2 text-[12.5px] leading-relaxed text-brand-700"
                                  >
                                    <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-brand-400" />
                                    {action}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}

                          <div className={cn('mt-3.5 flex flex-wrap gap-2')}>
                            <Button size="sm" loading={busy} onClick={() => toGoal(doc)}>
                              {!busy && <TargetIcon size={14} />}
                              Turn into a roadmap
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => analyse(doc)}
                              disabled={busy}
                            >
                              Read again
                            </Button>
                          </div>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.li>
              )
            })}
          </AnimatePresence>
        </ul>
      )}

      <ConfirmDialog
        open={Boolean(confirmDoc)}
        onClose={() => !deleting && setConfirmDoc(null)}
        onConfirm={confirmDelete}
        loading={deleting}
        title="Delete this document?"
        message={`“${confirmDoc?.original_name}” will be permanently removed.`}
      />
    </Card>
  )
}
