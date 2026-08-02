import { motion } from 'framer-motion'
import Button from '../ui/Button'
import Spinner from '../ui/Spinner'
import { ExternalIcon, PlayIcon, SearchIcon } from '../ui/Icons'

function VideoCard({ resource }) {
  return (
    <motion.a
      layout
      href={resource.url}
      target="_blank"
      rel="noopener noreferrer"
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className="group flex gap-2.5 rounded-lg border border-line bg-surface p-2 transition-colors hover:border-brand-200 hover:bg-brand-50/40"
    >
      <div className="relative h-13 w-22 shrink-0 overflow-hidden rounded-md bg-line">
        {resource.thumbnail_url ? (
          <img
            src={resource.thumbnail_url}
            alt=""
            loading="lazy"
            className="h-full w-full object-cover"
          />
        ) : (
          <span className="grid h-full w-full place-items-center text-ink-muted">
            <PlayIcon size={16} />
          </span>
        )}
        <span className="absolute inset-0 grid place-items-center bg-ink/0 text-white/0 transition-all group-hover:bg-ink/35 group-hover:text-white">
          <PlayIcon size={18} />
        </span>
      </div>

      <div className="min-w-0 flex-1 py-0.5">
        <p className="line-clamp-2 text-[12.5px] leading-snug font-medium text-ink">
          {resource.title}
        </p>
        {resource.channel_title && (
          <p className="mt-1 truncate text-[11.5px] text-ink-muted">
            {resource.channel_title}
          </p>
        )}
      </div>
    </motion.a>
  )
}

export default function ResourceList({
  resources = [],
  loading = false,
  warning,
  onFetch,
  searchQuery,
}) {
  const videos = resources.filter((r) => r.source === 'youtube')
  const search = resources.find((r) => r.source === 'google_search')

  if (loading) {
    return (
      <div className="flex items-center gap-2 px-1 py-3 text-[13px] text-ink-muted">
        <Spinner size={14} />
        Finding learning resources…
      </div>
    )
  }

  if (!resources.length) {
    return (
      <div className="flex flex-wrap items-center gap-2 px-1 py-2">
        <Button variant="secondary" size="sm" onClick={onFetch}>
          <SearchIcon size={14} />
          Find resources
        </Button>
        {searchQuery && (
          <span className="text-[12px] text-ink-muted">
            Searches for “{searchQuery}”
          </span>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-2 px-1 pb-1">
      <div className="flex items-center justify-between gap-3">
        <p className="text-[11.5px] font-semibold tracking-wide text-ink-muted uppercase">
          Learn this
        </p>
        <button
          type="button"
          onClick={onFetch}
          className="text-[12px] font-medium text-ink-muted transition-colors hover:text-brand-600"
        >
          Refresh
        </button>
      </div>

      {warning && <p className="text-[12px] text-warning">{warning}</p>}

      {videos.length > 0 && (
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {videos.map((resource) => (
            <VideoCard key={resource.id} resource={resource} />
          ))}
        </div>
      )}

      {search && (
        <a
          href={search.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 text-[12.5px] font-medium text-brand-600 transition-colors hover:text-brand-700"
        >
          <SearchIcon size={13} />
          {search.title}
          <ExternalIcon size={12} />
        </a>
      )}
    </div>
  )
}
