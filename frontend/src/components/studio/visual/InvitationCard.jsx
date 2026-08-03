import { forwardRef } from 'react'

/**
 * Typeset invitation card, exported as PNG.
 *
 * Deliberately drawn with CSS and inline SVG rather than generated as a raster
 * image: image models render lettering unreliably, and a wedding card with a
 * misspelt name is worthless. Here the names, dates and venue are real text,
 * always correct and always crisp when printed.
 *
 * Colours are inlined rather than themed — the exported PNG must look the same
 * whether the app was in light or dark mode.
 */
const PALETTES = {
  marigold: {
    ink: '#4a2410', accent: '#c2410c', soft: '#fb923c',
    bg: '#fffaf2', panel: '#fff3e2', rule: '#e8b787',
  },
  rose: {
    ink: '#500724', accent: '#be123c', soft: '#fb7185',
    bg: '#fff5f7', panel: '#ffe9ef', rule: '#f0a8bd',
  },
  royal: {
    ink: '#2e1065', accent: '#6d28d9', soft: '#a78bfa',
    bg: '#faf7ff', panel: '#f1eaff', rule: '#c3aef0',
  },
  emerald: {
    ink: '#052e1b', accent: '#047857', soft: '#34d399',
    bg: '#f4fdf8', panel: '#e3f7ec', rule: '#93d4b4',
  },
  midnight: {
    ink: '#0b1220', accent: '#1e3a8a', soft: '#60a5fa',
    bg: '#f6f8fc', panel: '#e8eefa', rule: '#a9bfe4',
  },
  classic: {
    ink: '#1c1917', accent: '#78716c', soft: '#a8a29e',
    bg: '#fdfcfa', panel: '#f5f3ef', rule: '#d6d0c6',
  },
}

/** Corner flourish. Motif changes the shape, not the structure. */
function Corner({ colour, motif, rotate }) {
  const paths = {
    floral: (
      <>
        <path d="M4 60 C4 28 28 4 60 4" fill="none" stroke={colour} strokeWidth="1.4" />
        <circle cx="16" cy="16" r="4.5" fill="none" stroke={colour} strokeWidth="1.2" />
        <path d="M16 11.5 C22 14 22 18 16 20.5 C10 18 10 14 16 11.5Z" fill={colour} opacity="0.5" />
        <path d="M11.5 16 C14 10 18 10 20.5 16 C18 22 14 22 11.5 16Z" fill={colour} opacity="0.5" />
      </>
    ),
    paisley: (
      <>
        <path d="M4 60 C4 28 28 4 60 4" fill="none" stroke={colour} strokeWidth="1.4" />
        <path
          d="M14 34 C10 22 18 12 28 14 C36 16 34 26 26 26 C20 26 20 20 25 20"
          fill="none" stroke={colour} strokeWidth="1.3"
        />
      </>
    ),
    geometric: (
      <>
        <path d="M4 60 L4 4 L60 4" fill="none" stroke={colour} strokeWidth="1.4" />
        <path d="M12 40 L12 12 L40 12" fill="none" stroke={colour} strokeWidth="1" />
        <rect x="18" y="18" width="9" height="9" fill={colour} opacity="0.45" />
      </>
    ),
    minimal: <path d="M4 44 L4 4 L44 4" fill="none" stroke={colour} strokeWidth="1.4" />,
  }

  return (
    <svg
      width="72" height="72" viewBox="0 0 64 64"
      style={{ position: 'absolute', ...rotate }}
      aria-hidden="true"
    >
      {paths[motif] || paths.floral}
    </svg>
  )
}

function Divider({ colour }) {
  return (
    <svg width="150" height="14" viewBox="0 0 150 14" aria-hidden="true">
      <line x1="0" y1="7" x2="58" y2="7" stroke={colour} strokeWidth="1" />
      <line x1="92" y1="7" x2="150" y2="7" stroke={colour} strokeWidth="1" />
      <path
        d="M75 1.5 C80 5 80 9 75 12.5 C70 9 70 5 75 1.5Z"
        fill={colour} opacity="0.75"
      />
    </svg>
  )
}

const InvitationCard = forwardRef(function InvitationCard({ data }, ref) {
  const t = PALETTES[data.theme?.palette] || PALETTES.classic
  const motif = data.theme?.motif || 'floral'

  return (
    <div
      ref={ref}
      style={{
        width: 720,
        background: t.bg,
        color: t.ink,
        fontFamily: "'Georgia', 'Times New Roman', serif",
        padding: 26,
      }}
    >
      <div
        style={{
          position: 'relative',
          border: `1px solid ${t.rule}`,
          outline: `4px solid ${t.bg}`,
          boxShadow: `0 0 0 5px ${t.rule}`,
          padding: '52px 48px',
          textAlign: 'center',
          background: t.panel,
        }}
      >
        <Corner colour={t.accent} motif={motif} rotate={{ top: 10, left: 10 }} />
        <Corner
          colour={t.accent} motif={motif}
          rotate={{ top: 10, right: 10, transform: 'scaleX(-1)' }}
        />
        <Corner
          colour={t.accent} motif={motif}
          rotate={{ bottom: 10, left: 10, transform: 'scaleY(-1)' }}
        />
        <Corner
          colour={t.accent} motif={motif}
          rotate={{ bottom: 10, right: 10, transform: 'scale(-1,-1)' }}
        />

        <p
          style={{
            margin: 0, fontSize: 12, letterSpacing: '0.32em',
            textTransform: 'uppercase', color: t.accent,
          }}
        >
          {data.occasion}
        </p>

        {data.hosts && (
          <p style={{ margin: '20px 0 0', fontSize: 14.5, fontStyle: 'italic', opacity: 0.85 }}>
            {data.hosts}
          </p>
        )}

        <h1
          style={{
            margin: '14px 0 0', fontSize: 46, fontWeight: 400,
            letterSpacing: '0.02em', lineHeight: 1.18,
          }}
        >
          {data.headline}
        </h1>

        {data.sub_headline && (
          <p style={{ margin: '12px 0 0', fontSize: 15.5, fontStyle: 'italic', opacity: 0.9 }}>
            {data.sub_headline}
          </p>
        )}

        <div style={{ margin: '22px 0' }}>
          <Divider colour={t.accent} />
        </div>

        {data.message && (
          <p
            style={{
              margin: '0 auto', maxWidth: 440, fontSize: 14.5,
              lineHeight: 1.75, opacity: 0.92,
            }}
          >
            {data.message}
          </p>
        )}

        {(data.date_text || data.time_text) && (
          <div style={{ marginTop: 26 }}>
            <p style={{ margin: 0, fontSize: 20, letterSpacing: '0.05em' }}>
              {data.date_text}
            </p>
            {data.time_text && (
              <p style={{ margin: '6px 0 0', fontSize: 14.5, opacity: 0.85 }}>
                {data.time_text}
              </p>
            )}
          </div>
        )}

        {(data.venue_name || data.venue_address) && (
          <div style={{ marginTop: 20 }}>
            {data.venue_name && (
              <p style={{ margin: 0, fontSize: 16, fontWeight: 600 }}>{data.venue_name}</p>
            )}
            {data.venue_address && (
              <p style={{ margin: '4px 0 0', fontSize: 13.5, opacity: 0.8 }}>
                {data.venue_address}
              </p>
            )}
          </div>
        )}

        {data.events?.length > 0 && (
          <div
            style={{
              marginTop: 28, paddingTop: 20, borderTop: `1px solid ${t.rule}`,
              display: 'flex', justifyContent: 'center', flexWrap: 'wrap', gap: 30,
            }}
          >
            {data.events.map((event, index) => (
              <div key={index} style={{ minWidth: 130 }}>
                <p
                  style={{
                    margin: 0, fontSize: 11.5, letterSpacing: '0.18em',
                    textTransform: 'uppercase', color: t.accent,
                  }}
                >
                  {event.name}
                </p>
                {event.when && (
                  <p style={{ margin: '5px 0 0', fontSize: 13 }}>{event.when}</p>
                )}
                {event.where && (
                  <p style={{ margin: '2px 0 0', fontSize: 12.5, opacity: 0.75 }}>
                    {event.where}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}

        {(data.rsvp || data.footer_note) && (
          <div style={{ marginTop: 26, paddingTop: 16, borderTop: `1px solid ${t.rule}` }}>
            {data.footer_note && (
              <p style={{ margin: 0, fontSize: 13.5, fontStyle: 'italic', opacity: 0.85 }}>
                {data.footer_note}
              </p>
            )}
            {data.rsvp && (
              <p style={{ margin: '7px 0 0', fontSize: 12.5, opacity: 0.75 }}>
                RSVP · {data.rsvp}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  )
})

export default InvitationCard
