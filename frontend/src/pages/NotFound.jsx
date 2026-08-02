import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="grid min-h-screen place-items-center bg-canvas px-6">
      <div className="text-center">
        <p className="text-[13px] font-semibold tracking-wide text-brand-600 uppercase">
          404
        </p>
        <h1 className="mt-2 text-2xl font-semibold tracking-[-0.02em] text-ink">
          We couldn't find that page
        </h1>
        <p className="mt-2 text-[13.5px] text-ink-muted">
          The link may be out of date, or the page may have moved.
        </p>
        <Link
          to="/dashboard"
          className="mt-6 inline-flex h-9.5 items-center rounded-lg bg-brand-600 px-4 text-sm font-medium text-white transition-colors hover:bg-brand-700"
        >
          Back to dashboard
        </Link>
      </div>
    </div>
  )
}
