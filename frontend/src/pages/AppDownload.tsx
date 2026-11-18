import { Download, Smartphone } from 'lucide-react'
import { formatarTamanho, useVersaoApp } from './localizacao/BaixarApp'

/**
 * Página pública /app: aberta no celular da criança para instalar ou atualizar o app,
 * sem login. Só mostra a versão disponível e o botão de download.
 */
export default function AppDownload() {
  const { info } = useVersaoApp()

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 p-4">
      <div className="w-full max-w-sm rounded-2xl bg-white p-6 text-center shadow-lg">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-purple-600 text-white">
          <Smartphone className="h-8 w-8" />
        </div>
        <h1 className="mt-4 text-xl font-bold text-gray-900">Gestão Familiar</h1>
        <p className="text-sm text-gray-600">App da criança para Android</p>

        {info === undefined && <p className="mt-6 text-sm text-gray-500">Carregando...</p>}
        {info === null && (
          <p className="mt-6 text-sm text-gray-600">O app ainda não está disponível para download. Peça para um adulto da família.</p>
        )}
        {info && (
          <>
            <p className="mt-4 text-sm text-gray-700">Versão {info.versao} · {formatarTamanho(info.tamanho_bytes)}</p>
            <a
              href={info.arquivo}
              download
              className="mt-4 inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-purple-600 px-4 text-base font-semibold text-white hover:bg-purple-700"
            >
              <Download className="h-5 w-5" /> Baixar o app
            </a>
            <ol className="mt-5 list-decimal space-y-1 pl-5 text-left text-sm text-gray-700">
              <li>Toque em "Baixar o app".</li>
              <li>Abra o arquivo baixado. Se pedir, permita "instalar desta fonte".</li>
              <li>Já tem o app? Instale por cima: ele atualiza sem precisar conectar de novo.</li>
            </ol>
          </>
        )}
      </div>
    </div>
  )
}
