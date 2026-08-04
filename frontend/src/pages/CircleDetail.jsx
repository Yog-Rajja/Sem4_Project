import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import PageShell from '../components/layout/PageShell'
import LeaderboardRow from '../components/circles/LeaderboardRow'
import Button from '../components/ui/Button'
import Card, { CardHeader } from '../components/ui/Card'
import ConfirmDialog from '../components/ui/ConfirmDialog'
import ErrorState from '../components/ui/ErrorState'
import Modal from '../components/ui/Modal'
import Spinner from '../components/ui/Spinner'
import { useToast } from '../components/ui/Toast'
import { ExternalIcon, LinkIcon, SparklesIcon, TrashIcon, UsersIcon } from '../components/ui/Icons'
import api, { errorMessage } from '../lib/api'
import { formatDate } from '../lib/format'

export default function CircleDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const toast = useToast()

  const [circle, setCircle] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [inviteOpen, setInviteOpen] = useState(false)
  const [regenerating, setRegenerating] = useState(false)
  const [copied, setCopied] = useState(false)

  const [confirmLeave, setConfirmLeave] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const { data } = await api.get(`/circles/${id}/`)
      setCircle(data)
    } catch (err) {
      setError(
        err?.response?.status === 404
          ? "This circle doesn't exist, or you're not in it."
          : errorMessage(err, 'Could not load this circle.'),
      )
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    load()
  }, [load])

  const inviteUrl = circle
    ? `${window.location.origin}/circles?join=${circle.invite_token}`
    : ''

  async function copyInvite() {
    try {
      await navigator.clipboard.writeText(inviteUrl)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      toast.error('Could not copy. Select the link and copy it manually.')
    }
  }

  async function regenerateInvite() {
    setRegenerating(true)
    try {
      const { data } = await api.post(`/circles/${id}/regenerate-invite/`)
      setCircle(data)
      toast.success('Old invite links no longer work.')
    } catch (err) {
      toast.error(errorMessage(err, 'Could not reset the invite link.'))
    } finally {
      setRegenerating(false)
    }
  }

  async function leave() {
    setBusy(true)
    try {
      await api.post(`/circles/${id}/leave/`)
      toast.success('You left the circle.')
      navigate('/circles', { replace: true })
    } catch (err) {
      toast.error(errorMessage(err, 'Could not leave that circle.'))
      setBusy(false)
    }
  }

  async function remove() {
    setBusy(true)
    try {
      await api.delete(`/circles/${id}/`)
      toast.success('Circle deleted.')
      navigate('/circles', { replace: true })
    } catch (err) {
      toast.error(errorMessage(err, 'Could not delete that circle.'))
      setBusy(false)
    }
  }

  if (loading) {
    return (
      <PageShell>
        <div className="grid place-items-center py-24 text-brand-600">
          <Spinner size={24} />
        </div>
      </PageShell>
    )
  }

  if (error) {
    return (
      <PageShell title="Circle">
        <Card>
          <ErrorState message={error} onRetry={load} />
          <div className="pb-6 text-center">
            <Link to="/circles" className="text-[13px] font-medium text-brand-600 hover:text-brand-700">
              Back to circles
            </Link>
          </div>
        </Card>
      </PageShell>
    )
  }

  return (
    <PageShell>
      <Link
        to="/circles"
        className="text-[13px] font-medium text-ink-muted transition-colors hover:text-ink"
      >
        ← All circles
      </Link>

      <div className="mt-3 mb-5 flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="grid h-11 w-11 place-items-center rounded-xl bg-brand-100 text-brand-700">
            <UsersIcon size={20} />
          </span>
          <div>
            <h1 className="text-xl font-semibold tracking-[-0.02em] text-ink sm:text-[22px]">
              {circle.name}
            </h1>
            <p className="mt-0.5 text-[13px] text-ink-muted">
              {circle.member_count} member{circle.member_count === 1 ? '' : 's'} · started{' '}
              {formatDate(circle.created_at)}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="secondary" size="sm" onClick={() => setInviteOpen(true)}>
            <LinkIcon size={15} />
            Invite
          </Button>
          {circle.is_owner ? (
            <Button
              variant="dangerGhost"
              size="icon"
              onClick={() => setConfirmDelete(true)}
              aria-label="Delete circle"
            >
              <TrashIcon size={16} />
            </Button>
          ) : (
            <Button
              variant="ghost"
              size="sm"
              className="text-danger hover:bg-danger-soft"
              onClick={() => setConfirmLeave(true)}
            >
              Leave
            </Button>
          )}
        </div>
      </div>

      <Card>
        <CardHeader
          title="Leaderboard"
          subtitle="Ranked by tasks completed this week, then by current streak"
        />
        <div className="px-2.5 pb-3">
          <AnimatePresence initial={false}>
            {circle.leaderboard.map((row, index) => (
              <LeaderboardRow key={row.user_id} row={row} index={index} />
            ))}
          </AnimatePresence>
        </div>
      </Card>

      <Modal
        open={inviteOpen}
        onClose={() => setInviteOpen(false)}
        title="Invite to this circle"
        description="Anyone with this link can join. Only aggregate stats are ever shown, never your goal titles or tasks."
        footer={<Button onClick={() => setInviteOpen(false)}>Done</Button>}
      >
        <div className="space-y-3">
          <div className="flex gap-2">
            <input
              readOnly
              value={inviteUrl}
              onFocus={(e) => e.target.select()}
              aria-label="Invite link"
              className="h-9.5 flex-1 rounded-lg border border-line bg-surface px-3 text-[13px] text-ink-soft outline-none focus:border-brand-500"
            />
            <Button variant="secondary" onClick={copyInvite}>
              {copied ? 'Copied' : 'Copy'}
            </Button>
          </div>
          <a
            href={inviteUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-[12.5px] font-medium text-brand-600 hover:text-brand-700"
          >
            Open the join page
            <ExternalIcon size={12} />
          </a>

          {circle.is_owner && (
            <div className="border-t border-line pt-3">
              <Button
                variant="ghost"
                size="sm"
                onClick={regenerateInvite}
                loading={regenerating}
              >
                {!regenerating && <SparklesIcon size={14} />}
                Reset link
              </Button>
              <p className="mt-1.5 text-[12px] text-ink-muted">
                Generates a new link and disables this one. Use it if the old link got
                shared too widely.
              </p>
            </div>
          )}
        </div>
      </Modal>

      <ConfirmDialog
        open={confirmLeave}
        onClose={() => !busy && setConfirmLeave(false)}
        onConfirm={leave}
        loading={busy}
        title="Leave this circle?"
        message={`You'll stop seeing "${circle.name}"'s leaderboard. You can rejoin later with an invite link.`}
        confirmLabel="Leave"
      />

      <ConfirmDialog
        open={confirmDelete}
        onClose={() => !busy && setConfirmDelete(false)}
        onConfirm={remove}
        loading={busy}
        title="Delete this circle?"
        message={`"${circle.name}" will be removed for everyone in it. This can't be undone.`}
      />
    </PageShell>
  )
}
