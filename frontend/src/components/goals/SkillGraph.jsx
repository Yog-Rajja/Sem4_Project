import { useEffect, useMemo, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import Button from '../ui/Button'
import Spinner from '../ui/Spinner'
import { useToast } from '../ui/Toast'
import { NetworkIcon, SparklesIcon } from '../ui/Icons'
import { computeLayout, trimSegment } from '../../lib/forceLayout'
import api, { errorMessage } from '../../lib/api'

const WIDTH = 680
const HEIGHT = 380
const NODE_RADIUS = 8

/** Colour a node by how much of its milestone is done. Reads CSS custom
    properties directly, so it tracks light/dark mode with no extra JS. */
function nodeColour(node) {
  if (node.complete) return 'var(--color-success)'
  if (node.progress > 0) return 'var(--color-brand-500)'
  return 'var(--color-line-strong)'
}

export default function SkillGraph({ goalId, onSelectMilestone }) {
  const toast = useToast()
  const [state, setState] = useState(null) // {generated, nodes, edges}
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [hovered, setHovered] = useState(null)

  useEffect(() => {
    let cancelled = false
    api
      .get(`/goals/${goalId}/skillmap/`)
      .then(({ data }) => !cancelled && setState(data))
      .catch(() => !cancelled && setState({ generated: false, nodes: [], edges: [] }))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [goalId])

  async function generate() {
    setGenerating(true)
    try {
      const { data } = await api.post(`/goals/${goalId}/skillmap/generate/`)
      setState(data)
    } catch (err) {
      toast.error(errorMessage(err, 'Could not build a skill map for this goal.'))
    } finally {
      setGenerating(false)
    }
  }

  const layout = useMemo(() => {
    if (!state?.nodes?.length) return {}
    return computeLayout(state.nodes, state.edges, { width: WIDTH, height: HEIGHT })
  }, [state])

  if (loading) {
    return (
      <div className="grid place-items-center py-10 text-brand-600">
        <Spinner size={18} />
      </div>
    )
  }

  if (!state?.generated) {
    return (
      <div className="flex flex-col items-center gap-3 px-6 py-10 text-center">
        <span className="grid h-11 w-11 place-items-center rounded-xl border border-line bg-surface-muted text-ink-muted">
          <NetworkIcon size={20} />
        </span>
        <div>
          <p className="text-sm font-semibold text-ink">No skill map yet</p>
          <p className="mt-1.5 max-w-sm text-[13px] leading-relaxed text-ink-muted">
            See how the topics in this roadmap depend on each other, and watch it
            fill in as you complete milestones.
          </p>
        </div>
        <Button onClick={generate} loading={generating}>
          {!generating && <SparklesIcon size={15} />}
          Generate skill map
        </Button>
      </div>
    )
  }

  const { nodes, edges } = state

  return (
    <div>
      <div className="mb-2 flex items-center justify-between px-1">
        <div className="flex items-center gap-4 text-[12px] text-ink-muted">
          <span className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full" style={{ background: 'var(--color-line-strong)' }} />
            Not started
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full" style={{ background: 'var(--color-brand-500)' }} />
            In progress
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full" style={{ background: 'var(--color-success)' }} />
            Done
          </span>
        </div>
        <Button variant="ghost" size="sm" onClick={generate} loading={generating}>
          {!generating && <SparklesIcon size={13} />}
          Regenerate
        </Button>
      </div>

      <div className="overflow-x-auto rounded-lg border border-line bg-surface-muted scrollbar-thin">
        <svg
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          width="100%"
          style={{ minWidth: 420, display: 'block' }}
          role="img"
          aria-label="Skill dependency graph"
        >
          <defs>
            <marker
              id="skillgraph-arrow"
              viewBox="0 0 10 10"
              refX="8"
              refY="5"
              markerWidth="7"
              markerHeight="7"
              orient="auto-start-reverse"
            >
              <path d="M0 0 L10 5 L0 10 Z" fill="var(--color-line-strong)" />
            </marker>
          </defs>

          <AnimatePresence>
            {edges.map((edge, index) => {
              const a = layout[edge.from]
              const b = layout[edge.to]
              if (!a || !b) return null
              const line = trimSegment(a, b, NODE_RADIUS + 2, NODE_RADIUS + 7)
              return (
                <motion.line
                  key={`${edge.from}-${edge.to}`}
                  x1={line.x1}
                  y1={line.y1}
                  x2={line.x2}
                  y2={line.y2}
                  stroke="var(--color-line-strong)"
                  strokeWidth="1.4"
                  markerEnd="url(#skillgraph-arrow)"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 0.8 }}
                  transition={{ delay: 0.15 + index * 0.012, duration: 0.25 }}
                />
              )
            })}
          </AnimatePresence>

          {nodes.map((node, index) => {
            const pos = layout[node.id]
            if (!pos) return null
            const isHovered = hovered === node.id
            return (
              <motion.g
                key={node.id}
                initial={{ opacity: 0, scale: 0.4 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: index * 0.02, type: 'spring', stiffness: 260, damping: 20 }}
                style={{ cursor: node.milestone_id ? 'pointer' : 'default' }}
                onMouseEnter={() => setHovered(node.id)}
                onMouseLeave={() => setHovered((current) => (current === node.id ? null : current))}
                onClick={() => node.milestone_id && onSelectMilestone?.(node.milestone_id)}
              >
                <title>
                  {node.label} — {node.milestone_title} ({node.progress}%)
                </title>
                {isHovered && (
                  <circle
                    cx={pos.x}
                    cy={pos.y}
                    r={NODE_RADIUS + 5}
                    fill="none"
                    stroke={nodeColour(node)}
                    strokeWidth="1.5"
                    opacity="0.4"
                  />
                )}
                <circle
                  cx={pos.x}
                  cy={pos.y}
                  r={NODE_RADIUS}
                  fill={nodeColour(node)}
                  stroke="var(--color-surface)"
                  strokeWidth="2"
                />
                <text
                  x={pos.x}
                  y={pos.y + NODE_RADIUS + 13}
                  textAnchor="middle"
                  fontSize="10.5"
                  fill="var(--color-ink-soft)"
                  style={{ fontFamily: 'inherit', pointerEvents: 'none' }}
                >
                  {node.label.length > 20 ? `${node.label.slice(0, 19)}…` : node.label}
                </text>
              </motion.g>
            )
          })}
        </svg>
      </div>
    </div>
  )
}
