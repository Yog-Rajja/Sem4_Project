import Button from './Button'
import Modal from './Modal'

export default function ConfirmDialog({
  open,
  onClose,
  onConfirm,
  title = 'Are you sure?',
  message,
  confirmLabel = 'Delete',
  loading = false,
  tone = 'danger',
}) {
  return (
    <Modal
      open={open}
      onClose={onClose}
      title={title}
      size="sm"
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          <Button variant={tone} onClick={onConfirm} loading={loading}>
            {confirmLabel}
          </Button>
        </>
      }
    >
      <p className="text-sm leading-relaxed text-ink-soft">{message}</p>
    </Modal>
  )
}
