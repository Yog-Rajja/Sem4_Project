import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { GRID, SERIES, axisProps, tooltipStyle } from './chartTheme'

/** Tasks falling due on each of the next 14 days — single series over time. */
export default function WorkloadChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart
        data={data}
        margin={{ top: 8, right: 8, bottom: 4, left: -18 }}
        barCategoryGap="26%"
      >
        <CartesianGrid vertical={false} stroke={GRID} />
        <XAxis dataKey="label" interval={1} {...axisProps} />
        <YAxis allowDecimals={false} {...axisProps} axisLine={false} />
        <Tooltip
          {...tooltipStyle}
          formatter={(value) => [
            `${value} task${value === 1 ? '' : 's'} due`,
            'Workload',
          ]}
        />
        <Bar dataKey="count" fill={SERIES} radius={[4, 4, 0, 0]} maxBarSize={26} />
      </BarChart>
    </ResponsiveContainer>
  )
}
