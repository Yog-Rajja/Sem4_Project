import {
    Area,
    AreaChart,
    CartesianGrid,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from 'recharts'
import { useChartTheme } from './chartTheme'
import useReducedMotion from '../../lib/useReducedMotion'

export default function CompletionTrendChart({ data }) {
    const theme = useChartTheme()
    const reducedMotion = useReducedMotion()
    const gradientId = 'completionGradient'

    return (
        <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 4, left: -18 }}>
                <defs>
                    <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor={theme.areaStroke} stopOpacity={0.35} />
                        <stop offset="95%" stopColor={theme.areaStroke} stopOpacity={0.02} />
                    </linearGradient>
                </defs>
                <CartesianGrid vertical={false} stroke={theme.grid} />
                <XAxis dataKey="label" interval={1} {...theme.axisProps} />
                <YAxis allowDecimals={false} {...theme.axisProps} axisLine={false} />
                <Tooltip
                    {...theme.tooltipStyle}
                    formatter={(value) => [
                        `${value} task${value === 1 ? '' : 's'} completed`,
                        'Completions',
                    ]}
                />
                <Area
                    type="monotone"
                    dataKey="count"
                    stroke={theme.areaStroke}
                    strokeWidth={2.5}
                    fill={`url(#${gradientId})`}
                    isAnimationActive={!reducedMotion}
                    dot={{ fill: theme.areaStroke, r: 3, strokeWidth: 0 }}
                    activeDot={{ r: 5, fill: theme.areaStroke, strokeWidth: 0 }}
                />
            </AreaChart>
        </ResponsiveContainer>
    )
}
