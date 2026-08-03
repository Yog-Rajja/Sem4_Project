import { useState } from 'react'
import { motion } from 'framer-motion'
import Button from '../ui/Button'
import Modal from '../ui/Modal'
import Spinner from '../ui/Spinner'
import { useToast } from '../ui/Toast'
import { TrophyIcon } from '../ui/Icons'
import ArtifactPreview from '../studio/ArtifactPreview'
import api, { errorMessage } from '../../lib/api'

/**
 * Shown once every task in a goal is done. The certificate's numbers are all
 * computed server-side from the goal's real history — the only thing an AI
 * ever writes is the one-line tagline, and even that falls back to a canned
 * line if every model is unavailable, so this never fails to appear just
 * because a daily quota is spent.
 */
export default function CertificateBanner({ goal }) {
  const toast = useToast()
  const [open, setOpen] = useState(false)
  const [artifact, setArtifact] = useState(null)
  const [loading, setLoading] = useState(false)

  async function claim() {
    setOpen(true)
    setLoading(true)
    try {
      const { data } = await api.post(`/goals/${goal.id}/certificate/`)
      setArtifact(data)
    } catch (err) {
      toast.error(errorMessage(err, 'Could not generate your certificate.'))
      setOpen(false)
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.24 }}
        className="mb-4 flex flex-wrap items-center gap-3 rounded-card border border-brand-100 bg-brand-50 px-4 py-3.5"
      >
        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-brand-600 text-white">
          <TrophyIcon size={19} />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-[13.5px] font-semibold text-brand-700">
            Every task in this goal is done.
          </p>
          <p className="mt-0.5 text-[12.5px] text-brand-700/75">
            Claim a certificate — a downloadable record of what you finished.
          </p>
        </div>
        <Button onClick={claim} loading={loading && open}>
          {!loading && <TrophyIcon size={15} />}
          Claim certificate
        </Button>
      </motion.div>

      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title="Your certificate"
        size="lg"
        footer={<Button onClick={() => setOpen(false)}>Done</Button>}
      >
        {loading ? (
          <div className="grid place-items-center py-16 text-brand-600">
            <Spinner size={22} />
          </div>
        ) : (
          artifact && <ArtifactPreview artifact={artifact} />
        )}
      </Modal>
    </>
  )
}
