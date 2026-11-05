import ApontamentosPage from './Apontamentos'
import AtividadesPage from './Atividades'
import AvaliacoesPage from './Avaliacoes'
import PainelPage from './Painel'
import ProvasPage from './Provas'

export function Painel() {
  return <PainelPage />
}

export function Atividades() {
  return <AtividadesPage modo="atividade" />
}

export function Comunicados() {
  return <AtividadesPage modo="comunicado" />
}

export function Provas() {
  return <ProvasPage />
}

export function Avaliacoes() {
  return <AvaliacoesPage />
}

export function Apontamentos() {
  return <ApontamentosPage />
}

export function SemMenu() {
  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-3">Nenhum menu liberado</h1>
      <p className="text-gray-600">Peça a um administrador para liberar o menu Estudos.</p>
    </div>
  )
}
