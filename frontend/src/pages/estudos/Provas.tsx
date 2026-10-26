import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ChevronLeft, ChevronRight, FileText } from 'lucide-react'
import api from '../../lib/api'
import { useAuthStore } from '../../stores/authStore'
import Modal from '../../components/Modal'
import Button from '../../components/Button'

interface Evento {
  id: string
  tipo: 'avaliacao' | 'evento_escolar'
  avaliacao_id?: number
  evento_tipo?: string
  titulo_exibicao: string
  disciplina?: string
  categoria?: string
  titulo?: string
  inicio: string
  fim: string
  periodo?: boolean
  turma?: string | null
  cor: string
}

interface AvaliacaoDetalhe {
  id: number
  disciplina: string
  categoria: string
  categoria_rotulo: string | null
  titulo: string
  data_texto: string
  data_inicio: string | null
  data_fim: string | null
  ocorrencias: { data_inicio: string, data_fim: string, turma: string | null }[]
  valor: number | null
  valor_texto: string | null
  objeto_conhecimento: string
  criterio_correcao: string
  itens_criterio: { ordem: number, descricao: string, pontos: number | null, por_unidade: boolean, quantidade: number | null }[]
  material_necessario: string | null
  observacoes: string | null
  orientacoes_categoria: string | null
  alunos?: { id: number, nome: string }[]
  cronograma?: { id: number, turma: string, bimestre: number, ano_letivo: number }
  pdf?: { nome: string | null } | null
}

interface AlunoOption {
  id: number
  first_name: string
  last_name: string
  username: string
  is_active: boolean
  is_child?: boolean
  is_superuser: boolean
  family_id?: number | null
}

interface CronogramaLista {
  id: number
  turma: string
  bimestre: number
  ano_letivo: number
  alunos: { id: number, nome: string }[]
}

const CATEGORIAS = [
  ['AV1', 'AV1', '#43A047'],
  ['AV2', 'AV2', '#FB8C00'],
  ['REDACAO', 'Redação', '#8E24AA'],
  ['PRODUTIVIDADE', 'Produtividade', '#1E88E5'],
  ['RECUPERACAO', 'Recuperação', '#EF9A9A'],
] as const

function iso(data: Date) {
  const mes = String(data.getMonth() + 1).padStart(2, '0')
  const dia = String(data.getDate()).padStart(2, '0')
  return `${data.getFullYear()}-${mes}-${dia}`
}

function parseIso(valor: string) {
  const [ano, mes, dia] = valor.split('-').map(Number)
  return new Date(ano, mes - 1, dia)
}

function segunda(data: Date) {
  const copia = new Date(data)
  copia.setDate(copia.getDate() - ((copia.getDay() + 6) % 7))
  copia.setHours(0, 0, 0, 0)
  return copia
}

function diaUtil(data: Date) {
  const dia = data.getDay()
  return dia !== 0 && dia !== 6
}

function diasUteis(inicio: Date, fim: Date) {
  const dias: Date[] = []
  const cursor = new Date(inicio)
  while (cursor <= fim || dias.length % 5 !== 0) {
    if (diaUtil(cursor)) dias.push(new Date(cursor))
    cursor.setDate(cursor.getDate() + 1)
    if (dias.length > 40) break
  }
  return dias
}

function cobre(evento: Evento, dia: string) {
  return evento.inicio <= dia && evento.fim >= dia
}

function formatarDia(valor: string) {
  return parseIso(valor).toLocaleDateString('pt-BR', { weekday: 'long', day: '2-digit', month: 'short' })
}

export default function Provas() {
  const user = useAuthStore((state) => state.user) as { is_child?: boolean, is_superuser?: boolean, family_id?: number | null } | null
  const filho = !!user?.is_child
  const [visao, setVisao] = useState<'mes' | 'semana' | 'lista'>('mes')
  const [cursor, setCursor] = useState(() => {
    const hoje = new Date()
    hoje.setHours(0, 0, 0, 0)
    return hoje
  })
  const [alunoId, setAlunoId] = useState('')
  const [disciplina, setDisciplina] = useState('')
  const [categoria, setCategoria] = useState('')
  const [mostrarEventos, setMostrarEventos] = useState(true)
  const [diaAberto, setDiaAberto] = useState<string | null>(null)
  const [avaliacaoId, setAvaliacaoId] = useState<number | null>(null)
  const [eventoAberto, setEventoAberto] = useState<Evento | null>(null)

  const intervalo = useMemo(() => {
    if (visao === 'semana') {
      const inicio = segunda(cursor)
      const sexta = new Date(inicio)
      sexta.setDate(inicio.getDate() + 4)
      return { de: iso(inicio), ate: iso(sexta), dias: diasUteis(inicio, sexta) }
    }
    const primeiro = new Date(cursor.getFullYear(), cursor.getMonth(), 1)
    const ultimo = new Date(cursor.getFullYear(), cursor.getMonth() + 1, 0)
    const dias = diasUteis(segunda(primeiro), ultimo)
    return { de: iso(dias[0]), ate: iso(dias[dias.length - 1]), dias }
  }, [cursor, visao])

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

  const { data: baseEventos = [] } = useQuery<Evento[]>({
    queryKey: ['calendario-opcoes', intervalo.de, intervalo.ate, alunoId, mostrarEventos],
    queryFn: async () => (await api.get('/estudos/calendario', {
      params: {
        de: intervalo.de,
        ate: intervalo.ate,
        agrupar: 'evento',
        incluir_eventos_escolares: mostrarEventos,
        ...(alunoId ? { aluno_id: alunoId } : {}),
      },
    })).data,
  })

  const { data: eventos = [], isError } = useQuery<Evento[]>({
    queryKey: ['calendario', intervalo.de, intervalo.ate, alunoId, disciplina, categoria, mostrarEventos],
    queryFn: async () => (await api.get('/estudos/calendario', {
      params: {
        de: intervalo.de,
        ate: intervalo.ate,
        agrupar: 'evento',
        incluir_eventos_escolares: mostrarEventos,
        ...(alunoId ? { aluno_id: alunoId } : {}),
        ...(disciplina ? { disciplina } : {}),
        ...(categoria ? { categoria } : {}),
      },
    })).data,
  })

  const { data: detalhe } = useQuery<AvaliacaoDetalhe>({
    queryKey: ['avaliacao', avaliacaoId],
    queryFn: async () => (await api.get(`/estudos/avaliacoes/${avaliacaoId}`)).data,
    enabled: avaliacaoId != null,
  })

  const disciplinas = useMemo(
    () => Array.from(new Set(baseEventos.map((item) => item.disciplina).filter(Boolean))) as string[],
    [baseEventos],
  )
  const titulo = cursor.toLocaleDateString('pt-BR', visao === 'semana'
    ? { day: '2-digit', month: 'long', year: 'numeric' }
    : { month: 'long', year: 'numeric' })
  const diaSelecionado = diaAberto || iso(new Date())
  const doDia = eventos.filter((item) => cobre(item, diaSelecionado))

  const mover = (passo: number) => {
    const proxima = new Date(cursor)
    if (visao === 'semana') proxima.setDate(proxima.getDate() + passo * 7)
    else proxima.setMonth(proxima.getMonth() + passo)
    setCursor(proxima)
  }

  const abrir = (evento: Evento) => {
    if (evento.tipo === 'avaliacao' && evento.avaliacao_id) {
      setEventoAberto(null)
      setAvaliacaoId(evento.avaliacao_id)
      return
    }
    setAvaliacaoId(null)
    setEventoAberto(evento)
  }

  const abrirPdf = async () => {
    if (!detalhe?.cronograma) return
    const resposta = await api.get(`/estudos/cronogramas/${detalhe.cronograma.id}/pdf`, { responseType: 'blob' })
    const url = URL.createObjectURL(new Blob([resposta.data], { type: 'application/pdf' }))
    const aba = window.open(url)
    if (!aba) window.location.assign(url)
  }

  return (
    <div className="mx-auto w-full max-w-lg lg:max-w-5xl">
      <div className="mb-4 flex items-center justify-between gap-3">
        <h1 className="flex items-center gap-2 text-xl font-bold text-gray-900 sm:text-2xl">
          <FileText className="h-7 w-7 text-indigo-600" />
          Provas
        </h1>
        <div className="flex rounded-xl border border-gray-200 bg-white p-1 text-sm">
          {(['mes', 'semana', 'lista'] as const).map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setVisao(item)}
              className={`min-h-10 rounded-lg px-3 ${visao === item ? 'bg-indigo-600 text-white' : 'text-gray-700'}`}
            >
              {item === 'mes' ? 'Mês' : item === 'semana' ? 'Semana' : 'Lista'}
            </button>
          ))}
        </div>
      </div>

      <div className="mb-4 grid gap-2 sm:grid-cols-2">
        {!filho && (
          <select value={alunoId} onChange={(e) => setAlunoId(e.target.value)} className="min-h-12 rounded-xl border border-gray-300 bg-white px-3" aria-label="Filtrar por filho">
            <option value="">Todos os filhos</option>
            {filhos.map((aluno) => <option key={aluno.id} value={aluno.id}>{aluno.nome}</option>)}
          </select>
        )}
        <select value={disciplina} onChange={(e) => setDisciplina(e.target.value)} className="min-h-12 rounded-xl border border-gray-300 bg-white px-3" aria-label="Filtrar por disciplina">
          <option value="">Todas as disciplinas</option>
          {disciplinas.map((item) => <option key={item} value={item}>{item}</option>)}
        </select>
        <select value={categoria} onChange={(e) => setCategoria(e.target.value)} className="min-h-12 rounded-xl border border-gray-300 bg-white px-3" aria-label="Filtrar por categoria">
          <option value="">Todas as categorias</option>
          {CATEGORIAS.map(([valor, nome]) => <option key={valor} value={valor}>{nome}</option>)}
        </select>
        <label className="flex min-h-12 items-center gap-2 rounded-xl border border-gray-300 bg-white px-3 text-sm text-gray-700">
          <input type="checkbox" checked={mostrarEventos} onChange={(e) => setMostrarEventos(e.target.checked)} />
          Recessos e semanas de prova
        </label>
      </div>

      <div className="mb-3 flex flex-wrap gap-2 text-xs text-gray-600">
        {CATEGORIAS.map(([valor, nome, cor]) => (
          <span key={valor} className="inline-flex items-center gap-1">
            <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: cor }} />
            {nome}
          </span>
        ))}
      </div>

      <div className="mb-3 flex items-center justify-between">
        <button type="button" onClick={() => mover(-1)} className="flex h-11 w-11 items-center justify-center rounded-full hover:bg-gray-100" aria-label="Período anterior">
          <ChevronLeft />
        </button>
        <h2 className="text-lg font-semibold capitalize text-gray-900">{titulo}</h2>
        <button type="button" onClick={() => mover(1)} className="flex h-11 w-11 items-center justify-center rounded-full hover:bg-gray-100" aria-label="Próximo período">
          <ChevronRight />
        </button>
      </div>

      {isError && <p className="text-red-700">Não foi possível carregar o calendário.</p>}
      {!isError && eventos.length === 0 && (
        <p className="mb-4 text-gray-600">Nenhuma avaliação neste período.</p>
      )}

      {visao !== 'lista' && (
        <div className="overflow-hidden rounded-2xl border border-gray-200 bg-white">
          <div className="grid grid-cols-5 border-b border-gray-100 text-center text-xs font-medium uppercase text-gray-500">
            {['Seg', 'Ter', 'Qua', 'Qui', 'Sex'].map((dia) => <div key={dia} className="py-2">{dia}</div>)}
          </div>
          <div className="grid grid-cols-5">
            {intervalo.dias.map((dia) => {
              const chave = iso(dia)
              const itens = eventos.filter((item) => cobre(item, chave)).slice(0, 3)
              const fora = visao === 'mes' && dia.getMonth() !== cursor.getMonth()
              return (
                <div
                  key={chave}
                  className={`min-h-16 border-b border-r border-gray-100 p-1 text-left sm:min-h-24 ${fora ? 'bg-gray-50 text-gray-400' : ''} ${diaAberto === chave ? 'bg-indigo-50' : ''}`}
                >
                  <button type="button" onClick={() => setDiaAberto(chave)} className="text-xs font-medium">
                    {dia.getDate()}
                  </button>
                  <button type="button" onClick={() => setDiaAberto(chave)} className="mt-1 flex gap-1 sm:hidden" aria-label={`Eventos de ${chave}`}>
                    {itens.map((item) => <span key={item.id} className="h-2 w-2 rounded-full" style={{ backgroundColor: item.cor }} />)}
                  </button>
                  <span className="mt-1 hidden space-y-1 sm:block">
                    {itens.map((item) => (
                      <button
                        key={item.id}
                        type="button"
                        onClick={() => abrir(item)}
                        className="block w-full truncate rounded px-1 text-left text-[11px] text-white"
                        style={{ backgroundColor: item.cor }}
                      >
                        {item.titulo_exibicao}
                      </button>
                    ))}
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {(visao === 'lista' || diaAberto) && (
        <div className="mt-4 space-y-2">
          {visao !== 'lista' && <h3 className="font-medium capitalize text-gray-800">{formatarDia(diaSelecionado)}</h3>}
          {(visao === 'lista' ? eventos : doDia).length === 0 && <p className="text-gray-600">Nada neste dia.</p>}
          {(visao === 'lista' ? eventos : doDia).map((evento) => (
            <button key={evento.id} type="button" onClick={() => abrir(evento)} className="flex w-full items-start gap-3 rounded-xl border border-gray-200 bg-white p-3 text-left">
              <span className="mt-1 h-3 w-3 shrink-0 rounded-full" style={{ backgroundColor: evento.cor }} />
              <span>
                <span className="block text-xs text-gray-500">{formatarDia(evento.inicio)}{evento.fim !== evento.inicio ? ` a ${parseIso(evento.fim).toLocaleDateString('pt-BR')}` : ''}</span>
                <span className="font-medium text-gray-900">{evento.titulo_exibicao}</span>
              </span>
            </button>
          ))}
        </div>
      )}

      <Modal isOpen={avaliacaoId != null} onClose={() => setAvaliacaoId(null)} title={detalhe ? `${detalhe.disciplina} · ${detalhe.categoria_rotulo || detalhe.categoria}` : 'Avaliação'}>
        {detalhe && (
          <div className="space-y-3 text-left text-sm text-gray-800">
            <h3 className="text-lg font-semibold text-gray-900">{detalhe.titulo}</h3>
            <p>{detalhe.data_texto}</p>
            {detalhe.valor_texto && <p>Valor: {detalhe.valor_texto}</p>}
            {detalhe.objeto_conhecimento && (
              <p className="whitespace-pre-wrap"><span className="font-medium">Conteúdo</span>{'\n'}{detalhe.objeto_conhecimento}</p>
            )}
            {detalhe.criterio_correcao && (
              <p className="whitespace-pre-wrap"><span className="font-medium">Critério de correção</span>{'\n'}{detalhe.criterio_correcao}</p>
            )}
            {detalhe.itens_criterio.length > 0 && (
              <ul className="list-decimal space-y-1 pl-5">
                {detalhe.itens_criterio.map((item) => (
                  <li key={item.ordem}>
                    {item.descricao}
                    {item.pontos != null ? ` (${item.pontos.toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}${item.por_unidade ? ' cada' : ''})` : ''}
                  </li>
                ))}
              </ul>
            )}
            {detalhe.material_necessario && <p className="whitespace-pre-wrap">Material: {detalhe.material_necessario}</p>}
            {detalhe.observacoes && <p className="whitespace-pre-wrap">{detalhe.observacoes}</p>}
            {detalhe.orientacoes_categoria && <p className="whitespace-pre-wrap text-gray-600">{detalhe.orientacoes_categoria}</p>}
            {detalhe.pdf && (
              <Button onClick={abrirPdf} className="min-h-12 w-full">Abrir PDF original</Button>
            )}
          </div>
        )}
      </Modal>

      <Modal isOpen={!!eventoAberto} onClose={() => setEventoAberto(null)} title="Calendário escolar">
        {eventoAberto && (
          <p className="text-left text-gray-800">
            {eventoAberto.titulo_exibicao}
            <br />
            {formatarDia(eventoAberto.inicio)}
          </p>
        )}
      </Modal>
    </div>
  )
}
