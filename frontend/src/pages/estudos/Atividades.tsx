import { useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ClipboardList, Plus, Pencil, Trash2, Search, ImagePlus, Eye, FileText, X } from 'lucide-react'
import { getDocument, GlobalWorkerOptions } from 'pdfjs-dist'
import pdfWorker from 'pdfjs-dist/build/pdf.worker.min.mjs?url'

GlobalWorkerOptions.workerSrc = pdfWorker
import api from '../../lib/api'
import { useAuthStore } from '../../stores/authStore'
import Button from '../../components/Button'
import Modal from '../../components/Modal'
import ConfirmDeleteModal from '../../components/ConfirmDeleteModal'

interface Atividade {
  id: number
  aluno_id: number
  aluno_nome: string
  titulo: string
  descricao: string
  disciplina: string
  professor: string
  data: string
  prazo_entrega: string
  status: 'pendente' | 'concluida'
  anexos: Anexo[]
  concluida_em: string | null
}

interface Anexo {
  name: string
  type: string
  size: number
}

interface AlunoOption {
  id: number
  username: string
  first_name: string
  last_name: string
  is_superuser: boolean
  is_active: boolean
  is_child?: boolean
  family_id?: number | null
}

interface FormState {
  aluno_id: number
  titulo: string
  descricao: string
  disciplina: string
  professor: string
  data: string
  prazo: string
}

const emptyForm: FormState = {
  aluno_id: 0,
  titulo: '',
  descricao: '',
  disciplina: '',
  professor: '',
  data: '',
  prazo: '',
}

function semAcento(valor: string) {
  return valor.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase()
}

function textosData(isoDate: string, prazo?: string) {
  const data = new Date(`${isoDate}T12:00:00`)
  const formatos = [
    isoDate,
    data.toLocaleDateString('pt-BR'),
    data.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' }),
    data.toLocaleDateString('pt-BR', { day: 'numeric', month: 'long' }),
    data.toLocaleDateString('pt-BR', { day: 'numeric', month: 'long', year: 'numeric' }),
    data.toLocaleDateString('pt-BR', { weekday: 'long' }),
    data.toLocaleDateString('pt-BR', { month: 'long' }),
  ]
  if (prazo) {
    const entrega = new Date(prazo)
    formatos.push(
      entrega.toLocaleDateString('pt-BR'),
      entrega.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' }),
      entrega.toLocaleDateString('pt-BR', { day: 'numeric', month: 'long', year: 'numeric' }),
    )
  }
  return formatos
}

function nomeAluno(aluno: AlunoOption) {
  const nome = `${aluno.first_name || ''} ${aluno.last_name || ''}`.trim()
  return nome || aluno.username
}

function formatDia(isoDate: string) {
  const data = new Date(`${isoDate}T12:00:00`)
  const semana = data.toLocaleDateString('pt-BR', { weekday: 'long' })
  const dia = data.getDate()
  const mes = data.toLocaleDateString('pt-BR', { month: 'short' }).replace('.', '')
  return `${semana}, ${dia}/${mes}`
}

function formatPrazoCurto(iso: string) {
  return new Date(iso).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })
}

function formatDataHora(iso: string) {
  return new Date(iso).toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatPrazoLongo(iso: string) {
  const data = new Date(iso)
  const dia = data.toLocaleDateString('pt-BR', { day: 'numeric', month: 'long' })
  const hora = data.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
  return `${dia} às ${hora}`
}

function diaDoPrazo(iso: string) {
  const data = new Date(iso)
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${data.getFullYear()}-${pad(data.getMonth() + 1)}-${pad(data.getDate())}`
}

function agruparPorPrazo(itens: Atividade[]) {
  const ordenados = [...itens].sort((a, b) => {
    const diferenca = new Date(a.prazo_entrega).getTime() - new Date(b.prazo_entrega).getTime()
    return diferenca !== 0 ? diferenca : a.id - b.id
  })
  const mapa = new Map<string, Atividade[]>()
  for (const item of ordenados) {
    const chave = diaDoPrazo(item.prazo_entrega)
    const lista = mapa.get(chave) ?? []
    lista.push(item)
    mapa.set(chave, lista)
  }
  return Array.from(mapa.entries())
}

function CartaoAtividade({
  atividade,
  isAdmin,
  onAbrir,
  onEditar,
  onExcluir,
}: {
  atividade: Atividade
  isAdmin: boolean
  onAbrir: (atividade: Atividade) => void
  onEditar: (atividade: Atividade) => void
  onExcluir: (atividade: Atividade) => void
}) {
  return (
    <article className="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
      <button
        type="button"
        onClick={() => onAbrir(atividade)}
        className="w-full px-4 py-4 text-left active:bg-indigo-50"
      >
        <div className="flex flex-wrap items-center gap-2">
          <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${atividade.status === 'concluida' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}`}>
            {atividade.status === 'concluida' ? 'Concluída' : 'Pendente'}
          </span>
          {atividade.disciplina && (
            <span className="text-sm text-gray-500">{atividade.disciplina}</span>
          )}
        </div>
        <p className="mt-2 text-lg font-semibold leading-snug text-gray-900">{atividade.titulo}</p>
        <p className="mt-1 text-base text-gray-700">Prazo: {formatPrazoCurto(atividade.prazo_entrega)}</p>
        {atividade.professor && (
          <p className="mt-0.5 text-sm text-gray-500">{atividade.professor}</p>
        )}
      </button>
      {isAdmin && (
        <div className="grid grid-cols-2 border-t border-gray-100">
          <button
            type="button"
            onClick={() => onEditar(atividade)}
            className="flex min-h-12 items-center justify-center gap-2 text-base text-blue-700 active:bg-blue-50"
          >
            <Pencil className="h-5 w-5" />
            Editar
          </button>
          <button
            type="button"
            onClick={() => onExcluir(atividade)}
            className="flex min-h-12 items-center justify-center gap-2 border-l border-gray-100 text-base text-red-700 active:bg-red-50"
          >
            <Trash2 className="h-5 w-5" />
            Excluir
          </button>
        </div>
      )}
    </article>
  )
}

function PaginasPdf({ url }: { url: string }) {
  const hostRef = useRef<HTMLDivElement>(null)
  const [falha, setFalha] = useState('')
  const [carregando, setCarregando] = useState(true)

  useEffect(() => {
    let cancelado = false
    const host = hostRef.current
    if (!host) return
    host.replaceChildren()
    setCarregando(true)
    setFalha('')
    let destruir = () => undefined as void
    fetch(url)
      .then((resposta) => resposta.arrayBuffer())
      .then((buffer) => getDocument({ data: new Uint8Array(buffer) }))
      .then((carregado) => {
        destruir = () => {
          carregado.destroy()
        }
        return carregado.promise
      })
      .then(async (pdf) => {
        for (let numero = 1; numero <= pdf.numPages; numero += 1) {
          if (cancelado) return
          const pagina = await pdf.getPage(numero)
          const base = pagina.getViewport({ scale: 1 })
          const largura = host.clientWidth || window.innerWidth
          const escala = (largura / base.width) * Math.min(2, window.devicePixelRatio || 1)
          const viewport = pagina.getViewport({ scale: escala })
          const canvas = document.createElement('canvas')
          const contexto = canvas.getContext('2d')
          if (!contexto) continue
          canvas.width = viewport.width
          canvas.height = viewport.height
          canvas.className = 'mb-3 w-full bg-white'
          canvas.style.width = '100%'
          canvas.style.height = 'auto'
          await pagina.render({ canvasContext: contexto, viewport }).promise
          if (!cancelado) host.appendChild(canvas)
          if (numero === 1) setCarregando(false)
        }
        if (!cancelado) setCarregando(false)
      })
      .catch(() => {
        if (!cancelado) {
          setCarregando(false)
          setFalha('Não foi possível mostrar o PDF.')
        }
      })
    return () => {
      cancelado = true
      destruir()
    }
  }, [url])

  return (
    <div className="min-h-0 flex-1 overflow-auto bg-neutral-800 px-2 py-3">
      {carregando && <p className="mb-3 text-center text-sm text-white">Abrindo PDF...</p>}
      {falha && <p className="text-center text-sm text-red-200">{falha}</p>}
      <div ref={hostRef} />
    </div>
  )
}

function GaleriaAnexos({
  atividade,
  isAdmin,
  onChange,
}: {
  atividade: Atividade
  isAdmin: boolean
  onChange: (atividade: Atividade) => void
}) {
  const [urls, setUrls] = useState<string[]>([])
  const [enviando, setEnviando] = useState(false)
  const [erro, setErro] = useState('')
  const [aberto, setAberto] = useState<number | null>(null)
  const anexos = atividade.anexos ?? []
  const chaveAnexos = anexos.map((item, indice) => `${indice}:${item.name}:${item.size}`).join('|')

  useEffect(() => {
    let ativo = true
    const criadas: string[] = []
    const carregar = async () => {
      try {
        for (let indice = 0; indice < anexos.length; indice += 1) {
          const resposta = await api.get(
            `/estudos/atividades/${atividade.id}/anexos/${indice}/download`,
            { responseType: 'blob' },
          )
          if (!ativo) return
          const tipo = anexos[indice]?.type || resposta.data.type || 'application/octet-stream'
          const arquivo = resposta.data.type === tipo ? resposta.data : new Blob([resposta.data], { type: tipo })
          criadas.push(URL.createObjectURL(arquivo))
        }
        if (ativo) setUrls([...criadas])
      } catch {
        if (ativo) setErro('Não foi possível abrir os anexos.')
      }
    }
    setUrls([])
    setErro('')
    if (anexos.length > 0) carregar()
    return () => {
      ativo = false
      criadas.forEach((url) => URL.revokeObjectURL(url))
    }
  }, [atividade.id, chaveAnexos])

  const enviar = async (arquivo: File) => {
    const corpo = new FormData()
    corpo.append('file', arquivo)
    setEnviando(true)
    setErro('')
    try {
      const resposta = await api.post<Atividade>(`/estudos/atividades/${atividade.id}/anexos`, corpo, {
        transformRequest: [(dados, headers) => {
          if (typeof headers.delete === 'function') headers.delete('Content-Type')
          else delete headers['Content-Type']
          return dados
        }],
      })
      onChange({ ...resposta.data, anexos: resposta.data.anexos ?? [] })
    } catch (error: any) {
      setErro(error.response?.data?.detail || 'Não foi possível enviar o arquivo.')
    } finally {
      setEnviando(false)
    }
  }

  const remover = async (indice: number) => {
    setErro('')
    try {
      const resposta = await api.delete<Atividade>(`/estudos/atividades/${atividade.id}/anexos/${indice}`)
      onChange({ ...resposta.data, anexos: resposta.data.anexos ?? [] })
    } catch (error: any) {
      setErro(error.response?.data?.detail || 'Não foi possível excluir o anexo.')
    }
  }

  const visualizar = (indice: number) => {
    if (!urls[indice]) {
      setErro('O arquivo ainda está carregando.')
      return
    }
    setErro('')
    setAberto(indice)
  }

  return (
    <div className="space-y-3">
      {anexos.length > 0 && (
        <div className="space-y-3">
          {anexos.map((anexo, indice) => {
            const url = urls[indice]
            const imagem = anexo.type.startsWith('image/')
            return (
              <article key={`${anexo.name}-${indice}`} className="overflow-hidden rounded-xl border border-gray-200 bg-white">
                {imagem && url && (
                  <img src={url} alt={anexo.name} className="h-44 w-full object-cover" />
                )}
                {!imagem && (
                  <div className="flex items-center gap-3 px-4 py-4">
                    <FileText className="h-6 w-6 shrink-0 text-red-600" />
                    <p className="truncate text-base text-gray-800">{anexo.name}</p>
                  </div>
                )}
                <div className={isAdmin ? 'grid grid-cols-2 border-t border-gray-100' : 'border-t border-gray-100'}>
                  <button
                    type="button"
                    onClick={() => visualizar(indice)}
                    disabled={!url}
                    className="flex min-h-12 items-center justify-center gap-2 text-base text-indigo-700 active:bg-indigo-50 disabled:text-gray-400"
                  >
                    <Eye className="h-5 w-5" />
                    {url ? 'Visualizar' : 'Carregando...'}
                  </button>
                  {isAdmin && (
                    <button
                      type="button"
                      onClick={() => remover(indice)}
                      className="flex min-h-12 items-center justify-center gap-2 border-l border-gray-100 text-base text-red-700 active:bg-red-50"
                    >
                      <Trash2 className="h-5 w-5" />
                      Remover
                    </button>
                  )}
                </div>
              </article>
            )
          })}
        </div>
      )}
      {isAdmin && (
        <label className="flex min-h-12 w-full cursor-pointer items-center justify-center gap-2 rounded-xl border border-dashed border-gray-300 px-3 text-base text-gray-700">
          <ImagePlus className="h-5 w-5" />
          {enviando ? 'Enviando...' : 'Adicionar imagem ou PDF'}
          <input
            type="file"
            accept="image/png,image/jpeg,.png,.jpg,.jpeg,application/pdf,.pdf"
            className="hidden"
            disabled={enviando}
            onChange={(evento) => {
              const arquivo = evento.target.files?.[0]
              evento.target.value = ''
              if (arquivo) enviar(arquivo)
            }}
          />
        </label>
      )}
      {erro && <p className="text-sm text-red-700">{erro}</p>}
      {aberto !== null && urls[aberto] && createPortal(
        <div className="fixed inset-0 z-[80] flex flex-col bg-neutral-900">
          <div className="flex items-center justify-between gap-3 bg-white px-3 py-2">
            <p className="truncate text-base font-medium text-gray-900">{anexos[aberto]?.name}</p>
            <button
              type="button"
              onClick={() => setAberto(null)}
              className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-gray-600"
              aria-label="Fechar visualização"
            >
              <X className="h-6 w-6" />
            </button>
          </div>
          {anexos[aberto]?.type.startsWith('image/') ? (
            <div className="flex min-h-0 flex-1 items-center justify-center overflow-auto bg-neutral-800 p-2">
              <img src={urls[aberto]} alt={anexos[aberto]?.name || 'Imagem'} className="max-h-full max-w-full object-contain" />
            </div>
          ) : (
            <PaginasPdf url={urls[aberto]} />
          )}
        </div>,
        document.body,
      )}
    </div>
  )
}

function toDateTimeLocal(iso: string) {
  const data = new Date(iso)
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${data.getFullYear()}-${pad(data.getMonth() + 1)}-${pad(data.getDate())}T${pad(data.getHours())}:${pad(data.getMinutes())}`
}

export default function Atividades() {
  const user = useAuthStore((state) => state.user)
  const isAdmin = !!user?.is_superuser
  const queryClient = useQueryClient()
  const [alunoFiltro, setAlunoFiltro] = useState<number | ''>('')
  const [selecionada, setSelecionada] = useState<Atividade | null>(null)
  const [form, setForm] = useState<FormState>(emptyForm)
  const [editando, setEditando] = useState<Atividade | null>(null)
  const [formAberto, setFormAberto] = useState(false)
  const [erro, setErro] = useState('')
  const [excluindo, setExcluindo] = useState<Atividade | null>(null)
  const [confirmarConclusao, setConfirmarConclusao] = useState(false)
  const [confirmarReabertura, setConfirmarReabertura] = useState(false)
  const [busca, setBusca] = useState('')
  const [recorte, setRecorte] = useState<'todas' | 'pendentes' | 'mes'>('todas')

  const { data: detalhe } = useQuery<Atividade>({
    queryKey: ['atividade', selecionada?.id],
    queryFn: async () => (await api.get<Atividade>(`/estudos/atividades/${selecionada!.id}`)).data,
    enabled: !!selecionada,
  })

  const { data: atividades = [], isError } = useQuery<Atividade[]>({
    queryKey: ['atividades', isAdmin ? alunoFiltro : 'minhas'],
    queryFn: async () => {
      const response = await api.get('/estudos/atividades', {
        params: isAdmin && alunoFiltro ? { aluno_id: alunoFiltro } : undefined,
      })
      return response.data
    },
    placeholderData: [],
    retry: false,
  })

  const { data: usuarios = [] } = useQuery<AlunoOption[]>({
    queryKey: ['users'],
    queryFn: async () => (await api.get('/users/')).data,
    enabled: isAdmin,
  })

  const filhos = usuarios.filter((aluno) => (
    aluno.is_active
    && aluno.is_child
    && !aluno.is_superuser
    && user?.family_id != null
    && aluno.family_id === user.family_id
  ))

  const agora = new Date()
  const nomeMes = agora.toLocaleDateString('pt-BR', { month: 'long' })

  const concluidaNesteMes = (item: Atividade) => {
    if (item.status !== 'concluida') return false
    const data = item.concluida_em ? new Date(item.concluida_em) : new Date(`${item.data}T12:00:00`)
    return data.getMonth() === agora.getMonth() && data.getFullYear() === agora.getFullYear()
  }

  const totalPendentes = atividades.filter((item) => item.status !== 'concluida').length
  const totalConcluidasMes = atividades.filter(concluidaNesteMes).length

  const visiveis = useMemo(() => {
    const termo = busca.trim().toLowerCase()
    return atividades.filter((item) => {
      if (recorte === 'pendentes' && item.status === 'concluida') return false
      if (recorte === 'mes' && !concluidaNesteMes(item)) return false
      if (!termo) return true
      const texto = semAcento([
        item.titulo,
        item.disciplina,
        item.descricao,
        item.professor,
        item.aluno_nome,
        ...textosData(item.data, item.prazo_entrega),
      ].join(' '))
      return texto.includes(semAcento(termo))
    })
  }, [atividades, busca, recorte])

  const grupos = useMemo(() => agruparPorPrazo(visiveis), [visiveis])

  const porFilho = useMemo(() => {
    if (!isAdmin) return []
    const mapa = new Map<number, Atividade[]>()
    for (const item of visiveis) {
      const lista = mapa.get(item.aluno_id) ?? []
      lista.push(item)
      mapa.set(item.aluno_id, lista)
    }
    if (!busca.trim() && recorte === 'todas') {
      for (const filho of filhos) {
        if (alunoFiltro && filho.id !== alunoFiltro) continue
        if (!mapa.has(filho.id)) mapa.set(filho.id, [])
      }
    }
    return Array.from(mapa.entries())
      .map(([id, itens]) => {
        const cadastro = filhos.find((filho) => filho.id === id)
        const nome = itens[0]?.aluno_nome || (cadastro ? nomeAluno(cadastro) : 'Filho')
        return {
          id,
          nome,
          pendentes: itens.filter((item) => item.status !== 'concluida').length,
          dias: agruparPorPrazo(itens),
        }
      })
      .sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'))
  }, [isAdmin, visiveis, filhos, busca, recorte, alunoFiltro])

  const salvar = useMutation({
    mutationFn: async () => {
      const payload = {
        aluno_id: form.aluno_id,
        titulo: form.titulo.trim(),
        descricao: form.descricao.trim(),
        disciplina: form.disciplina.trim(),
        professor: form.professor.trim(),
        data: form.data,
        prazo_entrega: new Date(form.prazo).toISOString(),
      }
      if (editando) {
        await api.put(`/estudos/atividades/${editando.id}`, payload)
      } else {
        await api.post('/estudos/atividades', payload)
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['atividades'] })
      setFormAberto(false)
      setEditando(null)
      setForm(emptyForm)
      setErro('')
    },
    onError: (error: any) => {
      setErro(error.response?.data?.detail || 'Não foi possível salvar a atividade.')
    },
  })

  const concluir = useMutation({
    mutationFn: async (id: number) => {
      const response = await api.post<Atividade>(`/estudos/atividades/${id}/concluir`)
      return response.data
    },
    onSuccess: (atividade) => {
      queryClient.invalidateQueries({ queryKey: ['atividades'] })
      setSelecionada(atividade)
      setConfirmarConclusao(false)
    },
  })

  const reabrir = useMutation({
    mutationFn: async (id: number) => {
      const response = await api.post<Atividade>(`/estudos/atividades/${id}/reabrir`)
      return response.data
    },
    onSuccess: (atividade) => {
      queryClient.invalidateQueries({ queryKey: ['atividades'] })
      setSelecionada(atividade)
      setConfirmarReabertura(false)
    },
  })

  const excluir = useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/estudos/atividades/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['atividades'] })
      setExcluindo(null)
      setSelecionada(null)
    },
  })

  const abrirNova = () => {
    setEditando(null)
    setForm(emptyForm)
    setErro('')
    setFormAberto(true)
  }

  const abrirEdicao = (atividade: Atividade) => {
    setEditando(atividade)
    setForm({
      aluno_id: atividade.aluno_id,
      titulo: atividade.titulo,
      descricao: atividade.descricao,
      disciplina: atividade.disciplina,
      professor: atividade.professor,
      data: atividade.data,
      prazo: toDateTimeLocal(atividade.prazo_entrega),
    })
    setErro('')
    setSelecionada(null)
    setFormAberto(true)
  }

  const enviar = () => {
    if (!form.aluno_id || !form.titulo.trim() || !form.data || !form.prazo) {
      setErro('Preencha filho, título, data e prazo de entrega.')
      return
    }
    salvar.mutate()
  }

  const atividadeAberta = selecionada && detalhe?.id === selecionada.id ? detalhe : selecionada
  const atualizarAnexos = (atividade: Atividade) => {
    setSelecionada(atividade)
    queryClient.setQueryData(['atividade', atividade.id], atividade)
  }

  const campo = 'mt-1 w-full rounded-xl border border-gray-300 px-3 py-3 text-base'

  return (
    <div className="mx-auto w-full max-w-lg lg:max-w-3xl">
      <div className="mb-4 flex flex-col gap-3">
        <h1 className="flex items-center gap-2 text-xl font-bold text-gray-900 sm:text-2xl">
          <ClipboardList className="h-7 w-7 shrink-0 text-indigo-600" />
          Atividades
        </h1>
        {isAdmin && (
          <div className="flex flex-col gap-2 sm:flex-row">
            <select
              value={alunoFiltro}
              onChange={(event) => setAlunoFiltro(event.target.value ? Number(event.target.value) : '')}
              className={campo}
              aria-label="Filtrar por filho"
            >
              <option value="">Todos os filhos</option>
              {filhos.map((aluno) => (
                <option key={aluno.id} value={aluno.id}>{nomeAluno(aluno)}</option>
              ))}
            </select>
            <Button onClick={abrirNova} className="flex min-h-12 w-full items-center justify-center gap-2 text-base sm:w-auto">
              <Plus className="h-5 w-5" />
              Nova atividade
            </Button>
          </div>
        )}
      </div>

      <div className="mb-3 grid grid-cols-2 gap-3">
        <button
          type="button"
          onClick={() => setRecorte((atual) => (atual === 'pendentes' ? 'todas' : 'pendentes'))}
          className={`rounded-2xl border px-4 py-3 text-left shadow-sm active:scale-[0.98] ${recorte === 'pendentes' ? 'border-amber-400 bg-amber-50' : 'border-gray-200 bg-white'}`}
          aria-pressed={recorte === 'pendentes'}
        >
          <p className="text-3xl font-bold text-amber-700">{totalPendentes}</p>
          <p className="mt-1 text-sm font-medium leading-tight text-gray-700">Pendentes</p>
        </button>
        <button
          type="button"
          onClick={() => setRecorte((atual) => (atual === 'mes' ? 'todas' : 'mes'))}
          className={`rounded-2xl border px-4 py-3 text-left shadow-sm active:scale-[0.98] ${recorte === 'mes' ? 'border-emerald-400 bg-emerald-50' : 'border-gray-200 bg-white'}`}
          aria-pressed={recorte === 'mes'}
        >
          <p className="text-3xl font-bold text-emerald-700">{totalConcluidasMes}</p>
          <p className="mt-1 text-sm font-medium capitalize leading-tight text-gray-700">Concluídas em {nomeMes}</p>
        </button>
      </div>

      <div className="relative mb-4">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
        <input
          value={busca}
          onChange={(event) => setBusca(event.target.value)}
          placeholder="Data, matéria ou descrição"
          aria-label="Pesquisar tarefas"
          className="w-full rounded-xl border border-gray-300 py-3 pl-10 pr-3 text-base"
        />
      </div>

      {isError && (
        <p className="mb-4 text-sm text-red-700">Não foi possível carregar as atividades.</p>
      )}

      {!isError && atividades.length === 0 && (
        <p className="text-gray-600">Nenhuma atividade por aqui.</p>
      )}

      {!isError && atividades.length > 0 && (isAdmin ? porFilho.length === 0 : grupos.length === 0) && (
        <p className="text-gray-600">Nenhuma tarefa encontrada.</p>
      )}

      {isAdmin && (
        <div className="space-y-5">
          {porFilho.map((filho) => (
            <section key={filho.id} className="overflow-hidden rounded-2xl border border-indigo-100">
              <header className="bg-indigo-50 px-4 py-3">
                <h2 className="text-lg font-bold text-indigo-950">{filho.nome}</h2>
                <p className="text-sm text-indigo-800">
                  {filho.pendentes} {filho.pendentes === 1 ? 'pendente' : 'pendentes'}
                  {filho.dias.length === 0 ? ' · nenhuma tarefa' : ''}
                </p>
              </header>
              <div className="space-y-4 bg-gray-50 px-3 py-3">
                {filho.dias.length === 0 && (
                  <p className="text-sm text-gray-600">Nenhuma tarefa deste filho.</p>
                )}
                {filho.dias.map(([dia, itens]) => (
                  <div key={dia}>
                    <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-gray-500">
                      Prazo {formatDia(dia)}
                    </h3>
                    <div className="space-y-2">
                      {itens.map((atividade) => (
                        <CartaoAtividade
                          key={atividade.id}
                          atividade={atividade}
                          isAdmin={isAdmin}
                          onAbrir={setSelecionada}
                          onEditar={abrirEdicao}
                          onExcluir={setExcluindo}
                        />
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </section>
          ))}
        </div>
      )}

      {!isAdmin && (
      <div className="space-y-6">
        {grupos.map(([dia, itens]) => (
          <section key={dia}>
            <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-gray-500">
              Prazo {formatDia(dia)}
            </h2>
            <div className="space-y-2">
              {itens.map((atividade) => (
                <CartaoAtividade
                  key={atividade.id}
                  atividade={atividade}
                  isAdmin={false}
                  onAbrir={setSelecionada}
                  onEditar={abrirEdicao}
                  onExcluir={setExcluindo}
                />
              ))}
            </div>
          </section>
        ))}
      </div>
      )}

      <Modal isOpen={!!selecionada && !confirmarConclusao && !confirmarReabertura} onClose={() => setSelecionada(null)} title="Atividade">
        {atividadeAberta && (
          <div className="space-y-4 text-left">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">{atividadeAberta.titulo}</h3>
                <p className="text-sm text-gray-500">Data: {formatDataHora(`${atividadeAberta.data}T00:00:00`)}</p>
                <p className="mt-2 text-sm text-gray-700">
                  Prazo: {formatPrazoCurto(atividadeAberta.prazo_entrega)}
                  {atividadeAberta.disciplina ? ` · ${atividadeAberta.disciplina}` : ''}
                  {atividadeAberta.professor ? ` · ${atividadeAberta.professor}` : ''}
                </p>
                {isAdmin && <p className="mt-1 text-sm text-indigo-700">{atividadeAberta.aluno_nome}</p>}
              </div>
              <div className="rounded-lg border border-indigo-200 px-3 py-2 text-sm text-indigo-800">
                <p className="text-xs uppercase tracking-wide">Prazo de entrega</p>
                <p className="font-medium">{formatPrazoLongo(atividadeAberta.prazo_entrega)}</p>
              </div>
            </div>
            <p className="whitespace-pre-wrap text-base leading-relaxed text-gray-800">{atividadeAberta.descricao || 'Sem descrição.'}</p>
            <GaleriaAnexos atividade={atividadeAberta} isAdmin={isAdmin} onChange={atualizarAnexos} />
            <p className="text-base font-medium text-gray-700">
              {atividadeAberta.status === 'concluida' ? 'Concluída' : 'Pendente'}
              {atividadeAberta.concluida_em ? ` em ${formatDataHora(atividadeAberta.concluida_em)}` : ''}
            </p>
            {!isAdmin && atividadeAberta.status !== 'concluida' && (
              <Button onClick={() => setConfirmarConclusao(true)} className="min-h-12 w-full text-base">
                Marcar como concluída
              </Button>
            )}
            {isAdmin && atividadeAberta.status === 'concluida' && (
              <Button variant="outline" onClick={() => setConfirmarReabertura(true)} className="min-h-12 w-full text-base">
                Voltar para pendente
              </Button>
            )}
          </div>
        )}
      </Modal>

      <Modal
        isOpen={confirmarConclusao && !!selecionada}
        onClose={() => setConfirmarConclusao(false)}
        title="Concluir atividade"
      >
        {selecionada && (
          <div className="space-y-4 text-left">
            <p className="text-gray-700">
              Confirmar que "{selecionada.titulo}" está concluída? Só um administrador pode deixar ela pendente de novo.
            </p>
            <div className="flex flex-col gap-2">
              <Button onClick={() => concluir.mutate(selecionada.id)} disabled={concluir.isPending} className="min-h-12 w-full text-base">
                {concluir.isPending ? 'Salvando...' : 'Confirmar'}
              </Button>
              <Button variant="outline" onClick={() => setConfirmarConclusao(false)} className="min-h-12 w-full text-base">
                Cancelar
              </Button>
            </div>
          </div>
        )}
      </Modal>

      <Modal
        isOpen={confirmarReabertura && !!selecionada}
        onClose={() => setConfirmarReabertura(false)}
        title="Voltar para pendente"
      >
        {selecionada && (
          <div className="space-y-4 text-left">
            <p className="text-gray-700">
              Deixar "{selecionada.titulo}" pendente de novo? O filho volta a ver essa tarefa em aberto.
            </p>
            <div className="flex flex-col gap-2">
              <Button onClick={() => reabrir.mutate(selecionada.id)} disabled={reabrir.isPending} className="min-h-12 w-full text-base">
                {reabrir.isPending ? 'Salvando...' : 'Confirmar'}
              </Button>
              <Button variant="outline" onClick={() => setConfirmarReabertura(false)} className="min-h-12 w-full text-base">
                Cancelar
              </Button>
            </div>
          </div>
        )}
      </Modal>

      <Modal
        isOpen={formAberto}
        onClose={() => setFormAberto(false)}
        title={editando ? 'Editar atividade' : 'Nova atividade'}
      >
        <div className="space-y-3 text-left">
          <label className="block text-sm font-medium text-gray-700">
            Filho
            <select
              value={form.aluno_id || ''}
              onChange={(event) => setForm({ ...form, aluno_id: Number(event.target.value) })}
              className={campo}
            >
              <option value="">Selecione</option>
              {filhos.map((aluno) => (
                <option key={aluno.id} value={aluno.id}>{nomeAluno(aluno)}</option>
              ))}
            </select>
          </label>
          <label className="block text-sm font-medium text-gray-700">
            Título
            <input
              value={form.titulo}
              onChange={(event) => setForm({ ...form, titulo: event.target.value })}
              className={campo}
            />
          </label>
          <label className="block text-sm font-medium text-gray-700">
            Descrição
            <textarea
              value={form.descricao}
              onChange={(event) => setForm({ ...form, descricao: event.target.value })}
              rows={3}
              className={campo}
            />
          </label>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block text-sm font-medium text-gray-700">
              Disciplina
              <input
                value={form.disciplina}
                onChange={(event) => setForm({ ...form, disciplina: event.target.value })}
                className={campo}
              />
            </label>
            <label className="block text-sm font-medium text-gray-700">
              Professor
              <input
                value={form.professor}
                onChange={(event) => setForm({ ...form, professor: event.target.value })}
                className={campo}
              />
            </label>
            <label className="block text-sm font-medium text-gray-700">
              Data
              <input
                type="date"
                value={form.data}
                onChange={(event) => setForm({ ...form, data: event.target.value })}
                className={campo}
              />
            </label>
            <label className="block text-sm font-medium text-gray-700">
              Prazo de entrega
              <input
                type="datetime-local"
                value={form.prazo}
                onChange={(event) => setForm({ ...form, prazo: event.target.value })}
                className={campo}
              />
            </label>
          </div>
          {erro && <p className="text-sm text-red-700">{erro}</p>}
          <div className="flex flex-col gap-2 pt-2">
            <Button onClick={enviar} disabled={salvar.isPending} className="min-h-12 w-full text-base">
              {salvar.isPending ? 'Salvando...' : 'Salvar'}
            </Button>
            <Button variant="outline" onClick={() => setFormAberto(false)} className="min-h-12 w-full text-base">
              Cancelar
            </Button>
          </div>
        </div>
      </Modal>

      <ConfirmDeleteModal
        isOpen={!!excluindo}
        onClose={() => setExcluindo(null)}
        message={excluindo ? `Excluir a atividade "${excluindo.titulo}"?` : ''}
        onConfirm={() => excluindo && excluir.mutate(excluindo.id)}
        isLoading={excluir.isPending}
      />
    </div>
  )
}
