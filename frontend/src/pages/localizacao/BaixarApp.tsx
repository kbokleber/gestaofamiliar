import { useEffect, useState } from 'react'
import QRCode from 'qrcode'
import { Copy, Download, Smartphone } from 'lucide-react'

interface VersaoApp {
  versao: string
  arquivo: string
  tamanho_bytes: number
  publicado_em?: string
}

const INFO_URL = '/downloads/app-crianca.json'

function formatarTamanho(bytes: number) {
  return `${(bytes / (1024 * 1024)).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} MB`
}

/**
 * Download da versão mais recente do app Android da criança, servido pelo próprio site.
 * O QR code permite abrir o link direto no celular da criança, sem mandar arquivo pelo WhatsApp.
 */
export default function BaixarApp() {
  const [info, setInfo] = useState<VersaoApp | null>(null)
  const [erro, setErro] = useState(false)
  const [qr, setQr] = useState('')
  const [copiado, setCopiado] = useState(false)

  useEffect(() => {
    let ativo = true
    fetch(INFO_URL, { cache: 'no-store' })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((dados: VersaoApp) => { if (ativo) setInfo(dados) })
      .catch(() => { if (ativo) setErro(true) })
    return () => { ativo = false }
  }, [])

  const link = info ? new URL(info.arquivo, window.location.origin).toString() : ''

  useEffect(() => {
    if (!link) return
    QRCode.toString(link, { type: 'svg', margin: 1, width: 160, color: { dark: '#111827', light: '#ffffff' } })
      .then(setQr)
      .catch(() => setQr(''))
  }, [link])

  if (erro) return null

  return (
    <div className="rounded-lg border border-purple-200 bg-purple-50 p-4">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
        <div className="min-w-0 flex-1">
          <p className="flex items-center gap-2 font-semibold text-gray-900">
            <Smartphone className="h-5 w-5 text-purple-600" />
            App da criança para Android
          </p>
          <p className="mt-1 text-sm text-gray-700">
            {info
              ? `Versão ${info.versao} · ${formatarTamanho(info.tamanho_bytes)}`
              : 'Carregando versão...'}
          </p>
          <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm text-gray-700">
            <li>No celular da criança, escaneie o QR code com a câmera (ou abra o link).</li>
            <li>Abra o arquivo baixado. Se pedir, permita "instalar desta fonte".</li>
            <li>Volte aqui, toque em "Gerar código" e digite o código no app.</li>
          </ol>
          <p className="mt-2 text-xs text-gray-500">Para atualizar, é só baixar e instalar por cima: não precisa conectar de novo.</p>
          <div className="mt-3 flex flex-wrap gap-2">
            <a
              href={info?.arquivo ?? '#'}
              download="GestaoFamiliar-crianca.apk"
              aria-disabled={!info}
              className={`inline-flex min-h-10 items-center gap-2 rounded-lg bg-purple-600 px-4 text-sm font-medium text-white hover:bg-purple-700 ${info ? '' : 'pointer-events-none opacity-50'}`}
            >
              <Download className="h-4 w-4" /> Baixar o app
            </a>
            <button
              type="button"
              disabled={!info}
              onClick={() => {
                void navigator.clipboard?.writeText(link).then(() => setCopiado(true))
              }}
              className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            >
              <Copy className="h-4 w-4" /> {copiado ? 'Link copiado' : 'Copiar link'}
            </button>
          </div>
        </div>
        {qr && (
          <div
            className="mx-auto h-40 w-40 shrink-0 rounded-lg bg-white p-1 shadow-sm sm:mx-0 [&>svg]:h-full [&>svg]:w-full"
            role="img"
            aria-label="QR code para baixar o app"
            // SVG gerado localmente pela biblioteca qrcode a partir do link do próprio site.
            dangerouslySetInnerHTML={{ __html: qr }}
          />
        )}
      </div>
    </div>
  )
}
