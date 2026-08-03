import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { useChartTheme } from './chartTheme'
import useReducedMotion from '../../lib/useReducedMotion'

/** Horizontal bars: one row per goal, sorted by the caller. Single series, so
    the card title names it and no legend is needed. */
export default function GoalProgressChart({ data }) {
  const theme = useChartTheme()
  const reducedMotion = useReducedMotion()

  const rows = data.map((goal) => ({
    name: goal.title.length > 28 ? `${goal.title.slice(0, 27)}…` : goal.title,
    progress: goal.progress,
    completed: goal.completed,
    total: goal.total,
  }))

  return (
    <ResponsiveContainer width="100%" height={Math.max(160, rows.length * 44 + 28)}>
      <BarChart
        data={rows}
        layout="vertical"
        margin={{ top: 4, right: 44, bottom: 4, left: 4 }}
        barCategoryGap="22%"
      >
        <CartesianGrid horizontal={false} stroke={theme.grid} />
        <XAxis type="number" domain={[0, 100]} unit="%" {...theme.axisProps} />
        <YAxis
          type="category"
          dataKey="name"
          width={140}
          {...theme.axisProps}
          axisLine={false}
          tick={{ fill: theme.axis, fontSize: 12 }}
        />
        <Tooltip
          {...theme.tooltipStyle}
          formatter={(value, _key, item) => [
            `${value}% · ${item.payload.completed}/${item.payload.total} tasks`,
            'Progress',
          ]}
        />
        <Bar
          dataKey="progress"
          fill={theme.series}
          radius={[0, 4, 4, 0]}
          maxBarSize={18}
          isAnimationActive={!reducedMotion}
        >
          <LabelList
            dataKey="progress"
            position="right"
            formatter={(value) => `${value}%`}
            style={{ fill: theme.axis, fontSize: 11.5, fontWeight: 600 }}
          />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
