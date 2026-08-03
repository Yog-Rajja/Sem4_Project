import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { useChartTheme } from './chartTheme'
import useReducedMotion from '../../lib/useReducedMotion'

/** Tasks falling due on each of the next 14 days — single series over time. */
export default function WorkloadChart({ data }) {
  const theme = useChartTheme()
  const reducedMotion = useReducedMotion()

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart
        data={data}
        margin={{ top: 8, right: 8, bottom: 4, left: -18 }}
        barCategoryGap="26%"
      >
        <CartesianGrid vertical={false} stroke={theme.grid} />
        <XAxis dataKey="label" interval={1} {...theme.axisProps} />
        <YAxis allowDecimals={false} {...theme.axisProps} axisLine={false} />
        <Tooltip
          {...theme.tooltipStyle}
          formatter={(value) => [
            `${value} task${value === 1 ? '' : 's'} due`,
            'Workload',
          ]}
        />
        <Bar
          dataKey="count"
          fill={theme.series}
          radius={[4, 4, 0, 0]}
          maxBarSize={26}
          isAnimationActive={!reducedMotion}
        />
      </BarChart>
    </ResponsiveContainer>
  )
}
