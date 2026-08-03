import { useEffect, useState } from 'react'

/**
 * Tracks the user's reduced-motion preference.
 *
 * CSS transitions are already handled in index.css, but Recharts animates in
 * JavaScript — without this, a reduced-motion user would still get bars
 * sweeping across the screen, and the data would only appear once the
 * animation finished.
 */
export default function useReducedMotion() {
  const [reduced, setReduced] = useState(
    () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false,
  )

  useEffect(() => {
    const media = window.matchMedia?.('(prefers-reduced-motion: reduce)')
    if (!media) return
    const onChange = (event) => setReduced(event.matches)
    media.addEventListener('change', onChange)
    return () => media.removeEventListener('change', onChange)
  }, [])

  return reduced
}
