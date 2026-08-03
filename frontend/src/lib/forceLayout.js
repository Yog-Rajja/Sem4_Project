/**
 * Minimal force-directed graph layout — no dependency, runs synchronously.
 *
 * Nodes start on a circle (deterministic, so re-renders don't jump around),
 * then a simple physics simulation runs for a fixed number of steps: nodes
 * repel each other, edges pull their endpoints together like springs, and a
 * weak centering force keeps the graph from drifting off-canvas. Good enough
 * for the graph sizes here (well under 20 nodes) and keeps the frontend free
 * of a graph-layout package, matching the rest of the app's preference for
 * small hand-rolled visuals (the countdown ring, the activity heatmap) over
 * new dependencies.
 */

const REPULSION = 2600
const SPRING_LENGTH = 108
const SPRING_STRENGTH = 0.02
const CENTERING = 0.006
const DAMPING = 0.82
const MIN_DISTANCE_SQ = 1

export function computeLayout(
  nodes,
  edges,
  { width = 640, height = 420, iterations = 240, padding = 44 } = {},
) {
  const cx = width / 2
  const cy = height / 2
  const radius = Math.min(width, height) / 2 - padding

  if (nodes.length === 0) return {}

  const positions = new Map()
  nodes.forEach((node, index) => {
    const angle = (index / nodes.length) * Math.PI * 2
    positions.set(node.id, {
      x: cx + Math.cos(angle) * radius,
      y: cy + Math.sin(angle) * radius,
      vx: 0,
      vy: 0,
    })
  })

  const edgeList = edges.filter((e) => positions.has(e.from) && positions.has(e.to))

  for (let step = 0; step < iterations; step++) {
    for (let i = 0; i < nodes.length; i++) {
      const a = positions.get(nodes[i].id)
      for (let j = i + 1; j < nodes.length; j++) {
        const b = positions.get(nodes[j].id)
        const dx = a.x - b.x
        const dy = a.y - b.y
        const distSq = Math.max(dx * dx + dy * dy, MIN_DISTANCE_SQ)
        const dist = Math.sqrt(distSq)
        const force = REPULSION / distSq
        const fx = (dx / dist) * force
        const fy = (dy / dist) * force
        a.vx += fx
        a.vy += fy
        b.vx -= fx
        b.vy -= fy
      }
    }

    for (const edge of edgeList) {
      const a = positions.get(edge.from)
      const b = positions.get(edge.to)
      const dx = b.x - a.x
      const dy = b.y - a.y
      const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1)
      const force = ((dist - SPRING_LENGTH) * SPRING_STRENGTH)
      const fx = (dx / dist) * force
      const fy = (dy / dist) * force
      a.vx += fx
      a.vy += fy
      b.vx -= fx
      b.vy -= fy
    }

    for (const node of nodes) {
      const p = positions.get(node.id)
      p.vx += (cx - p.x) * CENTERING
      p.vy += (cy - p.y) * CENTERING
      p.vx *= DAMPING
      p.vy *= DAMPING
      p.x += p.vx
      p.y += p.vy
    }
  }

  const out = {}
  for (const node of nodes) {
    const p = positions.get(node.id)
    out[node.id] = {
      x: Math.min(Math.max(p.x, padding), width - padding),
      y: Math.min(Math.max(p.y, padding), height - padding),
    }
  }
  return out
}

/** Shorten a line so it starts/ends at each node's circle boundary rather
    than its centre, so an arrowhead lands just outside the target node. */
export function trimSegment(a, b, startRadius, endRadius) {
  const dx = b.x - a.x
  const dy = b.y - a.y
  const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 0.001)
  const ux = dx / dist
  const uy = dy / dist
  return {
    x1: a.x + ux * startRadius,
    y1: a.y + uy * startRadius,
    x2: b.x - ux * endRadius,
    y2: b.y - uy * endRadius,
  }
}
