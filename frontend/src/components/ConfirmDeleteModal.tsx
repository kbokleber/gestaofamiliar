import { Trash2 } from 'lucide-react'
import Modal from './Modal'
import Button from './Button'

interface ConfirmDeleteModalProps {
  isOpen: boolean
  onClose: () => void
  title?: string
  message: React.ReactNode
  confirmLabel?: string
  onConfirm: () => void
  isLoading?: boolean
  /** Texto de aviso em vermelho (ex: "Esta ação não pode ser desfeita.") */
  warningText?: React.ReactNode
}

export default function ConfirmDeleteModal({
  isOpen,
  onClose,
  title = 'Confirmar exclusão',
  message,
  confirmLabel = 'Excluir',
  onConfirm,
  isLoading = false,
  warningText
}: ConfirmDeleteModalProps) {
  const handleConfirm = () => {
    onConfirm()
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={title}>
      <div className="space-y-5">
        <div className="flex gap-4">
          <div className="flex-shrink-0 w-12 h-12 rounded-full bg-red-100 flex items-center justify-center">
            <Trash2 className="w-6 h-6 text-red-600" aria-hidden />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-gray-700 leading-relaxed">
              {message}
            </p>
            {warningText && (
              <p className="mt-3 text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
                {warningText}
              </p>
            )}
          </div>
        </div>

        <div className="flex justify-end gap-3 pt-2">
          <Button
            variant="outline"
            onClick={onClose}
            disabled={isLoading}
          >
            Cancelar
          </Button>
          <Button
            variant="danger"
            onClick={handleConfirm}
            disabled={isLoading}
          >
            {isLoading ? 'Excluindo...' : confirmLabel}
          </Button>
        </div>
      </div>
    </Modal>
  )
}
