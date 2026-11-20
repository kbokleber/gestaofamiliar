import { MapPin } from 'lucide-react'
import { PAGINA_APP } from './BaixarApp'

/**
 * Tela de quem só compartilha a própria posição (ex.: avós). Não mostra mapa nem ninguém:
 * a API recusa toda leitura de localização para esse perfil.
 */
export default function MinhaLocalizacao() {
  return (
    <div className="mx-auto max-w-xl space-y-4">
      <h1 className="flex items-center gap-2 text-2xl font-bold text-gray-900">
        <MapPin className="h-6 w-6 text-teal-700" /> Minha localização
      </h1>
      <div className="space-y-3 rounded-lg bg-white p-4 text-base text-gray-700 shadow-sm">
        <p>A sua localização é compartilhada com os adultos da família pelo app Gestão Familiar, no seu celular.</p>
        <p>Você não vê o mapa nem a posição de outras pessoas.</p>
        <p>No app, use <strong>Configurações de envio</strong> para conferir se está tudo certo ou para parar de compartilhar, e o botão <strong>SOS</strong> para pedir ajuda.</p>
        <p className="text-sm text-gray-500">Ainda não tem o app? Abra <a className="text-purple-700 underline" href={PAGINA_APP}>{PAGINA_APP}</a> no celular.</p>
      </div>
    </div>
  )
}
