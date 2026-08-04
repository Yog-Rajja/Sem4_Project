import { useMemo } from 'react'
import { useTheme } from '../../context/ThemeContext'

/**
 * Chart chrome, mapped from the app's design tokens.
 *
 * Every chart here is single-series, so identity never rests on colour: one
 * brand hue carries magnitude and the chrome stays recessive.
 *
 * Dark is a *selected* step, not an inverted one. Both series colours were
 * validated against the surface they actually render on (#ffffff / #16161a)
 * for lightness band, chroma floor and contrast.
 */
const LIGHT = {
  series: '#1d5c99',
  seriesSoft: '#d8e7f5',
  grid: '#e6e6e9',
  axis: '#8b8b94',
  ink: '#18181b',
  surface: '#ffffff',
  border: '#e6e6e9',
  cursor: 'rgba(29,92,153,0.06)',
  pieColors: ['#61E8B2', '#5AC8FA', '#9B6DFF'],
  areaStroke: '#FF6B6B',
  areaFill: 'rgba(255,107,107,0.15)',
}

const DARK = {
  series: '#4a90d9',
  seriesSoft: '#1c3350',
  grid: '#27272e',
  axis: '#85858f',
  ink: '#f4f4f5',
  surface: '#16161a',
  border: '#27272e',
  cursor: 'rgba(74,144,217,0.10)',
  pieColors: ['#61E8B2', '#5AC8FA', '#9B6DFF'],
  areaStroke: '#FF6B6B',
  areaFill: 'rgba(255,107,107,0.25)',
}

export function useChartTheme() {
  const { isDark } = useTheme()

  return useMemo(() => {
    const palette = isDark ? DARK : LIGHT
    return {
      ...palette,
      axisProps: {
        stroke: palette.grid,
        tick: { fill: palette.axis, fontSize: 11.5 },
        tickLine: false,
        axisLine: { stroke: palette.grid },
      },
      tooltipStyle: {
        contentStyle: {
          borderRadius: 10,
          border: `1px solid ${palette.border}`,
          background: palette.surface,
          boxShadow: '0 10px 32px -8px rgb(16 24 40 / 0.18)',
          fontSize: 12.5,
          padding: '8px 10px',
          color: palette.ink,
        },
        labelStyle: { color: palette.ink, fontWeight: 600, marginBottom: 2 },
        itemStyle: { color: palette.ink },
        cursor: { fill: palette.cursor },
      },
    }
  }, [isDark])
}
