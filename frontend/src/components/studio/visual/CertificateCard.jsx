import { forwardRef } from 'react'
import { formatDate } from '../../../lib/format'

/**
 * Completion certificate, exported as PNG.
 *
 * Deliberately drawn as a formal keepsake: deep navy border, a wax-seal
 * medallion, serif type, distinct from the warm-palette Invitation card so
 * the two never get confused at a glance. Every number on it is a fact
 * computed server-side (see apps/studio/services/certificate.py); only the
 * tagline is AI-written, and even that falls back to a canned line if every
 * model is unavailable, so an achievement never fails to render.
 *
 * Colours are inlined rather than themed: the exported PNG must look the
 * same regardless of the app's light/dark mode when it was generated.
 */
const INK = '#132a40'
const ACCENT = '#14456f'
const GOLD = '#b8860b'
const PAPER = '#fdfcf8'
const RULE = '#d5e0e8'

function Seal() {
  return (
    <svg width="86" height="86" viewBox="0 0 86 86" aria-hidden="true">
      <circle cx="43" cy="43" r="40" fill="none" stroke={GOLD} strokeWidth="1.4" />
      <circle cx="43" cy="43" r="33" fill="none" stroke={GOLD} strokeWidth="1" />
      {Array.from({ length: 24 }, (_, i) => {
        const angle = (i / 24) * Math.PI * 2
        const x1 = 43 + Math.cos(angle) * 33
        const y1 = 43 + Math.sin(angle) * 33
        const x2 = 43 + Math.cos(angle) * 37
        const y2 = 43 + Math.sin(angle) * 37
        return (
          <line
            key={i}
            x1={x1} y1={y1} x2={x2} y2={y2}
            stroke={GOLD} strokeWidth="1"
          />
        )
      })}
      <path
        d="M30 44 L39 53 L57 32"
        fill="none"
        stroke={GOLD}
        strokeWidth="3.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function CornerFlourish({ rotate }) {
  return (
    <svg
      width="56" height="56" viewBox="0 0 56 56"
      style={{ position: 'absolute', ...rotate }}
      aria-hidden="true"
    >
      <path d="M4 52 C4 24 24 4 52 4" fill="none" stroke={ACCENT} strokeWidth="1.2" opacity="0.5" />
      <path d="M4 40 C4 20 20 4 40 4" fill="none" stroke={GOLD} strokeWidth="1" opacity="0.6" />
    </svg>
  )
}

const CertificateCard = forwardRef(function CertificateCard({ data }, ref) {
  return (
    <div
      ref={ref}
      style={{
        width: 760,
        background: PAPER,
        color: INK,
        fontFamily: "'Georgia', 'Times New Roman', serif",
        padding: 24,
      }}
    >
      <div
        style={{
          position: 'relative',
          border: `2px solid ${ACCENT}`,
          outline: `4px solid ${PAPER}`,
          boxShadow: `0 0 0 5px ${RULE}`,
          padding: '50px 56px 44px',
          textAlign: 'center',
        }}
      >
        <CornerFlourish rotate={{ top: 10, left: 10 }} />
        <CornerFlourish rotate={{ top: 10, right: 10, transform: 'scaleX(-1)' }} />
        <CornerFlourish rotate={{ bottom: 10, left: 10, transform: 'scaleY(-1)' }} />
        <CornerFlourish rotate={{ bottom: 10, right: 10, transform: 'scale(-1,-1)' }} />

        <p
          style={{
            margin: 0,
            fontSize: 11.5,
            letterSpacing: '0.34em',
            textTransform: 'uppercase',
            color: ACCENT,
          }}
        >
          Certificate of Completion
        </p>

        <p style={{ margin: '26px 0 6px', fontSize: 13, color: '#52525b' }}>
          This certifies that
        </p>
        <h1
          style={{
            margin: 0,
            fontSize: 38,
            fontWeight: 400,
            letterSpacing: '0.01em',
          }}
        >
          {data.recipient_name}
        </h1>

        <p style={{ margin: '18px 0 6px', fontSize: 13, color: '#52525b' }}>
          has completed every task in
        </p>
        <p
          style={{
            margin: 0,
            fontSize: 21,
            fontStyle: 'italic',
            color: ACCENT,
            lineHeight: 1.35,
          }}
        >
          “{data.goal_title}”
        </p>

        <div style={{ margin: '28px auto', width: 130, height: 1, background: RULE }} />

        <p
          style={{
            margin: '0 auto',
            maxWidth: 440,
            fontSize: 14,
            fontStyle: 'italic',
            lineHeight: 1.7,
            color: '#3f3f52',
          }}
        >
          {data.tagline}
        </p>

        <div
          style={{
            marginTop: 30,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 40,
          }}
        >
          <div style={{ textAlign: 'left' }}>
            <p style={{ margin: 0, fontSize: 20, fontWeight: 600 }}>
              {data.total_tasks}
            </p>
            <p style={{ margin: '2px 0 0', fontSize: 10.5, color: '#8b8b94' }}>
              tasks completed
            </p>
          </div>
          <div style={{ width: 1, height: 32, background: RULE }} />
          <div style={{ textAlign: 'left' }}>
            <p style={{ margin: 0, fontSize: 20, fontWeight: 600 }}>
              {data.milestone_count}
            </p>
            <p style={{ margin: '2px 0 0', fontSize: 10.5, color: '#8b8b94' }}>
              milestones
            </p>
          </div>
          <div style={{ width: 1, height: 32, background: RULE }} />
          <div style={{ textAlign: 'left' }}>
            <p style={{ margin: 0, fontSize: 20, fontWeight: 600 }}>
              {data.days_taken}
            </p>
            <p style={{ margin: '2px 0 0', fontSize: 10.5, color: '#8b8b94' }}>
              days
            </p>
          </div>
        </div>

        <div
          style={{
            marginTop: 36,
            display: 'flex',
            alignItems: 'flex-end',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ textAlign: 'left' }}>
            <p style={{ margin: 0, fontSize: 15, fontStyle: 'italic' }}>
              Smart Companion
            </p>
            <div style={{ marginTop: 4, width: 120, borderTop: `1px solid ${INK}` }} />
            <p style={{ margin: '4px 0 0', fontSize: 10, color: '#8b8b94' }}>
              Issued {formatDate(data.completed_date)}
            </p>
          </div>
          <Seal />
        </div>
      </div>
    </div>
  )
})

export default CertificateCard
