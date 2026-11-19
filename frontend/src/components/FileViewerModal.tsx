import { useEffect, useRef, useState } from 'react'
import { Download, Loader2, X, ZoomIn, ZoomOut } from 'lucide-react'
import { baixarBlob, ehPdf, nomeParaDownload } from '../utils/baixarArquivo'

export interface ArquivoVisualizado {
  blob: Blob
  nome: string
  tipo?: string
}

interface FileViewerModalProps {
  arquivo: ArquivoVisualizado | null
  onClose: () => void
}

type PdfDoc = import('pdfjs-dist').PDFDocumentProxy

/** Carrega o pdf.js só quando um PDF é aberto, para não pesar o restante do app. */
async function carregarPdfJs() {
  const pdfjs = await import('pdfjs-dist/legacy/build/pdf.mjs')
  const worker = await import('pdfjs-dist/legacy/build/pdf.worker.min.mjs?url')
  pdfjs.GlobalWorkerOptions.workerSrc = worker.default
  return pdfjs
}

const ZOOM_MIN = 0.5
const ZOOM_MAX = 3
const MAX_PIXELS_CANVAS = 16_000_000

/**
 * Mostra PDF e imagem dentro do próprio app.
 * O PDF é desenhado em canvas pelo pdf.js: não depende do leitor do navegador,
 * que no Chrome do Android abre about:blank em vez do arquivo.
 */
export default function FileViewerModal({ arquivo, onClose }: FileViewerModalProps) {
  const onCloseRef = useRef(onClose)
  onCloseRef.current = onClose
  const isPdf = !!arquivo && ehPdf(arquivo.tipo || arquivo.blob.type, arquivo.nome)

  useEffect(() => {
    if (!arquivo) return
    const aoTeclar = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onCloseRef.current()
    }
    document.addEventListener('keydown', aoTeclar)
    const overflowAnterior = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', aoTeclar)
      document.body.style.overflow = overflowAnterior
    }
  }, [arquivo])

  if (!arquivo) return null

  const baixar = () => {
    const tipo = arquivo.tipo || arquivo.blob.type
    baixarBlob(arquivo.blob, nomeParaDownload(arquivo.nome, tipo), tipo)
  }

  return (
    <div
      className="fixed inset-0 z-[90] flex flex-col bg-gray-900/95"
      role="dialog"
      aria-modal="true"
      aria-label={`Visualizar ${arquivo.nome}`}
    >
      <div className="flex items-center gap-2 bg-gray-900 px-3 py-2 text-white shadow">
        <p className="min-w-0 flex-1 truncate text-sm font-medium" title={arquivo.nome}>
          {arquivo.nome}
        </p>
        <button
          type="button"
          onClick={baixar}
          className="flex h-10 w-10 items-center justify-center rounded-full hover:bg-white/10"
          title="Baixar"
          aria-label="Baixar"
        >
          <Download className="h-5 w-5" />
        </button>
        <button
          type="button"
          onClick={onClose}
          className="flex h-10 w-10 items-center justify-center rounded-full hover:bg-white/10"
          title="Fechar"
          aria-label="Fechar"
          autoFocus
        >
          <X className="h-6 w-6" />
        </button>
      </div>
      {isPdf ? (
        <VisualizadorPdf blob={arquivo.blob} onBaixar={baixar} />
      ) : (
        <VisualizadorImagem blob={arquivo.blob} nome={arquivo.nome} />
      )}
    </div>
  )
}

function VisualizadorImagem({ blob, nome }: { blob: Blob; nome: string }) {
  const [url, setUrl] = useState('')

  useEffect(() => {
    const endereco = URL.createObjectURL(blob)
    setUrl(endereco)
    return () => URL.revokeObjectURL(endereco)
  }, [blob])

  return (
    <div className="flex flex-1 items-center justify-center overflow-auto p-2">
      {url && <img src={url} alt={nome} className="max-h-full max-w-full object-contain" />}
    </div>
  )
}

function VisualizadorPdf({ blob, onBaixar }: { blob: Blob; onBaixar: () => void }) {
  const areaRef = useRef<HTMLDivElement>(null)
  const [doc, setDoc] = useState<PdfDoc | null>(null)
  const [erro, setErro] = useState(false)
  const [zoom, setZoom] = useState(1)
  const [largura, setLargura] = useState(0)

  useEffect(() => {
    let cancelado = false
    let carregado: PdfDoc | null = null
    setDoc(null)
    setErro(false)
    ;(async () => {
      try {
        const pdfjs = await carregarPdfJs()
        const dados = new Uint8Array(await blob.arrayBuffer())
        carregado = await pdfjs.getDocument({ data: dados }).promise
        if (cancelado) {
          void carregado.destroy()
          return
        }
        setDoc(carregado)
      } catch (e) {
        console.error('Erro ao abrir PDF:', e)
        if (!cancelado) setErro(true)
      }
    })()
    return () => {
      cancelado = true
      if (carregado) void carregado.destroy()
    }
  }, [blob])

  // Ajusta as páginas à largura da tela; o zoom multiplica essa largura.
  useEffect(() => {
    const area = areaRef.current
    if (!area) return
    const medir = () => setLargura(area.clientWidth)
    medir()
    const observador = new ResizeObserver(medir)
    observador.observe(area)
    return () => observador.disconnect()
  }, [])

  const paginas = doc ? Array.from({ length: doc.numPages }, (_, i) => i + 1) : []

  return (
    <>
      <div ref={areaRef} className="flex-1 overflow-auto px-2 py-3">
        {erro ? (
          <div className="mx-auto mt-10 max-w-sm rounded-lg bg-white p-4 text-center text-sm text-gray-700">
            <p>Não foi possível mostrar este PDF.</p>
            <button
              type="button"
              onClick={onBaixar}
              className="mt-3 inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-white hover:bg-indigo-700"
            >
              <Download className="h-4 w-4" /> Baixar arquivo
            </button>
          </div>
        ) : !doc || !largura ? (
          <div className="mt-10 flex items-center justify-center gap-2 text-white">
            <Loader2 className="h-5 w-5 animate-spin" /> Carregando PDF...
          </div>
        ) : (
          // w-max + min-w-full: com zoom maior que a tela, a área cresce e dá para rolar até as
          // bordas; centralizar com items-center sozinho empurrava a parte esquerda para fora do alcance.
          <div className="mx-auto flex w-max min-w-full flex-col items-center gap-3">
            {paginas.map((numero) => (
              <PaginaPdf
                key={numero}
                doc={doc}
                numero={numero}
                largura={Math.min(largura - 16, 1000) * zoom}
              />
            ))}
          </div>
        )}
      </div>
      {doc && !erro && (
        <div className="flex items-center justify-center gap-3 bg-gray-900 px-3 py-2 pb-[max(0.5rem,env(safe-area-inset-bottom))] text-sm text-white">
          <button
            type="button"
            onClick={() => setZoom((z) => Math.max(ZOOM_MIN, +(z - 0.25).toFixed(2)))}
            disabled={zoom <= ZOOM_MIN}
            className="flex h-10 w-10 items-center justify-center rounded-full hover:bg-white/10 disabled:opacity-40"
            aria-label="Diminuir zoom"
          >
            <ZoomOut className="h-5 w-5" />
          </button>
          <button
            type="button"
            onClick={() => setZoom(1)}
            className="min-w-[4rem] rounded px-2 py-1 hover:bg-white/10"
            title="Ajustar à largura"
          >
            {Math.round(zoom * 100)}%
          </button>
          <button
            type="button"
            onClick={() => setZoom((z) => Math.min(ZOOM_MAX, +(z + 0.25).toFixed(2)))}
            disabled={zoom >= ZOOM_MAX}
            className="flex h-10 w-10 items-center justify-center rounded-full hover:bg-white/10 disabled:opacity-40"
            aria-label="Aumentar zoom"
          >
            <ZoomIn className="h-5 w-5" />
          </button>
          <span className="ml-2 text-gray-300">
            {doc.numPages} {doc.numPages === 1 ? 'página' : 'páginas'}
          </span>
        </div>
      )}
    </>
  )
}

function PaginaPdf({ doc, numero, largura }: { doc: PdfDoc; numero: number; largura: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    let cancelado = false
    let tarefa: { cancel: () => void } | null = null
    ;(async () => {
      const pagina = await doc.getPage(numero)
      const canvas = canvasRef.current
      if (cancelado || !canvas) return
      const base = pagina.getViewport({ scale: 1 })
      const escala = largura / base.width
      // Celulares recusam canvas muito grandes (iOS: ~16 milhões de pixels).
      const pixelsCss = base.width * escala * base.height * escala
      const densidade = Math.min(window.devicePixelRatio || 1, 2, Math.sqrt(MAX_PIXELS_CANVAS / pixelsCss))
      const viewport = pagina.getViewport({ scale: escala * densidade })
      canvas.width = Math.floor(viewport.width)
      canvas.height = Math.floor(viewport.height)
      canvas.style.width = `${Math.floor(viewport.width / densidade)}px`
      canvas.style.height = `${Math.floor(viewport.height / densidade)}px`
      const contexto = canvas.getContext('2d')
      if (!contexto) return
      const render = pagina.render({ canvasContext: contexto, viewport })
      tarefa = render
      try {
        await render.promise
      } catch {
        // render cancelado ao mudar o zoom
      }
    })()
    return () => {
      cancelado = true
      tarefa?.cancel()
    }
  }, [doc, numero, largura])

  return <canvas ref={canvasRef} className="max-w-none bg-white shadow-lg" />
}
