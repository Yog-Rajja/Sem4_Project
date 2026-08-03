/**
 * Inline icon set. Kept local rather than pulling an icon package so the
 * bundle stays small and the app renders with no network dependency.
 * Every icon inherits `currentColor` and sizes from the `size` prop.
 */

function Svg({ size = 18, children, ...rest }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      {...rest}
    >
      {children}
    </svg>
  )
}

export const HomeIcon = (p) => (
  <Svg {...p}>
    <path d="M3 10.5 12 3l9 7.5" />
    <path d="M5 9.5V21h14V9.5" />
    <path d="M9.5 21v-6h5v6" />
  </Svg>
)

export const TargetIcon = (p) => (
  <Svg {...p}>
    <circle cx="12" cy="12" r="8.5" />
    <circle cx="12" cy="12" r="4.5" />
    <circle cx="12" cy="12" r="1" fill="currentColor" />
  </Svg>
)

export const CheckSquareIcon = (p) => (
  <Svg {...p}>
    <path d="M8.5 12.5 11 15l4.5-5" />
    <rect x="3.5" y="3.5" width="17" height="17" rx="4" />
  </Svg>
)

export const CalendarIcon = (p) => (
  <Svg {...p}>
    <rect x="3.5" y="5" width="17" height="15.5" rx="3" />
    <path d="M3.5 9.5h17M8 3.5V6M16 3.5V6" />
  </Svg>
)

export const ChartIcon = (p) => (
  <Svg {...p}>
    <path d="M4 20V4" />
    <path d="M4 20h16" />
    <path d="M8 20v-6M12.5 20V8M17 20v-9" />
  </Svg>
)

export const FolderIcon = (p) => (
  <Svg {...p}>
    <path d="M3.5 7.5a2 2 0 0 1 2-2h3.4a2 2 0 0 1 1.5.7l1.1 1.3h7a2 2 0 0 1 2 2v8.5a2 2 0 0 1-2 2h-13a2 2 0 0 1-2-2z" />
  </Svg>
)

export const PlusIcon = (p) => (
  <Svg {...p}>
    <path d="M12 5v14M5 12h14" />
  </Svg>
)

export const TrashIcon = (p) => (
  <Svg {...p}>
    <path d="M4 7h16M9.5 7V5.5a1.5 1.5 0 0 1 1.5-1.5h2a1.5 1.5 0 0 1 1.5 1.5V7" />
    <path d="M6.5 7l.8 12a2 2 0 0 0 2 1.9h5.4a2 2 0 0 0 2-1.9l.8-12" />
  </Svg>
)

export const PencilIcon = (p) => (
  <Svg {...p}>
    <path d="M4 20h4l10.5-10.5a2.1 2.1 0 0 0-3-3L5 17v3z" />
  </Svg>
)

export const ChevronDownIcon = (p) => (
  <Svg {...p}>
    <path d="m6 9.5 6 6 6-6" />
  </Svg>
)

export const ChevronRightIcon = (p) => (
  <Svg {...p}>
    <path d="m9.5 6 6 6-6 6" />
  </Svg>
)

export const ArrowUpIcon = (p) => (
  <Svg {...p}>
    <path d="M12 19V5M6 11l6-6 6 6" />
  </Svg>
)

export const ArrowDownIcon = (p) => (
  <Svg {...p}>
    <path d="M12 5v14M6 13l6 6 6-6" />
  </Svg>
)

export const SparklesIcon = (p) => (
  <Svg {...p}>
    <path d="M12 3.5 13.6 8 18 9.5 13.6 11 12 15.5 10.4 11 6 9.5 10.4 8z" />
    <path d="M18.5 15.5l.7 2 2 .7-2 .7-.7 2-.7-2-2-.7 2-.7z" />
  </Svg>
)

export const PlayIcon = (p) => (
  <Svg {...p}>
    <path d="M9 7.5v9l7-4.5z" fill="currentColor" />
    <rect x="2.5" y="4.5" width="19" height="15" rx="4" />
  </Svg>
)

export const SearchIcon = (p) => (
  <Svg {...p}>
    <circle cx="11" cy="11" r="6.5" />
    <path d="m16 16 4.5 4.5" />
  </Svg>
)

export const LogoutIcon = (p) => (
  <Svg {...p}>
    <path d="M14 4.5h3.5a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H14" />
    <path d="M10 8.5 6.5 12 10 15.5M6.5 12H15" />
  </Svg>
)

export const MenuIcon = (p) => (
  <Svg {...p}>
    <path d="M4 7h16M4 12h16M4 17h16" />
  </Svg>
)

export const XIcon = (p) => (
  <Svg {...p}>
    <path d="M6 6l12 12M18 6 6 18" />
  </Svg>
)

export const ClockIcon = (p) => (
  <Svg {...p}>
    <circle cx="12" cy="12" r="8.5" />
    <path d="M12 7.5V12l3 2" />
  </Svg>
)

export const AlertIcon = (p) => (
  <Svg {...p}>
    <path d="M12 4.5 21 19.5H3z" />
    <path d="M12 10v4M12 17h.01" />
  </Svg>
)

export const ExternalIcon = (p) => (
  <Svg {...p}>
    <path d="M14 4.5h5.5V10" />
    <path d="M19.5 4.5 12 12" />
    <path d="M18 14v5.5H4.5V6H10" />
  </Svg>
)

export const UploadIcon = (p) => (
  <Svg {...p}>
    <path d="M12 16V4.5M7.5 9 12 4.5 16.5 9" />
    <path d="M4.5 15.5v2.5a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2v-2.5" />
  </Svg>
)

export const DownloadIcon = (p) => (
  <Svg {...p}>
    <path d="M12 4.5V16M7.5 11.5 12 16l4.5-4.5" />
    <path d="M4.5 15.5v2.5a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2v-2.5" />
  </Svg>
)

export const FileIcon = (p) => (
  <Svg {...p}>
    <path d="M13.5 3.5H7a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V9z" />
    <path d="M13.5 3.5V9H19" />
  </Svg>
)

export const SunIcon = (p) => (
  <Svg {...p}>
    <circle cx="12" cy="12" r="4" />
    <path d="M12 2.5v2M12 19.5v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M2.5 12h2M19.5 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4" />
  </Svg>
)

export const MoonIcon = (p) => (
  <Svg {...p}>
    <path d="M20 14.5A8.2 8.2 0 0 1 9.5 4 8.5 8.5 0 1 0 20 14.5z" />
  </Svg>
)

export const TimerIcon = (p) => (
  <Svg {...p}>
    <circle cx="12" cy="13.5" r="7.5" />
    <path d="M12 10v3.5l2 1.5M9.5 2.5h5" />
  </Svg>
)

export const FlameIcon = (p) => (
  <Svg {...p}>
    <path d="M12 3s4.5 3.6 4.5 8a4.5 4.5 0 0 1-9 0c0-1.3.5-2.4 1-3 .2 1 .8 1.8 1.6 1.8 1.2 0 1.4-1.5 1.4-3 0-1.6.5-3 .5-3.8z" />
    <path d="M7 13.5A5 5 0 0 0 12 21a5 5 0 0 0 5-5" />
  </Svg>
)

export const BellIcon = (p) => (
  <Svg {...p}>
    <path d="M18 9a6 6 0 1 0-12 0c0 5-2 6.5-2 6.5h16S18 14 18 9z" />
    <path d="M10.3 19a2 2 0 0 0 3.4 0" />
  </Svg>
)

export const WandIcon = (p) => (
  <Svg {...p}>
    <path d="M4 20 15 9" />
    <path d="M14.5 4.5 15.5 7l2.5 1-2.5 1-1 2.5-1-2.5L11 8l2.5-1z" />
    <path d="M19 14.5l.6 1.6 1.6.6-1.6.6-.6 1.6-.6-1.6-1.6-.6 1.6-.6z" />
  </Svg>
)

export const PauseIcon = (p) => (
  <Svg {...p}>
    <path d="M9.5 5.5v13M14.5 5.5v13" />
  </Svg>
)

export const StopIcon = (p) => (
  <Svg {...p}>
    <rect x="6" y="6" width="12" height="12" rx="2.5" />
  </Svg>
)

export const CommandIcon = (p) => (
  <Svg {...p}>
    <path d="M8.5 6.5a2 2 0 1 0-2 2h11a2 2 0 1 0-2-2v11a2 2 0 1 0 2-2h-11a2 2 0 1 0 2 2z" />
  </Svg>
)

export const CompassIcon = (p) => (
  <Svg {...p}>
    <circle cx="12" cy="12" r="9" />
    <path d="M15.5 8.5 13.5 14 8.5 15.5 10.5 10z" fill="currentColor" stroke="none" />
  </Svg>
)
