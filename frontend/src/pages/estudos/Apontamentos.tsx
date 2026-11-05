import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { StickyNote } from 'lucide-react'
import api from '../../lib/api'
import { useAuthStore } from '../../stores/authStore'
import Modal from '../../components/Modal'

interface AlunoOption {
  id: number
  first_name: string
  last_name: string
  username: string
  is_active: boolean
  is_child: boolean
  is_superuser: boolean
  family_id: number | null
}

interface CronogramaLista {
  id: number
  alunos: { id: number; nome: string }[]
}

interface Apontamento {
  id: number
  chave_origem: string
  aluno_id: number
  data: string | null
  disciplina: string
  professor: string
  tipo: string
  titulo: string
  descricao: string
  bimestre: number | null
  ano_letivo: number
  fonte: string
  scraped_at: string | null
}

function fmtData(isoData: string | null) {
  if (!isoData) return '—'
  const [y, m, d] = isoData.split('-')
  return `${d}/${m}/${y}`
}

export default function Apontamentos() {
  const user = useAuthStore((state) => state.user) as {
    id?: number
    is_child?: boolean
    is_superuser?: boolean
    family_id?: number | null
  } | null
  const filho = !!user?.is_child
  const anoAtual = new Date().getFullYear()

  const [alunoId, setAlunoId] = useState('')
  const [bimestre, setBimestre] = useState('')
  const [anoLetivo, setAnoLetivo] = useState(String(anoAtual))
  const [selecionado, setSelecionado] = useState<Apontamento | null>(null)

  const { data: cronogramas = [] } = useQuery<CronogramaLista[]>({
    queryKey: ['cronogramas'],
    queryFn: async () => (await api.get('/estudos/cronogramas')).data,
  })

  const { data: usuarios = [] } = useQuery<AlunoOption[]>({
    queryKey: ['users'],
    queryFn: async () => (await api.get('/users/')).data,
    enabled: !filho && !!user?.is_superuser,
  })

  const filhos = useMemo(() => {
    const daFamilia = usuarios.filter((aluno) => (
      aluno.is_active
      && aluno.is_child
      && !aluno.is_superuser
      && user?.family_id != null
      && aluno.family_id === user.family_id
    ))
    if (daFamilia.length > 0) {
      return daFamilia.map((aluno) => ({
        id: aluno.id,
        nome: `${aluno.first_name} ${aluno.last_name}`.trim() || aluno.username,
      }))
    }
    const mapa = new Map<number, string>()
    cronogramas.forEach((item) => item.alunos.forEach((aluno) => mapa.set(aluno.id, aluno.nome)))
    return Array.from(mapa, ([id, nome]) => ({ id, nome }))
  }, [usuarios, cronogramas, user?.family_id])

  const alunoAtivo = filho
    ? String(user?.id || '')
    : (alunoId || (filhos[0] ? String(filhos[0].id) : ''))

  const { data: itens = [], isLoading, isError } = useQuery<Apontamento[]>({
    queryKey: ['apontamentos', alunoAtivo, bimestre, anoLetivo],
    queryFn: async () => {
      const params: Record<string, string | number> = { limite: 200 }
      if (alunoAtivo) params.aluno_id = Number(alunoAtivo)
      if (bimestre) params.bimestre = Number(bimestre)
      if (anoLetivo) params.ano_letivo = Number(anoLetivo)
      return (await api.get('/estudos/apontamentos', { params })).data
    },
    enabled: !!alunoAtivo,
  })

  const campo = 'min-h-12 w-full rounded-xl border border-gray-300 bg-white px-3 text-base'

  return (
    <div className="mx-auto w-full max-w-lg lg:max-w-3xl">
      <div className="mb-4">
        <h1 className="flex items-center gap-2 text-xl font-bold text-gray-900 sm:text-2xl">
          <StickyNote className="h-7 w-7 text-amber-700" />
          Apontamentos
        </h1>
        <p className="mt-1 text-sm text-gray-600">
          Observações do e-class importadas via sync (POST /estudos/apontamentos/importar).
        </p>
      </div>

      <div className="mb-4 grid gap-2 sm:grid-cols-3">
        {!filho && (
          <select
            value={alunoAtivo}
            onChange={(e) => setAlunoId(e.target.value)}
            className={campo}
            aria-label="Filho"
          >
            {filhos.map((aluno) => (
              <option key={aluno.id} value={aluno.id}>{aluno.nome}</option>
            ))}
          </select>
        )}
        <select value={anoLetivo} onChange={(e) => setAnoLetivo(e.target.value)} className={campo} aria-label="Ano letivo">
          {[anoAtual, anoAtual - 1].map((ano) => (
            <option key={ano} value={ano}>{ano}</option>
          ))}
        </select>
        <select value={bimestre} onChange={(e) => setBimestre(e.target.value)} className={campo} aria-label="Bimestre">
          <option value="">Todos os bimestres</option>
          {[1, 2, 3, 4].map((n) => <option key={n} value={n}>{n}º bimestre</option>)}
        </select>
      </div>

      {!alunoAtivo && (
        <p className="rounded-xl border border-dashed border-gray-300 bg-white p-6 text-gray-600">
          Selecione um filho para ver os apontamentos.
        </p>
      )}
      {alunoAtivo && isLoading && <p className="text-gray-600">Carregando apontamentos…</p>}
      {alunoAtivo && isError && <p className="text-red-700">Não foi possível carregar os apontamentos.</p>}
      {alunoAtivo && !isLoading && !isError && itens.length === 0 && (
        <p className="rounded-xl border border-dashed border-gray-300 bg-white p-6 text-gray-600">
          Nenhum apontamento sincronizado ainda. Eles entram após a importação do e-class.
        </p>
      )}

      <ul className="space-y-2">
        {itens.map((item) => (
          <li key={item.id}>
            <button
              type="button"
              onClick={() => setSelecionado(item)}
              className="w-full rounded-2xl border border-gray-200 bg-white px-4 py-3 text-left hover:border-amber-300 hover:bg-amber-50/40"
            >
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <p className="font-semibold text-gray-900">{item.titulo || item.tipo || 'Apontamento'}</p>
                <p className="text-sm text-gray-600">
                  {fmtData(item.data)}
                  {item.bimestre != null && (
                    <span className="ml-2 text-amber-800">{item.bimestre}º bim.</span>
                  )}
                </p>
              </div>
              <p className="mt-1 text-sm text-gray-700">
                {[item.tipo, item.disciplina, item.professor ? `Prof.: ${item.professor}` : '']
                  .filter(Boolean)
                  .join(' · ')}
              </p>
              {item.descricao && (
                <p className="mt-1 line-clamp-2 text-sm text-gray-600">{item.descricao}</p>
              )}
            </button>
          </li>
        ))}
      </ul>

      <Modal
        isOpen={!!selecionado}
        onClose={() => setSelecionado(null)}
        title={selecionado?.titulo || selecionado?.tipo || 'Apontamento'}
      >
        {selecionado && (
          <div className="space-y-2 text-left text-sm text-gray-800">
            <p><span className="text-gray-500">Data:</span> {fmtData(selecionado.data)}</p>
            {selecionado.tipo && <p><span className="text-gray-500">Tipo:</span> {selecionado.tipo}</p>}
            {selecionado.disciplina && <p><span className="text-gray-500">Disciplina:</span> {selecionado.disciplina}</p>}
            {selecionado.professor && <p><span className="text-gray-500">Prof.:</span> {selecionado.professor}</p>}
            {selecionado.bimestre != null && (
              <p><span className="text-gray-500">Bimestre:</span> {selecionado.bimestre}º</p>
            )}
            {selecionado.descricao && (
              <p className="whitespace-pre-wrap border-t border-gray-100 pt-3">{selecionado.descricao}</p>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}
