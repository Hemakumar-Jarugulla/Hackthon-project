import { AlertTriangle } from 'lucide-react'
import { Button } from '../common/Button'
import { Modal } from './Modal'

/**
 * Confirmation modal used before archiving, deleting, or resolving records.
 */
export function ConfirmDialog({
  isOpen,
  onClose,
  onConfirm,
  title = 'Confirm Action',
  message = 'Are you sure you want to proceed? This action can affect downstream reporting.',
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  variant = 'danger',
  loading = false,
}) {
  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={title}
      size="sm"
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={loading}>
            {cancelLabel}
          </Button>
          <Button variant={variant} onClick={onConfirm} loading={loading}>
            {confirmLabel}
          </Button>
        </>
      }
    >
      <div className="flex items-start gap-3.5">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-amber-50 text-amber-600 border border-amber-200">
          <AlertTriangle className="h-5 w-5" />
        </div>
        <p className="text-sm text-slate-600 leading-relaxed">{message}</p>
      </div>
    </Modal>
  )
}

