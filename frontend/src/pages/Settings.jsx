import { useCallback, useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import PageShell from '../components/layout/PageShell'
import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import Card, { CardHeader } from '../components/ui/Card'
import { Input, Select } from '../components/ui/Input'
import Spinner from '../components/ui/Spinner'
import { ErrorBanner } from '../components/ui/ErrorState'
import { useToast } from '../components/ui/Toast'
import { BellIcon, MoonIcon, SunIcon } from '../components/ui/Icons'
import cn from '../lib/cn'
import api, { errorMessage } from '../lib/api'
import { permission, pushSupported, subscribe, unsubscribe } from '../lib/push'
import { useTheme } from '../context/ThemeContext'

function Toggle({ checked, onChange, disabled, label }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={cn(
        'relative h-6 w-11 shrink-0 rounded-full transition-colors duration-150',
        checked ? 'bg-brand-600' : 'bg-line-strong',
        disabled && 'cursor-not-allowed opacity-50',
      )}
    >
      <span
        className={cn(
          'absolute top-0.5 h-5 w-5 rounded-full bg-white shadow-sm transition-transform duration-150',
          checked ? 'translate-x-5.5' : 'translate-x-0.5',
        )}
      />
    </button>
  )
}

function Row({ title, description, children, warning }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-line px-5 py-4 last:border-0">
      <div className="min-w-0 flex-1">
        <p className="text-[13.5px] font-medium text-ink">{title}</p>
        <p className="mt-1 text-[12.5px] leading-relaxed text-ink-muted">
          {description}
        </p>
        {warning && (
          <p className="mt-1.5 text-[12.5px] leading-relaxed text-warning">{warning}</p>
        )}
      </div>
      <div className="flex shrink-0 items-center gap-2 pt-0.5">{children}</div>
    </div>
  )
}

export default function Settings() {
  const toast = useToast()
  const { isDark, toggle } = useTheme()

  const [settings, setSettings] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const [perm, setPerm] = useState(permission())
  const [emailDraft, setEmailDraft] = useState('')
  const [preview, setPreview] = useState(null)

  const load = useCallback(async () => {
    try {
      const [settingsRes, previewRes] = await Promise.all([
        api.get('/notifications/settings/'),
        api.get('/notifications/preview/'),
      ])
      setSettings(settingsRes.data)
      setEmailDraft(settingsRes.data.email_address || '')
      setPreview(previewRes.data)
    } catch (err) {
      setError(errorMessage(err, 'Could not load your settings.'))
    } finally {
      setLoading(false)
    }
  }, [])

  async function saveEmail() {
    setBusy('email')
    setError('')
    try {
      const { data } = await api.patch('/notifications/settings/', {
        email_address: emailDraft.trim(),
      })
      setSettings((current) => ({ ...current, ...data }))
      toast.success(
        data.resolved_email
          ? `Digests will go to ${data.resolved_email}.`
          : 'Address cleared.',
      )
    } catch (err) {
      setError(errorMessage(err, 'That address was not accepted.'))
    } finally {
      setBusy('')
    }
  }

  useEffect(() => {
    load()
  }, [load])

  async function patch(changes) {
    const previous = settings
    setSettings((current) => ({ ...current, ...changes }))
    try {
      const { data } = await api.patch('/notifications/settings/', changes)
      setSettings((current) => ({ ...current, ...data }))
    } catch (err) {
      setSettings(previous)
      toast.error(errorMessage(err, 'Could not save that.'))
    }
  }

  async function enablePush(next) {
    setError('')
    if (!next) {
      setBusy('push')
      try {
        await unsubscribe()
        await patch({ push_daily: false })
        setPerm(permission())
        toast.success('Push notifications turned off.')
      } finally {
        setBusy('')
      }
      return
    }

    setBusy('push')
    try {
      await subscribe(settings.vapid_public_key)
      await patch({ push_daily: true })
      setPerm(permission())
      await load()
      toast.success('This device will now get your daily digest.')
    } catch (err) {
      setError(err.message || 'Could not enable notifications.')
    } finally {
      setBusy('')
    }
  }

  async function sendTest() {
    setBusy('test')
    setError('')
    try {
      const { data } = await api.post('/notifications/test/', {})
      if (data.pushed || data.emailed) {
        toast.success(data.detail)
      } else {
        setError(data.detail)
      }
    } catch (err) {
      setError(errorMessage(err, 'Could not send a test notification.'))
    } finally {
      setBusy('')
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

  const supported = pushSupported()
  const blocked = perm === 'denied'

  return (
    <PageShell title="Settings" subtitle="How Smart Companion reaches you.">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.22 }}
        className="mx-auto max-w-2xl space-y-3"
      >
        {error && <ErrorBanner message={error} onDismiss={() => setError('')} />}

        <Card>
          <CardHeader
            title="Daily digest"
            subtitle="Today's tasks and anything overdue, once a morning"
            action={
              settings?.devices > 0 ? (
                <Badge tone="brand">
                  {settings.devices} device{settings.devices === 1 ? '' : 's'}
                </Badge>
              ) : null
            }
          />

          <Row
            title="Push to this device"
            description={
              supported
                ? 'Arrives on your phone or desktop even with the site closed. Uses the browser’s own push service — nothing is shared with a third party.'
                : 'This browser does not support push notifications. Try Chrome or Edge on Android or desktop.'
            }
            warning={
              blocked
                ? 'Notifications are blocked for this site. You’ll need to allow them in your browser’s site settings first.'
                : !settings?.push_supported
                  ? 'The server has no VAPID keys yet. Run: manage.py generate_vapid_keys'
                  : ''
            }
          >
            {busy === 'push' ? (
              <Spinner size={16} />
            ) : (
              <Toggle
                label="Push notifications"
                checked={Boolean(settings?.push_daily)}
                disabled={!supported || blocked || !settings?.push_supported}
                onChange={enablePush}
              />
            )}
          </Row>

          <Row
            title="Email me"
            description="The same digest as an email, with every task listed and how many are left."
            warning={
              settings?.email_mode === 'console'
                ? 'Not actually sending yet — mail is printed to the server console. Add EMAIL_HOST_USER and EMAIL_HOST_PASSWORD to backend/.env and restart the backend. Check it with: manage.py check_email'
                : ''
            }
          >
            <Toggle
              label="Email digest"
              checked={Boolean(settings?.email_daily)}
              onChange={(next) => patch({ email_daily: next })}
            />
          </Row>

          <Row
            title="Send to"
            description={
              settings?.account_email
                ? `Leave blank to use your account address (${settings.account_email}).`
                : 'Your account has no email address, so set one here.'
            }
          >
            <div className="w-64">
              <div className="flex gap-2">
                <Input
                  type="email"
                  aria-label="Digest email address"
                  placeholder={settings?.account_email || 'you@example.com'}
                  value={emailDraft}
                  onChange={(e) => setEmailDraft(e.target.value)}
                  invalid={Boolean(emailDraft) && !emailDraft.includes('@')}
                />
                <Button
                  variant="secondary"
                  size="md"
                  disabled={emailDraft === (settings?.email_address || '')}
                  loading={busy === 'email'}
                  onClick={saveEmail}
                >
                  Save
                </Button>
              </div>
              {settings?.resolved_email && (
                <p className="mt-1.5 text-[12px] text-ink-muted">
                  Digests go to{' '}
                  <span className="font-medium text-ink-soft">
                    {settings.resolved_email}
                  </span>
                  {settings.email_from && <> · sent from {settings.email_from}</>}
                </p>
              )}
            </div>
          </Row>

          <Row
            title="Send at"
            description="The digest goes out at or after this hour, once a day."
          >
            <Select
              aria-label="Digest hour"
              value={settings?.send_hour ?? 8}
              onChange={(e) => patch({ send_hour: Number(e.target.value) })}
              className="w-28"
            >
              {Array.from({ length: 24 }, (_, hour) => (
                <option key={hour} value={hour}>
                  {String(hour).padStart(2, '0')}:00
                </option>
              ))}
            </Select>
          </Row>

          <div className="flex flex-wrap items-center justify-between gap-3 bg-surface-muted px-5 py-3.5">
            <p className="text-[12.5px] text-ink-muted">
              Send one right now to check it works.
            </p>
            <Button variant="secondary" size="sm" loading={busy === 'test'} onClick={sendTest}>
              {busy !== 'test' && <BellIcon size={15} />}
              Send a test
            </Button>
          </div>
        </Card>

        {preview && (
          <Card>
            <CardHeader
              title="What today's message would say"
              subtitle="Generated from your live tasks — nothing is sent"
            />
            <div className="px-5 pb-5">
              <p className="text-[15px] font-semibold text-ink">{preview.title}</p>
              <p className="mt-1 text-[13px] text-ink-muted">{preview.body}</p>

              <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1.5 border-y border-line py-2.5 text-[12.5px] text-ink-muted">
                <span>
                  <strong className="font-semibold text-ink">
                    {preview.counts.today}
                  </strong>{' '}
                  due today
                </span>
                <span>
                  <strong className="font-semibold text-danger">
                    {preview.counts.overdue}
                  </strong>{' '}
                  overdue
                </span>
                <span>
                  <strong className="font-semibold text-ink">
                    {preview.counts.this_week}
                  </strong>{' '}
                  this week
                </span>
                <span>
                  <strong className="font-semibold text-ink">
                    {preview.counts.remaining}
                  </strong>{' '}
                  left in total
                </span>
              </div>

              {preview.goals.length > 0 && (
                <ul className="mt-3 space-y-1.5">
                  {preview.goals.map((goal) => (
                    <li
                      key={goal.title}
                      className="flex items-center justify-between gap-3 text-[13px]"
                    >
                      <span className="truncate text-ink-soft">{goal.title}</span>
                      <span className="shrink-0 text-ink-muted">
                        <strong className="font-semibold text-brand-600">
                          {goal.left}
                        </strong>{' '}
                        left of {goal.total}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </Card>
        )}

        <Card>
          <CardHeader title="Appearance" />
          <Row title="Theme" description="Follows your system unless you choose here.">
            <Button variant="secondary" size="sm" onClick={toggle}>
              {isDark ? <SunIcon size={15} /> : <MoonIcon size={15} />}
              {isDark ? 'Light' : 'Dark'}
            </Button>
          </Row>
        </Card>

        <p className="px-1 text-[12px] leading-relaxed text-ink-muted">
          Digests are sent by a scheduled task on the server
          (<code className="text-ink-soft">manage.py notify_daily</code>), not from
          your browser — so they arrive whether or not the app is open.
        </p>
      </motion.div>
    </PageShell>
  )
}
