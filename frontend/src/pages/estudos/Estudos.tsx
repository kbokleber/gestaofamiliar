import { ClipboardList, FileText } from 'lucide-react'

export function Atividades() {
  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900 mb-3 flex items-center gap-2">
        <ClipboardList className="w-8 h-8 text-indigo-600" />
        Atividades
      </h1>
      <p className="text-gray-600 max-w-2xl">
        As atividades de estudo entram nesta tela.
      </p>
    </div>
  )
}

export function Provas() {
  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900 mb-3 flex items-center gap-2">
        <FileText className="w-8 h-8 text-indigo-600" />
        Provas
      </h1>
      <p className="text-gray-600 max-w-2xl">
        As provas entram nesta tela.
      </p>
    </div>
  )
}

export function SemMenu() {
  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-3">Nenhum menu liberado</h1>
      <p className="text-gray-600">Peça a um administrador para liberar o menu Estudos.</p>
    </div>
  )
}
