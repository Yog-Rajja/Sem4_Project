import { Suspense, lazy, useCallback, useRef, useState } from 'react'
import Button from '../ui/Button'
import Spinner from '../ui/Spinner'
import { useToast } from '../ui/Toast'
import { DownloadIcon } from '../ui/Icons'
import CertificateCard from './visual/CertificateCard'
import DietPlanCard from './visual/DietPlanCard'
import InvitationCard from './visual/InvitationCard'
import TimetableCard from './visual/TimetableCard'

// The PDF engine is ~400 kB and only loads once a text document is opened.
const PdfFrame = lazy(() => import('./PdfFrame'))

const VISUAL_RENDERERS = {
  diet_plan: DietPlanCard,
  timetable: TimetableCard,
  invitation: InvitationCard,
  certificate: CertificateCard,
}

function slugify(value) {
  return (
    String(value)
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '')
      .slice(0, 60) || 'document'
  )
}

/** Renders a generated document and gives it a one-click download. */
export default function ArtifactPreview({ artifact }) {
  const toast = useToast()
  const cardRef = useRef(null)
  const [exporting, setExporting] = useState(false)

  const Visual = VISUAL_RENDERERS[artifact.kind]

  const downloadPng = useCallback(async () => {
    if (!cardRef.current) return
    setExporting(true)
    try {
      // Imported lazily so the export library isn't in the initial bundle.
      const { toPng } = await import('html-to-image')
      const dataUrl = await toPng(cardRef.current, {
        pixelRatio: 2,
        backgroundColor: '#ffffff',
        cacheBust: true,
      })
      const link = document.createElement('a')
      link.download = `${slugify(artifact.title)}.png`
      link.href = dataUrl
      link.click()
      toast.success('Image downloaded.')
    } catch {
      toast.error('Could not export that image. Try again.')
    } finally {
      setExporting(false)
    }
  }, [artifact.title, toast])

  // An image artifact is already a raster file; there is nothing to render.
  // Placed after the hooks above so they run in the same order every time.
  if (artifact.kind === 'image') {
    return (
      <div>
        <div className="mb-3 flex justify-end">
          <a
            href={artifact.image_url}
            download={`${slugify(artifact.title)}.png`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex h-9.5 items-center gap-2 rounded-lg bg-brand-600 px-4 text-sm font-medium text-white transition-colors hover:bg-brand-700"
          >
            <DownloadIcon size={15} />
            Download image
          </a>
        </div>
        <div className="grid place-items-center rounded-card border border-line bg-surface-muted p-4">
          <img
            src={artifact.image_url}
            alt={artifact.data?.alt_text || artifact.title}
            className="max-h-[70vh] w-auto rounded-lg shadow-card"
          />
        </div>
        {artifact.data?.alt_text && (
          <p className="mt-2 text-[12.5px] text-ink-muted">{artifact.data.alt_text}</p>
        )}
      </div>
    )
  }

  if (Visual) {
    return (
      <div>
        <div className="mb-3 flex justify-end">
          <Button onClick={downloadPng} loading={exporting}>
            {!exporting && <DownloadIcon size={15} />}
            Download PNG
          </Button>
        </div>

        {/* The card renders at its true export width and is scaled down to
            fit, so what you see is exactly what gets saved. */}
        <div className="overflow-x-auto rounded-card border border-line bg-surface-muted p-4 scrollbar-thin">
          <div className="origin-top-left scale-[0.62] sm:scale-75 lg:scale-100">
            <div className="w-fit shadow-card">
              <Visual ref={cardRef} data={artifact.data} />
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <Suspense
      fallback={
        <div className="grid h-[70vh] place-items-center rounded-card border border-line bg-surface-muted text-brand-600">
          <Spinner size={22} />
        </div>
      }
    >
      <PdfFrame artifact={artifact} filename={`${slugify(artifact.title)}.pdf`} />
    </Suspense>
  )
}
