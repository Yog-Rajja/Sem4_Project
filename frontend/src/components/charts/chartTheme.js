/**
 * Chart chrome, mapped from the app's design tokens.
 *
 * Every chart in this app is single-series, so identity never rests on colour:
 * one validated brand hue carries magnitude, and the chrome stays recessive.
 * (Validated against the #ffffff card surface: lightness band, chroma floor and
 * contrast all pass.)
 */
export const SERIES = '#4f46e5' // brand-600
export const SERIES_SOFT = '#e0e7ff' // brand-100, for the unfilled track
export const GRID = '#e6e6e9' // line
export const AXIS = '#8b8b94' // ink-muted
export const INK = '#18181b'

export const axisProps = {
  stroke: GRID,
  tick: { fill: AXIS, fontSize: 11.5 },
  tickLine: false,
  axisLine: { stroke: GRID },
}

export const tooltipStyle = {
  contentStyle: {
    borderRadius: 10,
    border: '1px solid #e6e6e9',
    boxShadow: '0 10px 32px -8px rgb(16 24 40 / 0.18)',
    fontSize: 12.5,
    padding: '8px 10px',
  },
  labelStyle: { color: INK, fontWeight: 600, marginBottom: 2 },
  cursor: { fill: 'rgba(99,102,241,0.06)' },
}
