import { BookOpen } from 'lucide-react'

export default function Estudos() {
  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900 mb-3 flex items-center gap-2">
        <BookOpen className="w-8 h-8 text-indigo-600" />
        Estudos
      </h1>
      <p className="text-gray-600 max-w-2xl">
        Esta área fica reservada para o sistema de estudos. O conteúdo entra aqui depois.
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
