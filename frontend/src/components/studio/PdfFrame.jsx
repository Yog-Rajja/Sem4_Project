import { PDFDownloadLink, PDFViewer } from '@react-pdf/renderer'
import cn from '../../lib/cn'
import Spinner from '../ui/Spinner'
import { DownloadIcon } from '../ui/Icons'
import CoverLetterDocument from './pdf/CoverLetterDocument'
import ProjectReportDocument from './pdf/ProjectReportDocument'
import ResumeDocument from './pdf/ResumeDocument'

const DOCUMENTS = {
  resume: ResumeDocument,
  cover_letter: CoverLetterDocument,
  project_report: ProjectReportDocument,
}

/**
 * The preview *is* the PDF — the same renderer produces what you see and what
 * you download, so the two can never drift apart. Text stays selectable, which
 * is what lets an ATS actually read a résumé.
 */
export default function PdfFrame({ artifact, filename }) {
  const DocumentComponent = DOCUMENTS[artifact.kind]
  if (!DocumentComponent) return null

  const element = <DocumentComponent data={artifact.data} />

  return (
    <div>
      <div className="mb-3 flex items-center justify-between gap-3">
        <p className="text-[12.5px] text-ink-muted">
          Selectable text, not an image, so it is readable by applicant tracking systems.
        </p>
        <PDFDownloadLink document={element} fileName={filename}>
          {({ loading }) => (
            <span
              className={cn(
                'inline-flex h-9.5 items-center gap-2 rounded-lg bg-brand-600 px-4',
                'text-sm font-medium text-white transition-colors hover:bg-brand-700',
                loading && 'pointer-events-none opacity-60',
              )}
            >
              {loading ? <Spinner size={14} /> : <DownloadIcon size={15} />}
              Download PDF
            </span>
          )}
        </PDFDownloadLink>
      </div>

      <div className="overflow-hidden rounded-card border border-line bg-surface-muted">
        <PDFViewer
          showToolbar={false}
          style={{ width: '100%', height: '72vh', border: 'none' }}
        >
          {element}
        </PDFViewer>
      </div>
    </div>
  )
}
