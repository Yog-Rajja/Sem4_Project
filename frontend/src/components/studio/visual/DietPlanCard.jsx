import { forwardRef } from 'react'

/**
 * Diet plan laid out for export as an image, so it stays legible when it ends
 * up in a phone gallery or a WhatsApp thread.
 *
 * Colours are inlined rather than themed: the exported PNG must look the same
 * regardless of whether the app was in dark mode when it was generated.
 */
const DietPlanCard = forwardRef(function DietPlanCard({ data }, ref) {
  const macros = data.macros || {}

  return (
    <div
      ref={ref}
      style={{
        width: 900,
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
        {data.goal_summary && (
          <p style={{ margin: '8px 0 0', fontSize: 14, color: '#52525b' }}>
            {data.goal_summary}
          </p>
        )}
      </div>

      <div style={{ display: 'flex', gap: 28, margin: '18px 0 22px' }}>
        {[
          ['Daily target', `${data.daily_calories} kcal`],
          ['Protein', `${macros.protein_g} g`],
          ['Carbs', `${macros.carbs_g} g`],
          ['Fat', `${macros.fat_g} g`],
        ].map(([label, value]) => (
          <div key={label}>
            <div
              style={{
                fontSize: 11,
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
                color: '#8b8b94',
              }}
            >
              {label}
            </div>
            <div style={{ fontSize: 19, fontWeight: 600, marginTop: 3 }}>{value}</div>
          </div>
        ))}
      </div>

      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <tbody>
          {(data.days || []).map((day) => (
            <tr key={day.day} style={{ borderTop: '1px solid #e6e6e9' }}>
              <td
                style={{
                  width: 104,
                  verticalAlign: 'top',
                  padding: '13px 12px 13px 0',
                  fontWeight: 600,
                }}
              >
                {day.day}
              </td>
              <td style={{ padding: '13px 0' }}>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
                  {(day.meals || []).map((meal, index) => (
                    <div
                      key={index}
                      style={{
                        flex: '1 1 180px',
                        minWidth: 165,
                        border: '1px solid #e6e6e9',
                        borderRadius: 8,
                        padding: '9px 11px',
                        background: '#fafafa',
                      }}
                    >
                      <div
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          fontSize: 11,
                          color: '#8b8b94',
                          marginBottom: 5,
                        }}
                      >
                        <span style={{ fontWeight: 600, color: '#1d5c99' }}>
                          {meal.slot}
                        </span>
                        {meal.calories ? <span>{meal.calories} kcal</span> : null}
                      </div>
                      <div style={{ lineHeight: 1.55 }}>
                        {(meal.items || []).join(' · ')}
                      </div>
                    </div>
                  ))}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {data.notes?.length ? (
        <div style={{ marginTop: 22, borderTop: '1px solid #e6e6e9', paddingTop: 14 }}>
          <div
            style={{
              fontSize: 11,
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              color: '#8b8b94',
              marginBottom: 7,
            }}
          >
            Notes
          </div>
          <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13, lineHeight: 1.7 }}>
            {data.notes.map((note, index) => (
              <li key={index}>{note}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <p style={{ marginTop: 20, fontSize: 11, color: '#8b8b94' }}>
        General guidance only, not medical or dietary advice.
      </p>
    </div>
  )
})

export default DietPlanCard
