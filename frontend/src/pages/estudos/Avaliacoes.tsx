import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ClipboardCheck } from 'lucide-react'
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
  bimestre: number
  ano_letivo: number
}

interface AvaliacaoLista {
  id: number
  disciplina: string
  categoria: string
  categoria_rotulo: string | null
  tipo_codigo_eclass?: string | null
  titulo: string
  data_texto: string
  data_inicio: string | null
  valor: number | null
  valor_texto: string | null
  nota_alcancada?: number | null
  professor?: string | null
  fonte?: string | null
  composicao?: { realizado_em?: string | null; avaliacao?: string | null; nota_final?: number | null }[] | null
  objeto_conhecimento?: string
  observacoes?: string | null
  alunos?: { id: number; nome: string }[]
  cronograma?: { id: number; turma: string; bimestre: number; ano_letivo: number }
}

interface Boletim {
  id: number
  aluno_id: number
  ano_letivo: number
  linhas: {
    id: number
    disciplina: string
    professor: string | null
    b1_nota: number | null
    b1_faltas: number | null
    b2_nota: number | null
    b2_faltas: number | null
    b3_nota: number | null
    b3_faltas: number | null
    b4_nota: number | null
    b4_faltas: number | null
    nota_parcial: number | null
    bimestre_nota_parcial: number | null
  }[]
}

function fmtNota(valor: number | null | undefined) {
  if (valor == null) return '—'
  return valor.toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })
}

function fmtData(isoData: string | null, dataTexto: string) {
  if (dataTexto) return dataTexto
  if (!isoData) return '—'
  const [y, m, d] = isoData.split('-')
  return `${d}/${m}/${y}`
}

export default function Avaliacoes() {
  const user = useAuthStore((state) => state.user) as {
    id?: number
    is_child?: boolean
    is_superuser?: boolean
    family_id?: number | null
  } | null
  const filho = !!user?.is_child
  const anoAtual = new Date().getFullYear()
  const bimestrePadrao = String(Math.min(4, Math.ceil((new Date().getMonth() + 1) / 3)))

  const [aba, setAba] = useState<'avaliacoes' | 'boletim'>('avaliacoes')
  const [alunoId, setAlunoId] = useState('')
  const [bimestre, setBimestre] = useState(bimestrePadrao)
  const [anoLetivo, setAnoLetivo] = useState(String(anoAtual))
  const [disciplina, setDisciplina] = useState('')
  const [avaliacaoId, setAvaliacaoId] = useState<number | null>(null)

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

  const { data: avaliacoes = [], isLoading, isError } = useQuery<AvaliacaoLista[]>({
    queryKey: ['avaliacoes-eclass', alunoAtivo, bimestre, anoLetivo, disciplina],
    queryFn: async () => {
      const params: Record<string, string | number | boolean> = {
        so_eclass: true,
        incluir_sem_data: true,
        limite: 200,
      }
      if (alunoAtivo) params.aluno_id = Number(alunoAtivo)
      if (bimestre) params.bimestre = Number(bimestre)
      if (anoLetivo) params.ano_letivo = Number(anoLetivo)
      if (disciplina) params.disciplina = disciplina
      return (await api.get('/estudos/avaliacoes', { params })).data
    },
    enabled: aba === 'avaliacoes' && !!alunoAtivo,
  })

  const { data: detalhe } = useQuery<AvaliacaoLista>({
    queryKey: ['avaliacao', avaliacaoId],
    queryFn: async () => (await api.get(`/estudos/avaliacoes/${avaliacaoId}`)).data,
    enabled: avaliacaoId != null,
  })

  const {
    data: boletim,
    isLoading: carregandoBoletim,
    isError: erroBoletim,
  } = useQuery<Boletim>({
    queryKey: ['boletim', alunoAtivo, anoLetivo],
    queryFn: async () => (await api.get('/estudos/boletim', {
      params: { aluno_id: Number(alunoAtivo), ano_letivo: Number(anoLetivo || anoAtual) },
    })).data,
    enabled: !!alunoAtivo && !!anoLetivo,
    retry: false,
  })

  const notaParcialPorDisciplina = useMemo(() => {
    const mapa = new Map<string, number | null>()
    if (!boletim) return mapa
    const bim = bimestre ? Number(bimestre) : null
    boletim.linhas.forEach((linha) => {
      if (linha.nota_parcial != null && (bim == null || linha.bimestre_nota_parcial === bim)) {
        mapa.set(linha.disciplina, linha.nota_parcial)
      }
    })
    return mapa
  }, [boletim, bimestre])

  const disciplinas = useMemo(
    () => Array.from(new Set(avaliacoes.map((item) => item.disciplina))).sort((a, b) => a.localeCompare(b, 'pt-BR')),
    [avaliacoes],
  )

  const cartoes = useMemo(() => {
    const mapa = new Map<string, { professor: string | null; itens: AvaliacaoLista[] }>()
    avaliacoes.forEach((item) => {
      const atual = mapa.get(item.disciplina) || { professor: item.professor || null, itens: [] }
      if (!atual.professor && item.professor) atual.professor = item.professor
      atual.itens.push(item)
      mapa.set(item.disciplina, atual)
    })
    return Array.from(mapa.entries())
      .map(([nome, dados]) => ({
        disciplina: nome,
        professor: dados.professor,
        notaParcial: notaParcialPorDisciplina.get(nome) ?? null,
        itens: [...dados.itens].sort((a, b) => {
          const da = a.data_inicio || ''
          const db = b.data_inicio || ''
          return da.localeCompare(db)
        }),
      }))
      .sort((a, b) => a.disciplina.localeCompare(b.disciplina, 'pt-BR'))
  }, [avaliacoes, notaParcialPorDisciplina])

  const campo = 'min-h-12 w-full rounded-xl border border-gray-300 bg-white px-3 text-base'

  return (
    <div className="mx-auto w-full max-w-lg lg:max-w-5xl">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-xl font-bold text-gray-900 sm:text-2xl">
            <ClipboardCheck className="h-7 w-7 text-teal-700" />
            Avaliações
          </h1>
          <p className="mt-1 text-sm text-gray-600">
            Notas lançadas no e-class (varredura semanal). O calendário de provas fica em Provas.
          </p>
        </div>
        <div className="flex rounded-xl border border-gray-200 bg-white p-1 text-sm">
          <button
            type="button"
            onClick={() => setAba('avaliacoes')}
            className={`min-h-10 flex-1 rounded-lg px-3 sm:flex-none ${aba === 'avaliacoes' ? 'bg-teal-700 text-white' : 'text-gray-700'}`}
          >
            Avaliações
          </button>
          <button
            type="button"
            onClick={() => setAba('boletim')}
            className={`min-h-10 flex-1 rounded-lg px-3 sm:flex-none ${aba === 'boletim' ? 'bg-teal-700 text-white' : 'text-gray-700'}`}
          >
            Notas e Faltas
          </button>
        </div>
      </div>

      <div className="mb-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
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
        {aba === 'avaliacoes' && (
          <>
            <select value={bimestre} onChange={(e) => setBimestre(e.target.value)} className={campo} aria-label="Bimestre">
              {[1, 2, 3, 4].map((n) => <option key={n} value={n}>{n}º bimestre</option>)}
            </select>
            <select value={disciplina} onChange={(e) => setDisciplina(e.target.value)} className={campo} aria-label="Disciplina">
              <option value="">Todas as disciplinas</option>
              {disciplinas.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          </>
        )}
      </div>

      {aba === 'avaliacoes' && (
        <>
          {!alunoAtivo && (
            <p className="rounded-xl border border-dashed border-gray-300 bg-white p-6 text-gray-600">
              Selecione um filho para ver as avaliações do e-class.
            </p>
          )}
          {alunoAtivo && isLoading && <p className="text-gray-600">Carregando avaliações…</p>}
          {alunoAtivo && isError && <p className="text-red-700">Não foi possível carregar as avaliações.</p>}
          {alunoAtivo && !isLoading && !isError && cartoes.length === 0 && (
            <p className="rounded-xl border border-dashed border-gray-300 bg-white p-6 text-gray-600">
              Nenhuma avaliação do e-class neste bimestre. Elas aparecem após a varredura semanal
              (segunda) → sync do portal — não após importar o PDF de critérios.
            </p>
          )}
          <div className="space-y-4">
            {cartoes.map((cartao) => (
              <section key={cartao.disciplina} className="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
                <header className="flex flex-wrap items-end justify-between gap-2 border-b border-gray-100 bg-stone-50 px-4 py-3">
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900">{cartao.disciplina}</h2>
                    {cartao.professor && <p className="text-sm text-gray-600">Prof.: {cartao.professor}</p>}
                  </div>
                  <p className="text-sm text-gray-800">
                    <span className="text-gray-500">Nota Parcial </span>
                    <span className="text-base font-semibold">{fmtNota(cartao.notaParcial)}</span>
                  </p>
                </header>
                <div className="overflow-x-auto">
                  <table className="min-w-full text-left text-sm">
                    <thead className="bg-white text-xs uppercase tracking-wide text-gray-500">
                      <tr>
                        <th className="px-3 py-2 font-medium">Data</th>
                        <th className="px-3 py-2 font-medium">Tipo</th>
                        <th className="px-3 py-2 font-medium">Atividade</th>
                        <th className="px-3 py-2 font-medium text-right">Alcançado</th>
                        <th className="px-3 py-2 font-medium text-right">Valor</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {cartao.itens.map((item) => (
                        <tr
                          key={item.id}
                          className="cursor-pointer hover:bg-teal-50/50"
                          onClick={() => setAvaliacaoId(item.id)}
                        >
                          <td className="whitespace-nowrap px-3 py-2.5 text-gray-700">
                            {fmtData(item.data_inicio, item.data_texto)}
                          </td>
                          <td className="whitespace-nowrap px-3 py-2.5 font-medium text-teal-800">
                            {item.tipo_codigo_eclass || item.categoria_rotulo || item.categoria}
                          </td>
                          <td className="max-w-[14rem] px-3 py-2.5 text-gray-900 sm:max-w-md">
                            <span className="line-clamp-2">{item.titulo}</span>
                          </td>
                          <td className="whitespace-nowrap px-3 py-2.5 text-right font-semibold text-gray-900">
                            {fmtNota(item.nota_alcancada)}
                          </td>
                          <td className="whitespace-nowrap px-3 py-2.5 text-right text-gray-700">
                            {item.valor != null ? fmtNota(item.valor) : (item.valor_texto || '—')}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            ))}
          </div>
        </>
      )}

      {aba === 'boletim' && (
        <>
          {!alunoAtivo && (
            <p className="rounded-xl border border-dashed border-gray-300 bg-white p-6 text-gray-600">
              Selecione um filho para ver o boletim.
            </p>
          )}
          {alunoAtivo && carregandoBoletim && <p className="text-gray-600">Carregando boletim…</p>}
          {alunoAtivo && erroBoletim && (
            <p className="rounded-xl border border-dashed border-gray-300 bg-white p-6 text-gray-600">
              Ainda não há boletim sincronizado. Ele entra com a varredura de Notas e Faltas do e-class.
            </p>
          )}
          {boletim && (
            <div className="overflow-x-auto rounded-2xl border border-gray-200 bg-white">
              <table className="min-w-full text-left text-sm">
                <thead className="bg-stone-50 text-gray-700">
                  <tr>
                    <th className="px-3 py-3 font-medium">Disciplina</th>
                    {[1, 2, 3, 4].map((n) => (
                      <th key={n} className="px-3 py-3 font-medium whitespace-nowrap">{n}º</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {boletim.linhas.map((linha) => (
                    <tr key={linha.id}>
                      <td className="px-3 py-3 font-medium text-gray-900">
                        {linha.disciplina}
                        {linha.professor && (
                          <span className="mt-0.5 block text-xs font-normal text-gray-500">{linha.professor}</span>
                        )}
                      </td>
                      {([1, 2, 3, 4] as const).map((n) => {
                        const nota = linha[`b${n}_nota` as const]
                        const faltas = linha[`b${n}_faltas` as const]
                        return (
                          <td key={n} className="px-3 py-3 whitespace-nowrap text-gray-800">
                            <span className="font-medium">{fmtNota(nota)}</span>
                            {faltas != null && <span className="text-gray-500"> / {faltas}f</span>}
                          </td>
                        )
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      <Modal
        isOpen={avaliacaoId != null}
        onClose={() => setAvaliacaoId(null)}
        title={detalhe
          ? `${detalhe.disciplina} · ${detalhe.tipo_codigo_eclass || detalhe.categoria_rotulo || detalhe.categoria}`
          : 'Avaliação'}
      >
        {detalhe && (
          <div className="space-y-3 text-left text-sm text-gray-800">
            <h3 className="text-lg font-semibold text-gray-900">{detalhe.titulo}</h3>
            {detalhe.professor && <p>Prof.: {detalhe.professor}</p>}
            <dl className="grid grid-cols-2 gap-2">
              <div>
                <dt className="text-xs uppercase text-gray-500">Data</dt>
                <dd>{fmtData(detalhe.data_inicio, detalhe.data_texto)}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase text-gray-500">Tipo</dt>
                <dd className="font-medium">{detalhe.tipo_codigo_eclass || detalhe.categoria}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase text-gray-500">Alcançado</dt>
                <dd className="font-semibold">{fmtNota(detalhe.nota_alcancada)}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase text-gray-500">Valor</dt>
                <dd>{detalhe.valor != null ? fmtNota(detalhe.valor) : (detalhe.valor_texto || '—')}</dd>
              </div>
            </dl>
            {detalhe.composicao && detalhe.composicao.length > 0 && (
              <div>
                <p className="font-medium">Composição</p>
                <ul className="list-disc space-y-1 pl-5">
                  {detalhe.composicao.map((item, idx) => (
                    <li key={idx}>
                      {item.avaliacao || '—'}
                      {item.realizado_em ? ` em ${item.realizado_em}` : ''}
                      {item.nota_final != null ? ` → ${fmtNota(item.nota_final)}` : ''}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {detalhe.objeto_conhecimento && (
              <p className="whitespace-pre-wrap text-gray-700">{detalhe.objeto_conhecimento}</p>
            )}
            {detalhe.observacoes && <p className="whitespace-pre-wrap">{detalhe.observacoes}</p>}
          </div>
        )}
      </Modal>
    </div>
  )
}
