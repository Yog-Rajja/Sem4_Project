import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { AXIS, GRID, SERIES, axisProps, tooltipStyle } from './chartTheme'

/** Horizontal bars: one row per goal, sorted by the caller. Single series, so
    the card title names it and no legend is needed. */
export default function GoalProgressChart({ data }) {
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
        <CartesianGrid horizontal={false} stroke={GRID} />
        <XAxis type="number" domain={[0, 100]} unit="%" {...axisProps} />
        <YAxis
          type="category"
          dataKey="name"
          width={140}
          {...axisProps}
          axisLine={false}
          tick={{ fill: AXIS, fontSize: 12 }}
        />
        <Tooltip
          {...tooltipStyle}
          formatter={(value, _key, item) => [
            `${value}% · ${item.payload.completed}/${item.payload.total} tasks`,
            'Progress',
          ]}
        />
        <Bar dataKey="progress" radius={[0, 4, 4, 0]} maxBarSize={18}>
          {rows.map((row) => (
            <Cell key={row.name} fill={SERIES} />
          ))}
          <LabelList
            dataKey="progress"
            position="right"
            formatter={(value) => `${value}%`}
            style={{ fill: AXIS, fontSize: 11.5, fontWeight: 600 }}
          />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
