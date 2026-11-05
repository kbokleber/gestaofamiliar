import { useMemo, useState } from 'react'
import { useQueries, useQuery } from '@tanstack/react-query'
import { LineChart } from 'lucide-react'
import api from '../../lib/api'
import { useAuthStore } from '../../stores/authStore'

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

interface BoletimLinha {
  id: number
  disciplina: string
  b1_nota: number | null
  b2_nota: number | null
  b3_nota: number | null
  b4_nota: number | null
}

interface Boletim {
  aluno_id: number
  ano_letivo: number
  linhas: BoletimLinha[]
}

interface Filho {
  id: number
  nome: string
}

const BIMESTRES = [1, 2, 3, 4] as const
const CORES = [
  '#0f766e', '#b45309', '#1d4ed8', '#be123c', '#6d28d9',
  '#047857', '#c2410c', '#0369a1', '#a16207', '#4338ca',
  '#0e7490', '#9f1239',
]

function notasDaLinha(linha: BoletimLinha): Array<number | null> {
  return [linha.b1_nota, linha.b2_nota, linha.b3_nota, linha.b4_nota]
}

function fmtNota(valor: number | null | undefined) {
  if (valor == null) return '—'
  return valor.toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })
}

function variacao(notas: Array<number | null>) {
  const preenchidas = notas.filter((nota): nota is number => nota != null)
  if (preenchidas.length < 2) return null
  return preenchidas[preenchidas.length - 1] - preenchidas[0]
}

interface Serie {
  id: string
  nome: string
  cor: string
  notas: Array<number | null>
}

function GraficoEvolucao({ series }: { series: Serie[] }) {
  const [ativo, setAtivo] = useState<string | null>(null)
  const largura = 640
  const altura = 280
  const margem = { esquerda: 36, direita: 12, topo: 16, base: 32 }
  const plotW = largura - margem.esquerda - margem.direita
  const plotH = altura - margem.topo - margem.base
  const yMax = 10
  const x = (indice: number) => margem.esquerda + (indice / (BIMESTRES.length - 1)) * plotW
  const y = (nota: number) => margem.topo + ((yMax - nota) / yMax) * plotH

  const visiveis = series.filter((serie) => serie.notas.some((nota) => nota != null))

  return (
    <div>
      <svg viewBox={`0 0 ${largura} ${altura}`} className="h-auto w-full" role="img" aria-label="Evolução das notas por bimestre">
        {[0, 2.5, 5, 7.5, 10].map((marca) => (
          <g key={marca}>
            <line x1={margem.esquerda} x2={largura - margem.direita} y1={y(marca)} y2={y(marca)} stroke="#e7e5e4" />
            <text x={margem.esquerda - 8} y={y(marca) + 4} textAnchor="end" className="fill-gray-500" fontSize="11">
              {marca.toLocaleString('pt-BR')}
            </text>
          </g>
        ))}
        {BIMESTRES.map((bimestre, indice) => (
          <text key={bimestre} x={x(indice)} y={altura - 8} textAnchor="middle" className="fill-gray-600" fontSize="12">
            {bimestre}º
          </text>
        ))}
        {visiveis.map((serie) => {
          const apagada = ativo != null && ativo !== serie.id
          const trechos: string[] = []
          let atual = ''
          serie.notas.forEach((nota, indice) => {
            if (nota == null) {
              if (atual) trechos.push(atual)
              atual = ''
              return
            }
            const ponto = `${x(indice)},${y(nota)}`
            atual = atual ? `${atual} ${ponto}` : ponto
          })
          if (atual) trechos.push(atual)
          return (
            <g key={serie.id} opacity={apagada ? 0.15 : 1}>
              {trechos.map((pontos, indiceTrecho) => (
                <polyline key={indiceTrecho} points={pontos} fill="none" stroke={serie.cor} strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" />
              ))}
              {serie.notas.map((nota, indice) => nota == null ? null : (
                <circle
                  key={indice}
                  cx={x(indice)}
                  cy={y(nota)}
                  r={ativo === serie.id ? 5.5 : 4}
                  fill={serie.cor}
                  stroke="white"
                  strokeWidth="1.5"
                >
                  <title>{`${serie.nome} · ${indice + 1}º bimestre: ${fmtNota(nota)}`}</title>
                </circle>
              ))}
            </g>
          )
        })}
      </svg>
      <ul className="mt-3 flex flex-wrap gap-2">
        {visiveis.map((serie) => (
          <li key={serie.id}>
            <button
              type="button"
              onClick={() => setAtivo((atual) => atual === serie.id ? null : serie.id)}
              className={`inline-flex min-h-9 items-center gap-2 rounded-full border px-3 text-sm ${ativo === serie.id ? 'border-gray-900 bg-gray-900 text-white' : 'border-gray-200 bg-white text-gray-800'}`}
              aria-pressed={ativo === serie.id}
            >
              <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: serie.cor }} />
              {serie.nome}
            </button>
          </li>
        ))}
      </ul>
      {visiveis.length === 0 && (
        <p className="text-sm text-gray-600">Ainda não há nota lançada neste ano.</p>
      )}
    </div>
  )
}

export default function Painel() {
  const user = useAuthStore((state) => state.user) as {
    id?: number
    first_name?: string
    last_name?: string
    username?: string
    is_child?: boolean
    is_superuser?: boolean
    family_id?: number | null
  } | null
  const filho = !!user?.is_child
  const anoAtual = new Date().getFullYear()
  const [anoLetivo, setAnoLetivo] = useState(String(anoAtual))
  const [alunoId, setAlunoId] = useState('')
  const [modo, setModo] = useState<'materias' | 'filhos'>('materias')
  const [disciplinaComparada, setDisciplinaComparada] = useState('')

  const { data: cronogramas = [] } = useQuery<CronogramaLista[]>({
    queryKey: ['cronogramas'],
    queryFn: async () => (await api.get('/estudos/cronogramas')).data,
    enabled: !filho,
  })

  const { data: usuarios = [] } = useQuery<AlunoOption[]>({
    queryKey: ['users'],
    queryFn: async () => (await api.get('/users/')).data,
    enabled: !filho && !!user?.is_superuser,
  })

  const filhos = useMemo<Filho[]>(() => {
    if (filho) {
      if (!user?.id) return []
      const nome = `${user.first_name || ''} ${user.last_name || ''}`.trim() || user.username || 'Você'
      return [{ id: user.id, nome }]
    }
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
  }, [filho, user, usuarios, cronogramas])

  const alunoAtivo = filho
    ? String(user?.id || '')
    : (alunoId || (filhos[0] ? String(filhos[0].id) : ''))
  const modoAtivo = filho ? 'materias' : modo

  const boletins = useQueries({
    queries: filhos.map((item) => ({
      queryKey: ['boletim-painel', item.id, anoLetivo],
      queryFn: async () => (await api.get<Boletim>('/estudos/boletim', {
        params: { aluno_id: item.id, ano_letivo: Number(anoLetivo) },
      })).data,
      enabled: !!anoLetivo,
      retry: false,
    })),
  })

  const porFilho = useMemo(() => {
    const mapa = new Map<number, BoletimLinha[]>()
    filhos.forEach((item, indice) => {
      mapa.set(item.id, boletins[indice]?.data?.linhas || [])
    })
    return mapa
  }, [filhos, boletins])

  const linhasAtivas = porFilho.get(Number(alunoAtivo)) || []
  const disciplinas = useMemo(() => {
    const nomes = new Set<string>()
    porFilho.forEach((linhas) => linhas.forEach((linha) => nomes.add(linha.disciplina)))
    return Array.from(nomes).sort((a, b) => a.localeCompare(b, 'pt-BR'))
  }, [porFilho])
  const materiaComparada = disciplinaComparada || disciplinas[0] || ''

  const seriesMaterias: Serie[] = linhasAtivas.map((linha, indice) => ({
    id: linha.disciplina,
    nome: linha.disciplina,
    cor: CORES[indice % CORES.length],
    notas: notasDaLinha(linha),
  }))

  const seriesFilhos: Serie[] = filhos.map((item, indice) => {
    const linha = (porFilho.get(item.id) || []).find((atual) => atual.disciplina === materiaComparada)
    return {
      id: String(item.id),
      nome: item.nome,
      cor: CORES[indice % CORES.length],
      notas: linha ? notasDaLinha(linha) : [null, null, null, null],
    }
  })

  const carregando = boletins.some((consulta) => consulta.isLoading)
  const campo = 'min-h-12 w-full rounded-xl border border-gray-300 bg-white px-3 text-base'

  return (
    <div className="mx-auto w-full max-w-lg lg:max-w-5xl">
      <div className="mb-4">
        <h1 className="flex items-center gap-2 text-xl font-bold text-gray-900 sm:text-2xl">
          <LineChart className="h-7 w-7 text-teal-700" />
          Painel
        </h1>
        <p className="mt-1 text-sm text-gray-600">
          {filho
            ? 'Evolução das suas notas, do 1º ao 4º bimestre. Você não vê as notas dos irmãos.'
            : 'Evolução das notas de cada filho, do 1º ao 4º bimestre. Pais veem todos; cada filho vê só as próprias.'}
        </p>
      </div>

      <div className="mb-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        <select value={anoLetivo} onChange={(e) => setAnoLetivo(e.target.value)} className={campo} aria-label="Ano letivo">
          {[anoAtual, anoAtual - 1].map((ano) => (
            <option key={ano} value={ano}>{ano}</option>
          ))}
        </select>
        {!filho && (
          <select value={alunoAtivo} onChange={(e) => setAlunoId(e.target.value)} className={campo} aria-label="Filho" disabled={modoAtivo === 'filhos'}>
            {filhos.map((item) => (
              <option key={item.id} value={item.id}>{item.nome}</option>
            ))}
          </select>
        )}
        {!filho && (
        <div className="flex rounded-xl border border-gray-200 bg-white p-1 text-sm sm:col-span-2">
          <button
            type="button"
            onClick={() => setModo('materias')}
            className={`min-h-10 flex-1 rounded-lg px-3 ${modoAtivo === 'materias' ? 'bg-teal-700 text-white' : 'text-gray-700'}`}
          >
            Por matéria
          </button>
          <button
            type="button"
            onClick={() => setModo('filhos')}
            disabled={filhos.length < 2}
            className={`min-h-10 flex-1 rounded-lg px-3 disabled:text-gray-400 ${modoAtivo === 'filhos' ? 'bg-teal-700 text-white' : 'text-gray-700'}`}
          >
            Comparar filhos
          </button>
        </div>
        )}
      </div>

      {modoAtivo === 'filhos' && (
        <select
          value={materiaComparada}
          onChange={(e) => setDisciplinaComparada(e.target.value)}
          className={`${campo} mb-4`}
          aria-label="Matéria"
        >
          {disciplinas.map((nome) => (
            <option key={nome} value={nome}>{nome}</option>
          ))}
        </select>
      )}

      <section className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
        <h2 className="text-base font-semibold text-gray-900">
          {modoAtivo === 'materias'
            ? (filho ? 'Suas notas' : `Notas de ${filhos.find((item) => String(item.id) === alunoAtivo)?.nome || '—'}`)
            : materiaComparada || 'Comparar filhos'}
        </h2>
        <p className="mb-2 text-sm text-gray-500">Toque numa legenda para destacar a linha.</p>
        {carregando && <p className="text-gray-600">Carregando notas…</p>}
        {!carregando && (
          <GraficoEvolucao series={modoAtivo === 'materias' ? seriesMaterias : seriesFilhos} />
        )}
      </section>

      {modoAtivo === 'materias' && !carregando && linhasAtivas.length > 0 && (
        <div className="mt-4 overflow-hidden rounded-2xl border border-gray-200 bg-white">
          <ul className="divide-y divide-gray-100">
            {linhasAtivas.map((linha) => {
              const delta = variacao(notasDaLinha(linha))
              return (
                <li key={linha.id} className="px-4 py-3">
                  <div className="flex items-baseline justify-between gap-3">
                    <p className="font-medium text-gray-900">{linha.disciplina}</p>
                    <p className={`text-sm font-medium ${delta == null ? 'text-gray-400' : delta >= 0 ? 'text-emerald-700' : 'text-rose-700'}`}>
                      {delta == null ? '—' : `${delta > 0 ? '+' : ''}${delta.toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}`}
                    </p>
                  </div>
                  <div className="mt-2 grid grid-cols-4 gap-2 text-center text-sm">
                    {notasDaLinha(linha).map((nota, indice) => (
                      <div key={indice} className="rounded-lg bg-stone-50 py-1.5">
                        <p className="text-[11px] text-gray-500">{indice + 1}º</p>
                        <p className="font-semibold text-gray-900">{fmtNota(nota)}</p>
                      </div>
                    ))}
                  </div>
                </li>
              )
            })}
          </ul>
        </div>
      )}
    </div>
  )
}
