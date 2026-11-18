import api from '../../lib/api'

export type Preposicao = 'em' | 'na' | 'no'

export interface Aparelho {
  id: number
  nome: string
  revogado: boolean
  bateria: number | null
  atualizado_em: string | null
  visto_em: string | null
}

export interface Crianca {
  id: number
  nome: string
  apelido: string | null
  family_id: number
  bateria: number | null
  atualizado_em: string | null
  ha_segundos: number | null
  latitude: number | null
  longitude: number | null
  accuracy_m: number | null
  speed_kmh: number | null
  status: {
    codigo: 'dentro' | 'fora' | 'sem_posicao' | 'sem_lugares'
    frase: string
    lugar_id: number | null
    lugar_nome: string | null
  }
  aparelhos: Aparelho[]
}

export interface Lugar {
  id: number
  family_id: number
  nome: string
  preposicao: Preposicao
  endereco: string | null
  latitude: number
  longitude: number
  raio_m: number
}

export interface LugarEntrada {
  nome: string
  preposicao: Preposicao
  endereco: string | null
  latitude: number
  longitude: number
  raio_m: number
}

export interface PontoTrajeto {
  id: number
  latitude: number
  longitude: number
  accuracy_m: number | null
  speed_kmh: number | null
  battery_level: number | null
  recorded_at: string
  device_id: number
  lacuna_antes: boolean
}

export interface Parada {
  inicio: string
  fim: string
  duracao_segundos: number
  latitude: number
  longitude: number
}

export interface EventoLugar {
  id: number
  tipo: 'chegada' | 'saida'
  frase: string
  lugar_nome: string
  lugar_id: number | null
  em: string
  latitude: number
  longitude: number
}

export interface Trajeto {
  crianca_id: number
  crianca_nome: string
  dia: string
  fuso: string
  inicio: string | null
  fim: string | null
  distancia_m: number
  distancia_km: number
  velocidade_media_kmh: number
  velocidade_maxima_kmh: number
  fonte_velocidade: 'pontos' | 'gps' | 'mista' | 'sem_dados'
  paradas: Parada[]
  pontos: PontoTrajeto[]
  eventos: EventoLugar[]
}

export interface Pareamento {
  codigo: string
  expira_em: string
  crianca_id: number
  crianca_nome: string
  validade_minutos: number
}

const BASE = '/localizacao'

export const localizacaoApi = {
  criancas: async () => (await api.get<Crianca[]>(`${BASE}/criancas`)).data,
  trajeto: async (criancaId: number, dia: string) =>
    (await api.get<Trajeto>(`${BASE}/criancas/${criancaId}/trajeto`, { params: { dia } })).data,
  lugares: async () => (await api.get<Lugar[]>(`${BASE}/lugares`)).data,
  criarLugar: async (dados: LugarEntrada) => (await api.post<Lugar>(`${BASE}/lugares`, dados)).data,
  editarLugar: async (id: number, dados: LugarEntrada) =>
    (await api.put<Lugar>(`${BASE}/lugares/${id}`, dados)).data,
  apagarLugar: async (id: number) => {
    await api.delete(`${BASE}/lugares/${id}`)
  },
  geocodificar: async (endereco: string) =>
    (await api.post<{ latitude: number; longitude: number; endereco_formatado: string }>(
      `${BASE}/lugares/geocodificar`,
      { endereco },
    )).data,
  parear: async (criancaId: number) =>
    (await api.post<Pareamento>(`${BASE}/pareamentos`, { child_user_id: criancaId })).data,
  salvarApelido: async (criancaId: number, apelido: string) =>
    (await api.put<{ crianca_id: number; apelido: string | null }>(
      `${BASE}/criancas/${criancaId}/apelido`,
      { apelido },
    )).data,
  revogar: async (aparelhoId: number) => {
    await api.post(`${BASE}/dispositivos/${aparelhoId}/revogar`)
  },
}

/** Mensagem de erro da API em português, com um texto padrão. */
export function mensagemDeErro(erro: unknown, padrao: string): string {
  const detalhe = (erro as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  return typeof detalhe === 'string' && detalhe.trim() ? detalhe : padrao
}

/** Mesma sugestão da API: Escola → na, Parque → no, o resto → em. */
export function sugerirPreposicao(nome: string): Preposicao {
  const primeiro = nome.trim().split(/\s+/)[0]?.toLowerCase() || ''
  if (['escola', 'praça', 'praca', 'faculdade', 'igreja', 'academia'].includes(primeiro)) return 'na'
  if (['colégio', 'colegio', 'parque', 'clube', 'curso'].includes(primeiro)) return 'no'
  return 'em'
}

export function hojeSaoPaulo(): string {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Sao_Paulo',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date())
}

export function formatarHora(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleTimeString('pt-BR', {
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'America/Sao_Paulo',
  })
}

export function haQuantoTempo(segundos: number | null): string {
  if (segundos == null) return 'sem envio'
  if (segundos < 60) return 'agora há pouco'
  const minutos = Math.round(segundos / 60)
  if (minutos < 60) return `há ${minutos} min`
  const horas = Math.round(minutos / 60)
  if (horas < 24) return `há ${horas} h`
  const dias = Math.round(horas / 24)
  return `há ${dias} ${dias === 1 ? 'dia' : 'dias'}`
}

export function formatarDuracao(segundos: number): string {
  const minutos = Math.round(segundos / 60)
  if (minutos < 60) return `${minutos} min`
  const horas = Math.floor(minutos / 60)
  const resto = minutos % 60
  return resto ? `${horas} h ${resto} min` : `${horas} h`
}

/** Cor da bateria: vermelho até 20%, amarelo até 50%, verde acima. */
export function corBateria(nivel: number | null): { texto: string; fundo: string; hex: string } {
  if (nivel == null) return { texto: 'text-gray-500', fundo: 'bg-gray-100', hex: '#6b7280' }
  if (nivel <= 20) return { texto: 'text-red-700', fundo: 'bg-red-100', hex: '#dc2626' }
  if (nivel <= 50) return { texto: 'text-amber-700', fundo: 'bg-amber-100', hex: '#d97706' }
  return { texto: 'text-green-700', fundo: 'bg-green-100', hex: '#16a34a' }
}
