import { forwardRef } from 'react'

/** Weekly timetable as a printable/shareable grid, exported to PNG. */
const TimetableCard = forwardRef(function TimetableCard({ data }, ref) {
  return (
    <div
      ref={ref}
      style={{
        width: 980,
        background: '#ffffff',
        color: '#18181b',
        fontFamily: "'Inter', system-ui, sans-serif",
        padding: 36,
      }}
    >
      <div style={{ borderBottom: '2px solid #18181b', paddingBottom: 16 }}>
        <h1 style={{ margin: 0, fontSize: 27, letterSpacing: '-0.02em' }}>
          {data.title}
        </h1>
        {data.summary && (
          <p style={{ margin: '8px 0 0', fontSize: 14, color: '#52525b' }}>
            {data.summary}
          </p>
        )}
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: `repeat(${Math.max(1, (data.days || []).length)}, 1fr)`,
          gap: 10,
          marginTop: 22,
        }}
      >
        {(data.days || []).map((day) => (
          <div key={day.day}>
            <div
              style={{
                fontSize: 12,
                fontWeight: 700,
                letterSpacing: '0.05em',
                textTransform: 'uppercase',
                textAlign: 'center',
                padding: '7px 0',
                background: '#18181b',
                color: '#ffffff',
                borderRadius: 6,
              }}
            >
              {day.day.slice(0, 3)}
            </div>

            <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 6 }}>
              {(day.blocks || []).map((block, index) => (
                <div
                  key={index}
                  style={{
                    border: '1px solid #e6e6e9',
                    borderLeft: '3px solid #1d5c99',
                    borderRadius: 6,
                    padding: '7px 8px',
                    background: '#fafafa',
                    fontSize: 11.5,
                  }}
                >
                  <div style={{ color: '#8b8b94', fontSize: 10.5, marginBottom: 3 }}>
                    {block.start}–{block.end}
                  </div>
                  <div style={{ fontWeight: 600, lineHeight: 1.35 }}>
                    {block.activity}
                  </div>
                  {block.detail && (
                    <div style={{ color: '#52525b', marginTop: 3, lineHeight: 1.4 }}>
                      {block.detail}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {data.notes?.length ? (
        <div style={{ marginTop: 24, borderTop: '1px solid #e6e6e9', paddingTop: 14 }}>
          <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13, lineHeight: 1.7 }}>
            {data.notes.map((note, index) => (
              <li key={index}>{note}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  )
})

export default TimetableCard
