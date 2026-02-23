import { useState } from 'react'
import { Upload, X, FileText, Image, Download, Eye } from 'lucide-react'

export interface Document {
  name: string
  type: string
  size: number
  data: string // base64
}

interface DocumentUploadProps {
  documents: Document[]
  onChange: (documents: Document[]) => void
  maxFiles?: number
  maxSizeMB?: number
}

export default function DocumentUpload({ 
  documents, 
  onChange, 
  maxFiles = 10,
  maxSizeMB = 10
}: DocumentUploadProps) {
  const [uploading, setUploading] = useState(false)

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return

    if (documents.length + files.length > maxFiles) {
      alert(`Você pode enviar no máximo ${maxFiles} arquivos`)
      return
    }

    setUploading(true)

    try {
      const newDocuments: Document[] = []

      for (let i = 0; i < files.length; i++) {
        const file = files[i]
        
        // Validar tamanho
        if (file.size > maxSizeMB * 1024 * 1024) {
          alert(`O arquivo "${file.name}" é maior que ${maxSizeMB}MB`)
          continue
        }

        // Validar tipo
        const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'application/pdf']
        if (!validTypes.includes(file.type)) {
          alert(`O arquivo "${file.name}" não é um tipo válido (JPG, PNG, GIF ou PDF)`)
          continue
        }

        // Converter para base64
        const base64 = await fileToBase64(file)

        newDocuments.push({
          name: file.name,
          type: file.type,
          size: file.size,
          data: base64
        })
      }

      onChange([...documents, ...newDocuments])
    } catch (error) {
      console.error('Erro ao fazer upload:', error)
      alert('Erro ao fazer upload dos arquivos')
    } finally {
      setUploading(false)
      e.target.value = '' // Limpar input
    }
  }

  const fileToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onloadend = () => {
        const base64String = (reader.result as string).split(',')[1]
        resolve(base64String)
      }
      reader.onerror = reject
      reader.readAsDataURL(file)
    })
  }

  const removeDocument = (index: number) => {
    const doc = documents[index]
    if (!confirm(`Deseja realmente excluir o arquivo "${doc.name}"?`)) {
      return
    }
    const newDocuments = documents.filter((_, i) => i !== index)
    onChange(newDocuments)
  }

  const downloadDocument = (doc: Document) => {
    if (!doc.data) {
      alert('Arquivo sem dados para download.')
      return
    }
    try {
      const { mimeType } = getDisplayType(doc)
      const blob = base64ToBlob(doc.data, mimeType)
      const blobUrl = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = blobUrl
      link.download = doc.name
      link.click()
      URL.revokeObjectURL(blobUrl)
    } catch (e) {
      console.error('Erro ao fazer download:', e)
      alert('Não foi possível fazer o download do arquivo.')
    }
  }

  const getDisplayType = (doc: Document): { isPdf: boolean; mimeType: string } => {
    const ext = (doc.name || '').split('.').pop()?.toLowerCase()
    const storedType = (doc.type || '').toLowerCase()
    const imageTypes: Record<string, string> = {
      jpg: 'image/jpeg', jpeg: 'image/jpeg', png: 'image/png', gif: 'image/gif'
    }
    if (ext && imageTypes[ext]) {
      return { isPdf: false, mimeType: imageTypes[ext] }
    }
    if (ext === 'pdf' || storedType === 'application/pdf') {
      return { isPdf: true, mimeType: 'application/pdf' }
    }
    if (storedType.startsWith('image/')) return { isPdf: false, mimeType: storedType }
    return { isPdf: false, mimeType: storedType || 'image/jpeg' }
  }

  const base64ToBlob = (base64: string, mimeType: string): Blob => {
    const clean = String(base64).replace(/\s/g, '')
    const byteChars = atob(clean)
    const byteNumbers = new Array(byteChars.length)
    for (let i = 0; i < byteChars.length; i++) byteNumbers[i] = byteChars.charCodeAt(i)
    return new Blob([new Uint8Array(byteNumbers)], { type: mimeType })
  }

  const viewDocument = (doc: Document) => {
    if (!doc.data) {
      alert('Arquivo sem dados para visualização. Pode ter sido salvo em formato antigo.')
      return
    }
    const safeName = String(doc.name).replace(/</g, '&lt;').replace(/"/g, '&quot;')
    const { isPdf, mimeType } = getDisplayType(doc)
    const newWindow = window.open('', '_blank')
    if (newWindow) {
      try {
        const blob = base64ToBlob(doc.data, mimeType)
        const blobUrl = URL.createObjectURL(blob)
        if (isPdf) {
          newWindow.document.write(`
            <!DOCTYPE html><html><head><meta charset="UTF-8"><title>${safeName}</title></head>
            <body style="margin:0;overflow:hidden">
              <iframe src="${blobUrl}" style="width:100%;height:100vh;border:none;" title="${safeName}"></iframe>
            </body></html>
          `)
        } else {
          newWindow.document.write(`
            <!DOCTYPE html><html><head><meta charset="UTF-8"><title>${safeName}</title>
            <style>body{margin:0;display:flex;justify-content:center;align-items:center;min-height:100vh;background:#1a1a1a}</style></head>
            <body><img src="${blobUrl}" alt="${safeName}" style="max-width:100%;max-height:100vh;object-fit:contain" /></body></html>
          `)
        }
        newWindow.document.close()
        newWindow.addEventListener('beforeunload', () => URL.revokeObjectURL(blobUrl))
      } catch (e) {
        console.error('Erro ao visualizar:', e)
        newWindow.close()
        alert('Não foi possível abrir o arquivo. Tente fazer o download.')
      }
    } else {
      alert('O navegador bloqueou a janela de visualização. Permita pop-ups ou use o botão de download.')
    }
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  const getFileIcon = (type: string) => {
    if (type.startsWith('image/')) return <Image className="h-5 w-5 text-blue-500" />
    if (type === 'application/pdf') return <FileText className="h-5 w-5 text-red-500" />
    return <FileText className="h-5 w-5 text-gray-500" />
  }

  return (
    <div className="space-y-4">
      {/* Botão de Upload */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Documentos (Fotos, PDFs)
        </label>
        <div className="flex items-center justify-center w-full">
          <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-gray-300 border-dashed rounded-lg cursor-pointer bg-gray-50 hover:bg-gray-100">
            <div className="flex flex-col items-center justify-center pt-5 pb-6">
              <Upload className="w-10 h-10 mb-3 text-gray-400" />
              <p className="mb-2 text-sm text-gray-500">
                <span className="font-semibold">Clique para selecionar</span> ou arraste arquivos
              </p>
              <p className="text-xs text-gray-500">
                JPG, PNG, GIF ou PDF (max. {maxSizeMB}MB cada)
              </p>
            </div>
            <input
              type="file"
              className="hidden"
              multiple
              accept="image/jpeg,image/jpg,image/png,image/gif,application/pdf"
              onChange={handleFileSelect}
              disabled={uploading || documents.length >= maxFiles}
            />
          </label>
        </div>
        <p className="mt-1 text-xs text-gray-500">
          {documents.length} de {maxFiles} arquivos
        </p>
      </div>

      {/* Lista de Documentos */}
      {documents.length > 0 && (
        <div className="space-y-2">
          <p className="text-sm font-medium text-gray-700">Arquivos anexados:</p>
          {documents.map((doc, index) => (
            <div
              key={index}
              className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-200"
            >
              <div className="flex items-center space-x-3 flex-1 min-w-0">
                {getFileIcon(doc.type)}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">{doc.name}</p>
                  <p className="text-xs text-gray-500">{formatFileSize(doc.size)}</p>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <button
                  type="button"
                  onClick={() => viewDocument(doc)}
                  className="p-1 text-blue-600 hover:text-blue-800"
                  title="Visualizar"
                >
                  <Eye className="h-5 w-5" />
                </button>
                <button
                  type="button"
                  onClick={() => downloadDocument(doc)}
                  className="p-1 text-green-600 hover:text-green-800"
                  title="Download"
                >
                  <Download className="h-5 w-5" />
                </button>
                <button
                  type="button"
                  onClick={() => removeDocument(index)}
                  className="p-1 text-red-600 hover:text-red-800"
                  title="Remover"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {uploading && (
        <div className="text-center text-sm text-gray-500">
          Fazendo upload...
        </div>
      )}
    </div>
  )
}

