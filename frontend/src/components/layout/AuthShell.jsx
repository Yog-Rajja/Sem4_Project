import { motion } from 'framer-motion'
import { CompassIcon } from '../ui/Icons'

const HIGHLIGHTS = [
  'Describe a goal in plain English, get a dated roadmap back.',
  'Every milestone comes with real videos and a search link.',
  'Track tasks, deadlines and progress in one dashboard.',
]

/** Split layout for the signed-out screens: form on the left, pitch on the right. */
export default function AuthShell({ title, subtitle, children, footer }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
      <div className="flex items-center justify-center px-5 py-10 sm:px-8">
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
          className="w-full max-w-sm"
        >
          <div className="mb-7 flex items-center gap-2.5">
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-brand-600 text-white">
              <CompassIcon size={19} />
            </span>
            <span className="text-[15px] font-semibold tracking-[-0.01em]">
              Smart Companion
            </span>
          </div>

          <h1 className="text-[26px] font-semibold tracking-[-0.025em] text-ink">
            {title}
          </h1>
          <p className="mt-1.5 text-[13.5px] text-ink-muted">{subtitle}</p>

          <div className="mt-7">{children}</div>

          {footer && <div className="mt-6 text-[13px] text-ink-muted">{footer}</div>}
        </motion.div>
      </div>

      <div className="relative hidden overflow-hidden bg-brand-600 lg:block">
        <div
          className="absolute inset-0 opacity-30"
          style={{
            backgroundImage:
              'radial-gradient(circle at 20% 15%, #afcdea 0, transparent 45%), radial-gradient(circle at 80% 75%, #14456f 0, transparent 50%)',
          }}
        />
        <div className="relative flex h-full flex-col justify-center px-14">
          <p className="max-w-md text-[26px] leading-[1.3] font-semibold tracking-[-0.02em] text-white">
            Turn “I want to crack GATE” into a plan you can actually follow.
          </p>
          <ul className="mt-8 space-y-3.5">
            {HIGHLIGHTS.map((line) => (
              <li key={line} className="flex items-start gap-3 text-[14px] text-brand-100">
                <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-200" />
                {line}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  )
}
