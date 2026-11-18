import { useCallback, useEffect, useState } from 'react'
import QRCode from 'qrcode'
import { Copy, Download, KeyRound, Smartphone, Upload } from 'lucide-react'
import api from '../../lib/api'
import { useAuthStore } from '../../stores/authStore'

export interface VersaoApp {
  versao: string
  arquivo: string
  tamanho_bytes: number
  publicado_em?: string | null
}

/** Endereço público da página de download (abre no celular, sem login). */
export const PAGINA_APP = '/app'
const INFO_URL = '/api/v1/app-android/ultima'

export function formatarTamanho(bytes: number) {
  return `${(bytes / (1024 * 1024)).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} MB`
}

/** Versão mais recente do app, lida do servidor (rota pública). null = nenhuma enviada ainda. */
export function useVersaoApp() {
  const [info, setInfo] = useState<VersaoApp | null | undefined>(undefined)
  const carregar = useCallback(() => {
    fetch(INFO_URL, { cache: 'no-store' })
      .then((r) => (r.ok ? r.json() : null))
      .then((dados: VersaoApp | null) => setInfo(dados))
      .catch(() => setInfo(null))
  }, [])
  useEffect(() => { carregar() }, [carregar])
  return { info, recarregar: carregar }
}

/**
 * Cartão em Localização › Celulares: versão disponível, botão de download, QR code da página /app
 * e, para o admin, o envio de uma versão nova do APK.
 */
export default function BaixarApp() {
  const admin = !!useAuthStore((s) => s.user)?.is_superuser
  const { info, recarregar } = useVersaoApp()
  const [qr, setQr] = useState('')
  const [copiado, setCopiado] = useState(false)
  const pagina = `${window.location.origin}${PAGINA_APP}`

  useEffect(() => {
    QRCode.toString(pagina, { type: 'svg', margin: 1, width: 160, color: { dark: '#111827', light: '#ffffff' } })
      .then(setQr)
      .catch(() => setQr(''))
  }, [pagina])

  if (info === undefined) return null
  if (info === null && !admin) return null

  return (
    <div className="rounded-lg border border-purple-200 bg-purple-50 p-4">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
        <div className="min-w-0 flex-1">
          <p className="flex items-center gap-2 font-semibold text-gray-900">
            <Smartphone className="h-5 w-5 text-purple-600" />
            App Gestão Familiar para Android
          </p>
          {info ? (
            <>
              <p className="mt-1 text-sm text-gray-700">Versão {info.versao} · {formatarTamanho(info.tamanho_bytes)}</p>
              <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm text-gray-700">
                <li>No celular, escaneie o QR code com a câmera ou abra <strong>{pagina}</strong>.</li>
                <li>Baixe e abra o arquivo. Se pedir, permita "instalar desta fonte".</li>
                <li>Abra o app e entre com a sua conta. No celular da criança, entre com a conta dela: a localização se conecta sozinha. Adultos recebem os alertas (chegada, bateria baixa, sem sinal).</li>
              </ol>
              <p className="mt-2 text-xs text-gray-500">Para atualizar, é só abrir {PAGINA_APP} no celular e instalar por cima: não precisa conectar de novo. Sem login da criança, ainda dá para usar "Gerar código" nas configurações do app.</p>
              <div className="mt-3 flex flex-wrap gap-2">
                <a
                  href={info.arquivo}
                  download
                  className="inline-flex min-h-10 items-center gap-2 rounded-lg bg-purple-600 px-4 text-sm font-medium text-white hover:bg-purple-700"
                >
                  <Download className="h-4 w-4" /> Baixar o app
                </a>
                <button
                  type="button"
                  onClick={() => { void navigator.clipboard?.writeText(pagina).then(() => setCopiado(true)) }}
                  className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 text-sm text-gray-700 hover:bg-gray-50"
                >
                  <Copy className="h-4 w-4" /> {copiado ? 'Link copiado' : 'Copiar link'}
                </button>
              </div>
            </>
          ) : (
            <p className="mt-1 text-sm text-gray-700">Nenhuma versão enviada ainda. Envie o APK abaixo para liberar o download em {PAGINA_APP}.</p>
          )}
          {admin && <EnviarVersao aoEnviar={recarregar} />}
          {admin && <TokenPublicacao />}
        </div>
        {qr && info && (
          <div
            className="mx-auto h-40 w-40 shrink-0 rounded-lg bg-white p-1 shadow-sm sm:mx-0 [&>svg]:h-full [&>svg]:w-full"
            role="img"
            aria-label="QR code da página de download do app"
            // SVG gerado localmente pela biblioteca qrcode a partir do endereço do próprio site.
            dangerouslySetInnerHTML={{ __html: qr }}
          />
        )}
      </div>
    </div>
  )
}

/** Só admin: envia o APK assinado de uma versão nova. A versão é sugerida pelo nome do arquivo. */
function EnviarVersao({ aoEnviar }: { aoEnviar: () => void }) {
  const [arquivo, setArquivo] = useState<File | null>(null)
  const [versao, setVersao] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [mensagem, setMensagem] = useState('')

  const enviar = async () => {
    if (!arquivo || !versao.trim()) return
    setEnviando(true)
    setMensagem('')
    const dados = new FormData()
    dados.append('versao', versao.trim())
    dados.append('arquivo', arquivo)
    try {
      // A instância da API usa JSON por padrão; sem isto o axios converte o FormData em JSON e o arquivo se perde.
      const { data } = await api.post<VersaoApp>('/app-android/upload', dados, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setMensagem(`Versão ${data.versao} publicada. Já pode ser baixada em ${PAGINA_APP}.`)
      setArquivo(null)
      setVersao('')
      aoEnviar()
    } catch (e) {
      const detalhe = (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
      const status = (e as { response?: { status?: number } })?.response?.status
      setMensagem(
        typeof detalhe === 'string'
          ? detalhe
          : status === 413
            ? 'O arquivo é grande demais para o servidor.'
            : `Não foi possível enviar o app${status ? ` (erro ${status})` : ''}.`,
      )
    } finally {
      setEnviando(false)
    }
  }

  return (
    <details className="mt-4 rounded-lg border border-purple-200 bg-white p-3">
      <summary className="cursor-pointer text-sm font-medium text-purple-800">Enviar nova versão do app (admin)</summary>
      <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-end">
        <label className="text-sm text-gray-700">
          Arquivo .apk
          <input
            type="file"
            accept=".apk,application/vnd.android.package-archive"
            onChange={(e) => {
              const f = e.target.files?.[0] ?? null
              setArquivo(f)
              const achada = f?.name.match(/(\d+\.\d+(?:\.\d+)?)/)
              if (achada && !versao) setVersao(achada[1])
            }}
            className="mt-1 block w-full text-sm"
          />
        </label>
        <label className="text-sm text-gray-700">
          Versão
          <input
            value={versao}
            onChange={(e) => setVersao(e.target.value)}
            placeholder="1.0.2"
            className="mt-1 block min-h-10 w-28 rounded-lg border border-gray-300 px-3"
          />
        </label>
        <button
          type="button"
          onClick={() => { void enviar() }}
          disabled={!arquivo || !versao.trim() || enviando}
          className="inline-flex min-h-10 items-center gap-2 rounded-lg bg-purple-600 px-4 text-sm font-medium text-white hover:bg-purple-700 disabled:opacity-50"
        >
          <Upload className="h-4 w-4" /> {enviando ? 'Enviando...' : 'Publicar'}
        </button>
      </div>
      {mensagem && <p className="mt-2 text-sm text-gray-700">{mensagem}</p>}
    </details>
  )
}

/**
 * Só admin: token que permite publicar versões novas do app automaticamente, sem baixar e reenviar o APK.
 * O valor aparece uma única vez; depois, só dá para gerar outro (que invalida o anterior) ou revogar.
 */
function TokenPublicacao() {
  const [ativo, setAtivo] = useState<boolean | null>(null)
  const [token, setToken] = useState('')
  const [copiado, setCopiado] = useState(false)
  const [ocupado, setOcupado] = useState(false)
  const [erro, setErro] = useState('')

  useEffect(() => {
    api.get<{ ativo: boolean }>('/app-android/token-publicacao')
      .then(({ data }) => setAtivo(data.ativo))
      .catch(() => setAtivo(null))
  }, [])

  const gerar = async () => {
    if (ativo && !window.confirm('Gerar um token novo? O token atual deixa de funcionar.')) return
    setOcupado(true)
    setErro('')
    try {
      const { data } = await api.post<{ token: string }>('/app-android/token-publicacao')
      setToken(data.token)
      setAtivo(true)
      setCopiado(false)
    } catch {
      setErro('Não foi possível gerar o token.')
    } finally {
      setOcupado(false)
    }
  }

  const revogar = async () => {
    if (!window.confirm('Revogar o token de publicação? A publicação automática para até gerar outro.')) return
    setOcupado(true)
    setErro('')
    try {
      await api.delete('/app-android/token-publicacao')
      setAtivo(false)
      setToken('')
    } catch {
      setErro('Não foi possível revogar o token.')
    } finally {
      setOcupado(false)
    }
  }

  return (
    <details className="mt-3 rounded-lg border border-purple-200 bg-white p-3">
      <summary className="cursor-pointer text-sm font-medium text-purple-800">Publicação automática (admin)</summary>
      <p className="mt-2 text-sm text-gray-700">
        Com este token, as versões novas do app são publicadas direto aqui, sem você baixar e reenviar o APK.
        Ele só serve para publicar o app.
      </p>
      <p className="mt-1 text-xs text-gray-500">
        Situação: {ativo === null ? '—' : ativo ? 'token ativo' : 'sem token'}
      </p>
      {token && (
        <div className="mt-2 rounded-lg bg-amber-50 p-2 text-sm text-amber-900">
          <p className="font-medium">Copie agora: este valor não aparece de novo.</p>
          <code className="mt-1 block break-all rounded bg-white p-2 text-xs text-gray-900">{token}</code>
          <button
            type="button"
            onClick={() => { void navigator.clipboard?.writeText(token).then(() => setCopiado(true)) }}
            className="mt-2 inline-flex min-h-9 items-center gap-2 rounded-lg border border-gray-300 bg-white px-3 text-sm text-gray-700"
          >
            <Copy className="h-4 w-4" /> {copiado ? 'Copiado' : 'Copiar'}
          </button>
        </div>
      )}
      <div className="mt-3 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => { void gerar() }}
          disabled={ocupado}
          className="inline-flex min-h-10 items-center gap-2 rounded-lg bg-purple-600 px-4 text-sm font-medium text-white hover:bg-purple-700 disabled:opacity-50"
        >
          <KeyRound className="h-4 w-4" /> {ativo ? 'Gerar novo token' : 'Gerar token de publicação'}
        </button>
        {ativo && (
          <button
            type="button"
            onClick={() => { void revogar() }}
            disabled={ocupado}
            className="inline-flex min-h-10 items-center rounded-lg px-3 text-sm text-red-600 hover:bg-red-50 disabled:opacity-50"
          >
            Revogar
          </button>
        )}
      </div>
      {erro && <p className="mt-2 text-sm text-red-600">{erro}</p>}
    </details>
  )
}
