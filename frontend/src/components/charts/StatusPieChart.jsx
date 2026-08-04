import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { useChartTheme } from './chartTheme'

export default function StatusPieChart({ data }) {
    const theme = useChartTheme()
    const total = data.reduce((s, d) => s + d.value, 0)

    if (total === 0) return null

    return (
        <ResponsiveContainer width="100%" height={260}>
            <PieChart>
                <Pie
                    data={data}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={95}
                    paddingAngle={3}
                    dataKey="value"
                    stroke="none"
                    animationBegin={0}
                    animationDuration={800}
                >
                    {data.map((entry, i) => (
                        <Cell key={entry.name} fill={theme.pieColors[i % theme.pieColors.length]} />
                    ))}
                </Pie>
                <Tooltip
                    {...theme.tooltipStyle}
                    formatter={(value, name) => [
                        `${value} task${value === 1 ? '' : 's'} (${total ? Math.round((value / total) * 100) : 0}%)`,
                        name,
                    ]}
                />
            </PieChart>
        </ResponsiveContainer>
    )
}
