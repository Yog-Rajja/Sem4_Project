import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import PageShell from '../components/layout/PageShell'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import EmptyState from '../components/ui/EmptyState'
import ErrorState, { ErrorBanner } from '../components/ui/ErrorState'
import { Field, Input } from '../components/ui/Input'
import Modal from '../components/ui/Modal'
import Spinner from '../components/ui/Spinner'
import Badge from '../components/ui/Badge'
import { LinkIcon, PlusIcon, UsersIcon } from '../components/ui/Icons'
import api, { errorMessage } from '../lib/api'
import { unwrapList } from '../lib/list'

function extractToken(input) {
  const value = input.trim()
  const uuidPattern = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i
  const match = value.match(uuidPattern)
  return match ? match[0] : value
}

export default function Circles() {
  const navigate = useNavigate()

  const [circles, setCircles] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [createOpen, setCreateOpen] = useState(false)
  const [name, setName] = useState('')
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState('')

  const [joinOpen, setJoinOpen] = useState(false)
  const [joinInput, setJoinInput] = useState('')
  const [joining, setJoining] = useState(false)
  const [joinError, setJoinError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const { data } = await api.get('/circles/')
      setCircles(unwrapList(data))
    } catch (err) {
      setError(errorMessage(err, 'Could not load your circles.'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  // A pasted invite link like /circles?join=<token> opens the join dialog
  // pre-filled, the same pattern the dashboard uses for ?plan=1.
  useEffect(() => {
    const token = new URLSearchParams(window.location.search).get('join')
    if (token) {
      setJoinInput(token)
      setJoinOpen(true)
    }
  }, [])

  async function createCircle(e) {
    e.preventDefault()
    if (name.trim().length < 2) {
      setCreateError('Give the circle a slightly longer name.')
      return
    }
    setCreating(true)
    setCreateError('')
    try {
      const { data } = await api.post('/circles/', { name: name.trim() })
      navigate(`/circles/${data.id}`)
    } catch (err) {
      setCreateError(errorMessage(err, 'Could not create that circle.'))
    } finally {
      setCreating(false)
    }
  }

  async function joinCircle(e) {
    e.preventDefault()
    const token = extractToken(joinInput)
    if (!token) {
      setJoinError('Paste an invite link or code.')
      return
    }
    setJoining(true)
    setJoinError('')
    try {
      const { data } = await api.post('/circles/join/', { token })
      navigate(`/circles/${data.id}`)
    } catch (err) {
      setJoinError(
        err?.response?.status === 404
          ? 'That invite link is not valid — ask for a fresh one.'
          : errorMessage(err, 'Could not join that circle.'),
      )
    } finally {
      setJoining(false)
    }
  }

  return (
    <PageShell
      title="Circles"
      subtitle="Small groups who can see each other's progress, not each other's goals."
      actions={
        <>
          <Button variant="secondary" onClick={() => setJoinOpen(true)}>
            <LinkIcon size={15} />
            Join a circle
          </Button>
          <Button onClick={() => setCreateOpen(true)}>
            <PlusIcon size={15} />
            New circle
          </Button>
        </>
      }
    >
      {loading ? (
        <div className="grid place-items-center py-24 text-brand-600">
          <Spinner size={24} />
        </div>
      ) : error ? (
        <Card>
          <ErrorState message={error} onRetry={load} />
        </Card>
      ) : circles.length === 0 ? (
        <Card>
          <EmptyState
            icon={UsersIcon}
            title="No circles yet"
            message="Start one and invite a friend working toward something similar — a little friendly accountability goes a long way."
            action={
              <Button onClick={() => setCreateOpen(true)}>
                <PlusIcon size={15} />
                Start a circle
              </Button>
            }
          />
        </Card>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {circles.map((circle, index) => (
            <motion.button
              key={circle.id}
              type="button"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.22, delay: Math.min(index * 0.04, 0.2) }}
              onClick={() => navigate(`/circles/${circle.id}`)}
              className="flex flex-col items-start gap-2.5 rounded-card border border-line bg-surface p-4 text-left shadow-card transition-all duration-150 hover:-translate-y-0.5 hover:border-brand-200 hover:shadow-pop"
            >
              <span className="grid h-9 w-9 place-items-center rounded-xl bg-brand-100 text-brand-700">
                <UsersIcon size={17} />
              </span>
              <p className="text-[14.5px] font-semibold text-ink">{circle.name}</p>
              <div className="flex items-center gap-1.5">
                <Badge>
                  {circle.member_count} member{circle.member_count === 1 ? '' : 's'}
                </Badge>
                {circle.is_owner && <Badge tone="brand">Owner</Badge>}
              </div>
            </motion.button>
          ))}
        </div>
      )}

      <Modal
        open={createOpen}
        onClose={() => !creating && setCreateOpen(false)}
        title="Start a circle"
        description="Invite anyone with the link once it's created."
        footer={
          <>
            <Button variant="secondary" onClick={() => setCreateOpen(false)} disabled={creating}>
              Cancel
            </Button>
            <Button onClick={createCircle} loading={creating}>
              Create
            </Button>
          </>
        }
      >
        <form onSubmit={createCircle}>
          {createError && <ErrorBanner message={createError} />}
          <Field label="Circle name" htmlFor="circle-name" className="mt-3">
            <Input
              id="circle-name"
              autoFocus
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="GATE Warriors"
            />
          </Field>
        </form>
      </Modal>

      <Modal
        open={joinOpen}
        onClose={() => !joining && setJoinOpen(false)}
        title="Join a circle"
        description="Paste the invite link or code someone shared with you."
        footer={
          <>
            <Button variant="secondary" onClick={() => setJoinOpen(false)} disabled={joining}>
              Cancel
            </Button>
            <Button onClick={joinCircle} loading={joining}>
              Join
            </Button>
          </>
        }
      >
        <form onSubmit={joinCircle}>
          {joinError && <ErrorBanner message={joinError} />}
          <Field label="Invite link or code" htmlFor="join-token" className="mt-3">
            <Input
              id="join-token"
              autoFocus
              value={joinInput}
              onChange={(e) => setJoinInput(e.target.value)}
              placeholder="Paste it here"
            />
          </Field>
        </form>
      </Modal>
    </PageShell>
  )
}
