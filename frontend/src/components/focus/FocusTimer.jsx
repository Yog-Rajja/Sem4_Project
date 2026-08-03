import { useCallback, useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import cn from '../../lib/cn'
import Button from '../ui/Button'
import { PauseIcon, PlayIcon, StopIcon } from '../ui/Icons'

const RING = 2 * Math.PI * 86

function format(totalSeconds) {
  const safe = Math.max(0, totalSeconds)
  const minutes = String(Math.floor(safe / 60)).padStart(2, '0')
  const seconds = String(safe % 60).padStart(2, '0')
  return `${minutes}:${seconds}`
}

/**
 * Countdown ring.
 *
 * Elapsed time is derived from wall-clock timestamps rather than counted by
 * the interval, so a throttled background tab still reports the real duration.
 */
export default function FocusTimer({
  minutes,
  running,
  paused,
  onStart,
  onPause,
  onResume,
  onFinish,
  busy,
  mode = 'focus',
}) {
  const total = minutes * 60
  const [elapsed, setElapsed] = useState(0)
  const startedRef = useRef(null)
  const bankedRef = useRef(0)

  // Reset whenever a fresh session is configured.
  useEffect(() => {
    if (!running) {
      setElapsed(0)
      startedRef.current = null
      bankedRef.current = 0
    }
  }, [running, minutes])

  useEffect(() => {
    if (!running || paused) return
    if (startedRef.current === null) startedRef.current = Date.now()

    const tick = () => {
      const live = (Date.now() - startedRef.current) / 1000
      setElapsed(Math.floor(bankedRef.current + live))
    }
    tick()
    const id = setInterval(tick, 250)
    return () => clearInterval(id)
  }, [running, paused])

  const remaining = total - elapsed
  const finishRef = useRef(onFinish)
  finishRef.current = onFinish

  // Auto-complete the moment the countdown reaches zero.
  useEffect(() => {
    if (running && remaining <= 0) finishRef.current(elapsed, true)
  }, [running, remaining, elapsed])

  // Surface the countdown in the tab title so it works while you're elsewhere.
  useEffect(() => {
    if (running && !paused) {
      document.title = `${format(remaining)} · ${mode === 'break' ? 'Break' : 'Focus'}`
    } else {
      document.title = 'Smart Companion'
    }
    return () => {
      document.title = 'Smart Companion'
    }
  }, [running, paused, remaining, mode])

  const pause = useCallback(() => {
    bankedRef.current = elapsed
    startedRef.current = null
    onPause()
  }, [elapsed, onPause])

  const progress = total ? Math.min(1, elapsed / total) : 0
  const isBreak = mode === 'break'

  return (
    <div className="flex flex-col items-center">
      <div className="relative h-56 w-56">
        <svg viewBox="0 0 200 200" className="h-full w-full -rotate-90">
          <circle
            cx="100"
            cy="100"
            r="86"
            fill="none"
            strokeWidth="10"
            className="stroke-line"
          />
          <motion.circle
            cx="100"
            cy="100"
            r="86"
            fill="none"
            strokeWidth="10"
            strokeLinecap="round"
            className={isBreak ? 'stroke-success' : 'stroke-brand-500'}
            strokeDasharray={RING}
            animate={{ strokeDashoffset: RING * (1 - progress) }}
            transition={{ duration: 0.3, ease: 'linear' }}
          />
        </svg>

        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-[42px] leading-none font-semibold tracking-[-0.03em] tabular-nums text-ink">
            {format(running ? remaining : total)}
          </span>
          <span className="mt-2 text-[12px] font-medium tracking-wide text-ink-muted uppercase">
            {!running ? (isBreak ? 'Break' : 'Focus') : paused ? 'Paused' : isBreak ? 'Break' : 'In focus'}
          </span>
        </div>
      </div>

      <div className="mt-7 flex items-center gap-2">
        {!running ? (
          <Button size="lg" onClick={onStart} loading={busy} className="px-7">
            <PlayIcon size={17} />
            Start {isBreak ? 'break' : 'focus'}
          </Button>
        ) : (
          <>
            <Button
              size="lg"
              variant="secondary"
              onClick={paused ? onResume : pause}
              className="px-6"
            >
              {paused ? <PlayIcon size={16} /> : <PauseIcon size={16} />}
              {paused ? 'Resume' : 'Pause'}
            </Button>
            <Button
              size="lg"
              variant="danger"
              onClick={() => onFinish(elapsed, false)}
              loading={busy}
              className="px-6"
            >
              <StopIcon size={16} />
              Stop
            </Button>
          </>
        )}
      </div>

      {running && (
        <p className={cn('mt-3 text-[12.5px] text-ink-muted')}>
          {Math.floor(elapsed / 60)} min banked so far — stopping early still counts it.
        </p>
      )}
    </div>
  )
}
