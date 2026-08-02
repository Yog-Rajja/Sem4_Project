import { useCallback, useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import Card, { CardHeader } from '../ui/Card'
import Button from '../ui/Button'
import ConfirmDialog from '../ui/ConfirmDialog'
import EmptyState from '../ui/EmptyState'
import Spinner from '../ui/Spinner'
import { useToast } from '../ui/Toast'
import { DownloadIcon, FileIcon, TrashIcon, UploadIcon } from '../ui/Icons'
import api, { errorMessage } from '../../lib/api'
import { unwrapList } from '../../lib/list'
import { formatBytes, formatDate } from '../../lib/format'

const MAX_BYTES = 10 * 1024 * 1024

/** Minimal document vault: upload a file against a goal, list it, download it.
    No folders, tags or preview — deliberately out of scope. */
export default function DocumentVault({ goalId }) {
  const toast = useToast()
  const inputRef = useRef(null)

  const [documents, setDocuments] = useState([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [confirmDoc, setConfirmDoc] = useState(null)
  const [deleting, setDeleting] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await api.get('/documents/', { params: { goal: goalId } })
      setDocuments(unwrapList(data))
    } catch {
      // A vault failure should never block the roadmap; stay quiet and empty.
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
        subtitle="Notes, syllabi and anything else worth keeping with this goal"
        action={
          <>
            <input
              ref={inputRef}
              type="file"
              className="hidden"
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
          message="Attach a syllabus, notes or a reference PDF so everything for this goal lives together."
          className="py-8"
        />
      ) : (
        <ul className="px-3 pb-3">
          <AnimatePresence initial={false}>
            {documents.map((doc) => (
              <motion.li
                key={doc.id}
                layout
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.16 }}
                className="group flex items-center gap-3 rounded-lg px-2 py-2 transition-colors hover:bg-surface-muted"
              >
                <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg border border-line bg-surface text-ink-muted">
                  <FileIcon size={15} />
                </span>

                <div className="min-w-0 flex-1">
                  <p className="truncate text-[13.5px] font-medium text-ink">
                    {doc.original_name}
                  </p>
                  <p className="text-[12px] text-ink-muted">
                    {formatBytes(doc.size_bytes)} · {formatDate(doc.uploaded_at)}
                  </p>
                </div>

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
              </motion.li>
            ))}
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
