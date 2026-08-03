import { useEffect, useState } from 'react'
import Button from '../ui/Button'
import Modal from '../ui/Modal'
import { useToast } from '../ui/Toast'
import { ExternalIcon } from '../ui/Icons'
import api, { errorMessage } from '../../lib/api'

/** Turn a roadmap into a public read-only link, and take it down again. */
export default function ShareDialog({ open, onClose, goal, onChange }) {
  const toast = useToast()
  const [shared, setShared] = useState(Boolean(goal.is_shared))
  const [token, setToken] = useState(goal.is_shared ? goal.share_token : null)
  const [busy, setBusy] = useState(false)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    setShared(Boolean(goal.is_shared))
    setToken(goal.is_shared ? goal.share_token : null)
  }, [goal.is_shared, goal.share_token])

  const url = token ? `${window.location.origin}/r/${token}` : ''

  async function toggle(next) {
    setBusy(true)
    try {
      const { data } = await api.post(`/goals/${goal.id}/share/`, { shared: next })
      setShared(data.is_shared)
      setToken(data.share_token)
      onChange?.(data)
      toast.success(next ? 'Anyone with the link can now view this.' : 'Link disabled.')
    } catch (err) {
      toast.error(errorMessage(err, 'Could not update sharing.'))
    } finally {
      setBusy(false)
    }
  }

  async function copy() {
    try {
      await navigator.clipboard.writeText(url)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      toast.error('Could not copy. Select the link and copy it manually.')
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Share this roadmap"
      description="A read-only page anyone can open — no account needed."
      footer={<Button onClick={onClose}>Done</Button>}
    >
      <div className="space-y-4">
        <div className="flex items-start gap-3 rounded-lg border border-line bg-surface-muted px-3.5 py-3">
          <div className="min-w-0 flex-1">
            <p className="text-[13.5px] font-medium text-ink">
              {shared ? 'Sharing is on' : 'This roadmap is private'}
            </p>
            <p className="mt-1 text-[12.5px] leading-relaxed text-ink-muted">
              {shared
                ? 'Anyone holding the link can see the plan and its progress. Your email, notes and documents are never included.'
                : 'Only you can see it. Turn sharing on to get a link.'}
            </p>
          </div>
          <Button
            size="sm"
            variant={shared ? 'secondary' : 'primary'}
            loading={busy}
            onClick={() => toggle(!shared)}
          >
            {shared ? 'Turn off' : 'Turn on'}
          </Button>
        </div>

        {shared && url && (
          <div>
            <label htmlFor="share-url" className="mb-1.5 block text-[13px] font-medium text-ink-soft">
              Link
            </label>
            <div className="flex gap-2">
              <input
                id="share-url"
                readOnly
                value={url}
                onFocus={(e) => e.target.select()}
                className="h-9.5 flex-1 rounded-lg border border-line bg-surface px-3 text-[13px] text-ink-soft outline-none focus:border-brand-500"
              />
              <Button variant="secondary" onClick={copy}>
                {copied ? 'Copied' : 'Copy'}
              </Button>
            </div>
            <a
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-2 inline-flex items-center gap-1.5 text-[12.5px] font-medium text-brand-600 hover:text-brand-700"
            >
              Open the shared page
              <ExternalIcon size={12} />
            </a>
          </div>
        )}
      </div>
    </Modal>
  )
}
