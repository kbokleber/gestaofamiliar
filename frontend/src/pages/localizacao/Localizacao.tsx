import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Marker, Polyline, Tooltip } from 'react-leaflet'
import {
  BatteryFull, BatteryLow, BatteryMedium, Clock, Copy, Gauge, MapPin, Pencil, Plus, RefreshCw,
  Route, Search, Smartphone, Trash2,
} from 'lucide-react'
import Button from '../../components/Button'
import Modal from '../../components/Modal'
import ConfirmDeleteModal from '../../components/ConfirmDeleteModal'
import {
  corBateria, formatarDuracao, formatarHora, haQuantoTempo, hojeSaoPaulo, localizacaoApi,
  mensagemDeErro, sugerirPreposicao,
  type Aparelho, type Crianca, type Lugar, type LugarEntrada, type Pareamento, type Preposicao, type Sos, type Trajeto,
} from './api'
import { CirculosLugares, MapaBase, iconeBolinha, iconeGrupo } from './Mapa'
import { agruparProximos, casarFotos } from './fotosEGrupos'
import { checklistDoCelular, pendencias, type EstadoItemSite } from './checklistDoCelular'
import BaixarApp from './BaixarApp'
import { useAuthStore } from '../../stores/authStore'

type Aba = 'agora' | 'trajeto' | 'lugares' | 'celulares'

const ABAS: Array<{ id: Aba; nome: string; icone: typeof MapPin }> = [
  { id: 'agora', nome: 'Agora', icone: MapPin },
  { id: 'trajeto', nome: 'Trajeto', icone: Route },
  { id: 'lugares', nome: 'Lugares', icone: Pencil },
  { id: 'celulares', nome: 'Celulares', icone: Smartphone },
]

export default function Localizacao() {
  const [aba, setAba] = useState<Aba>('agora')
  const criancas = useQuery({
    queryKey: ['localizacao', 'criancas'],
    queryFn: localizacaoApi.criancas,
    refetchInterval: 60_000,
  })
  const lugares = useQuery({ queryKey: ['localizacao', 'lugares'], queryFn: localizacaoApi.lugares })

  const erro = criancas.error || lugares.error

  return (
    <div className="mx-auto w-full max-w-5xl space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h1 className="flex items-center gap-2 text-xl font-bold text-gray-900 sm:text-2xl">
          <MapPin className="h-7 w-7 text-purple-600" />
          Localização
        </h1>
        <button
          type="button"
          onClick={() => { void criancas.refetch(); void lugares.refetch() }}
          className="flex h-10 items-center gap-2 rounded-lg border border-gray-300 bg-white px-3 text-sm text-gray-700 hover:bg-gray-50"
          title="Atualizar"
        >
          <RefreshCw className={`h-4 w-4 ${criancas.isFetching ? 'animate-spin' : ''}`} />
          <span className="hidden sm:inline">Atualizar</span>
        </button>
      </div>

      <div className="grid grid-cols-4 gap-1 rounded-lg bg-gray-100 p-1" role="tablist">
        {ABAS.map(({ id, nome, icone: Icone }) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={aba === id}
            onClick={() => setAba(id)}
            className={`flex min-h-10 items-center justify-center gap-1.5 rounded-md px-2 text-sm font-medium ${
              aba === id ? 'bg-white text-purple-700 shadow' : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            <Icone className="hidden h-4 w-4 sm:block" />
            {nome}
          </button>
        ))}
      </div>

      {erro ? (
        <p className="rounded-lg bg-red-50 p-4 text-sm text-red-700">
          {mensagemDeErro(erro, 'Não foi possível carregar a localização.')}
        </p>
      ) : criancas.isLoading || lugares.isLoading ? (
        <p className="p-4 text-sm text-gray-500">Carregando...</p>
      ) : (
        <>
          {aba === 'agora' && <AbaAgora criancas={criancas.data || []} lugares={lugares.data || []} />}
          {aba === 'trajeto' && <AbaTrajeto criancas={criancas.data || []} lugares={lugares.data || []} />}
          {aba === 'lugares' && <AbaLugares lugares={lugares.data || []} />}
          {aba === 'celulares' && <AbaCelulares criancas={criancas.data || []} />}
        </>
      )}
    </div>
  )
}

function Bateria({ nivel, grande = false }: { nivel: number | null; grande?: boolean }) {
  const cor = corBateria(nivel)
  const Icone = nivel == null ? BatteryMedium : nivel <= 20 ? BatteryLow : nivel <= 50 ? BatteryMedium : BatteryFull
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full font-bold ${cor.fundo} ${cor.texto} ${
        grande ? 'px-3 py-1 text-xl' : 'px-2 py-0.5 text-sm'
      }`}
      title="Bateria do celular"
    >
      <Icone className={grande ? 'h-6 w-6' : 'h-4 w-4'} />
      {nivel == null ? '—' : `${nivel}%`}
    </span>
  )
}

function SemCriancas() {
  return (
    <p className="rounded-lg bg-white p-4 text-sm text-gray-600 shadow-sm">
      Nenhuma criança cadastrada na família. Em Administração › Usuários, marque a pessoa como "Filho".
    </p>
  )
}

// ---------------------------------------------------------------- Agora

function AbaAgora({ criancas, lugares }: { criancas: Crianca[]; lugares: Lugar[] }) {
  const comPosicao = criancas.filter((c) => c.latitude != null && c.longitude != null)
  const pontos = useMemo<[number, number][]>(
    () => [
      ...comPosicao.map((c) => [c.latitude!, c.longitude!] as [number, number]),
      ...(comPosicao.length ? [] : lugares.map((l) => [l.latitude, l.longitude] as [number, number])),
    ],
    [comPosicao, lugares],
  )
  const chave = `${comPosicao.map((c) => c.id).join(',')}|${lugares.length}`
  const membrosComFoto = useQuery({
    queryKey: ['localizacao', 'fotos'],
    queryFn: localizacaoApi.fotosDaFamilia,
    staleTime: 10 * 60 * 1000,
    retry: false,
  })
  const fotos = useMemo(() => casarFotos(criancas, membrosComFoto.data ?? []), [criancas, membrosComFoto.data])
  const queryClient = useQueryClient()
  const pedidosSos = useQuery({ queryKey: ['localizacao', 'sos'], queryFn: localizacaoApi.sos, refetchInterval: 30_000 })
  const sosAbertos = (pedidosSos.data ?? []).filter((pedido) => !pedido.visto_em)
  // Só o admin: SOS que não avisou ninguém (lista de destinatários sem ninguém com acesso).
  const ehAdmin = !!useAuthStore((state) => state.user)?.is_superuser
  const semDestinatario = useQuery({
    queryKey: ['localizacao', 'sos-sem-destinatario'],
    queryFn: localizacaoApi.sosSemDestinatario,
    enabled: ehAdmin,
    refetchInterval: 60_000,
    retry: false,
  })
  const comSos = new Set(sosAbertos.map((pedido) => pedido.pessoa_id))
  const visto = useMutation({
    mutationFn: (id: number) => localizacaoApi.marcarSosVisto(id),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['localizacao', 'sos'] }),
    onError: (e) => alert(mensagemDeErro(e, 'Não foi possível marcar como visto.')),
  })
  // Quem está a poucos metros de outra pessoa aparece no mesmo marcador, lado a lado.
  const grupos = useMemo(
    () => agruparProximos(comPosicao.map((c) => ({ ...c, latitude: c.latitude!, longitude: c.longitude! })), 30),
    [comPosicao],
  )

  if (criancas.length === 0) return <SemCriancas />

  return (
    <div className="space-y-4">
      {sosAbertos.map((pedido) => (
        <FaixaSos key={pedido.id} pedido={pedido} onVisto={() => visto.mutate(pedido.id)} ocupado={visto.isPending} />
      ))}
      {(semDestinatario.data ?? []).map((alerta) => (
        <div key={`sem-${alerta.id}`} role="alert" className="rounded-lg border-2 border-amber-500 bg-amber-50 p-4">
          <p className="font-bold text-amber-900">SOS de {alerta.nome} às {formatarHora(alerta.criado_em)} não avisou ninguém</p>
          <p className="text-sm text-amber-900">Motivo: {alerta.motivo}. Revise "Quem recebe o SOS" na aba Celulares.</p>
        </div>
      ))}
      <div className="grid gap-3 sm:grid-cols-2">
        {criancas.map((crianca) => (
          <div key={crianca.id} className="rounded-lg bg-white p-4 shadow-sm">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="text-lg font-semibold text-gray-900">
                  {crianca.nome}
                  {crianca.adulto && <span className="ml-2 rounded-full bg-teal-100 px-2 py-0.5 align-middle text-xs font-medium text-teal-800">Adulto</span>}
                </p>
                <p className={`mt-1 text-base ${crianca.status.codigo === 'dentro' ? 'font-medium text-purple-700' : 'text-gray-700'}`}>
                  {crianca.status.frase}
                </p>
              </div>
              <Bateria nivel={crianca.bateria} grande />
            </div>
            <p className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-gray-500">
              <span className="inline-flex items-center gap-1"><Clock className="h-3.5 w-3.5" />{haQuantoTempo(crianca.ha_segundos)}</span>
              {crianca.speed_kmh != null && crianca.speed_kmh > 0 && (
                <span className="inline-flex items-center gap-1"><Gauge className="h-3.5 w-3.5" />{crianca.speed_kmh} km/h</span>
              )}
              {crianca.accuracy_m != null && <span>precisão de {Math.round(crianca.accuracy_m)} m</span>}
            </p>
            {crianca.aparelhos.filter((a) => !a.revogado).length === 0 && (
              <p className="mt-2 text-xs text-amber-700">Nenhum celular pareado. Use a aba Celulares.</p>
            )}
          </div>
        ))}
      </div>

      <MapaBase pontos={pontos} chaveEnquadramento={chave} altura="h-[55vh] min-h-72">
        <CirculosLugares lugares={lugares} />
        {grupos.map((grupo) => (
          <Marker
            key={grupo.pessoas.map((p) => p.id).join('-')}
            position={[grupo.latitude, grupo.longitude]}
            icon={iconeGrupo(grupo.pessoas.map((p) => ({
              nome: p.nome, bateria: p.bateria, apelido: p.apelido, adulto: p.adulto, foto: fotos[p.id] ?? null,
              sos: comSos.has(p.id),
            })))}
          >
            <Tooltip direction="top">
              {grupo.pessoas.map((p) => (
                <div key={p.id}>{p.status.frase} · {haQuantoTempo(p.ha_segundos)}</div>
              ))}
            </Tooltip>
          </Marker>
        ))}
        {sosAbertos.filter((pedido) => pedido.latitude != null && pedido.longitude != null).map((pedido) => (
          <Marker key={`sos-${pedido.id}`} position={[pedido.latitude!, pedido.longitude!]} icon={iconeBolinha('#dc2626', 'SOS')}>
            <Tooltip direction="top">SOS de {pedido.nome} às {formatarHora(pedido.criado_em)}</Tooltip>
          </Marker>
        ))}
      </MapaBase>
      <p className="text-xs text-gray-500">Atualiza sozinho a cada minuto. Os círculos roxos são os lugares cadastrados.</p>
    </div>
  )
}

function FaixaSos({ pedido, onVisto, ocupado }: { pedido: Sos; onVisto: () => void; ocupado: boolean }) {
  return (
    <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-lg border-2 border-red-600 bg-red-50 p-4">
      <div className="min-w-0">
        <p className="text-lg font-bold text-red-800">SOS de {pedido.nome} às {formatarHora(pedido.criado_em)}</p>
        <p className="text-sm text-red-900">
          {pedido.posicao_em ? `Última posição às ${formatarHora(pedido.posicao_em)} (marcada no mapa)` : 'Sem posição conhecida'}
          {pedido.bateria != null ? ` · bateria ${pedido.bateria}%` : ''}
        </p>
      </div>
      <Button onClick={onVisto} disabled={ocupado} className="min-h-11">Visto</Button>
    </div>
  )
}

/** Quem recebe o SOS: só adultos da família que veem o mapa. Nenhum marcado = todos eles. */
function DestinatariosSos() {
  const queryClient = useQueryClient()
  const dados = useQuery({ queryKey: ['localizacao', 'sos-destinatarios'], queryFn: localizacaoApi.destinatariosSos })
  const [escolhidos, setEscolhidos] = useState<number[] | null>(null)
  const atuais = escolhidos ?? dados.data?.escolhidos ?? []
  const salvar = useMutation({
    mutationFn: () => localizacaoApi.salvarDestinatariosSos(dados.data!.family_id, atuais),
    onSuccess: () => {
      setEscolhidos(null)
      void queryClient.invalidateQueries({ queryKey: ['localizacao', 'sos-destinatarios'] })
    },
    onError: (e) => alert(mensagemDeErro(e, 'Não foi possível salvar quem recebe o SOS.')),
  })
  if (!dados.data) return null
  return (
    <div className="rounded-lg bg-white p-4 shadow-sm">
      <p className="text-lg font-semibold text-gray-900">Quem recebe o SOS</p>
      <p className="mt-1 text-sm text-gray-600">
        O botão SOS do app avisa só as pessoas marcadas, com nome, última posição, horário e bateria. Marque pelo menos 2 adultos: quem pede socorro não recebe o próprio aviso. Sem nenhuma marcada, avisa todos os adultos que veem o mapa.
      </p>
      {(dados.data.sem_acesso ?? []).length > 0 && (
        <p role="alert" className="mt-2 rounded-md bg-red-50 p-2 text-sm text-red-800">
          Destinatário sem acesso: {(dados.data.sem_acesso ?? []).map((p) => p.nome).join(', ')}. Continua na lista, mas não recebe o SOS até voltar a ter o menu Localização.
        </p>
      )}
      {atuais.length === 0 && (
        <p role="status" className="mt-2 rounded-md bg-amber-50 p-2 text-sm text-amber-800">
          Nenhum familiar marcado: hoje o SOS avisa todos os adultos que veem o mapa. Marque quem deve receber.
        </p>
      )}
      <div className="mt-3 space-y-2">
        {[...dados.data.opcoes, ...(dados.data.sem_acesso ?? []).map((p) => ({ ...p, semAcesso: true }))].map((pessoa) => (
          <label key={pessoa.id} className="flex min-h-11 items-center gap-3 text-base text-gray-800">
            <input
              type="checkbox"
              className="h-5 w-5"
              checked={atuais.includes(pessoa.id)}
              onChange={(e) => setEscolhidos(e.target.checked ? [...atuais, pessoa.id] : atuais.filter((id) => id !== pessoa.id))}
            />
            {pessoa.nome}
            {'semAcesso' in pessoa && <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-800">sem acesso</span>}
          </label>
        ))}
      </div>
      <Button onClick={() => salvar.mutate()} disabled={salvar.isPending || escolhidos == null} className="mt-3">
        Salvar
      </Button>
    </div>
  )
}

// ---------------------------------------------------------------- Trajeto

function AbaTrajeto({ criancas, lugares }: { criancas: Crianca[]; lugares: Lugar[] }) {
  const [criancaId, setCriancaId] = useState<number | null>(criancas[0]?.id ?? null)
  const [dia, setDia] = useState(hojeSaoPaulo())
  const trajeto = useQuery({
    queryKey: ['localizacao', 'trajeto', criancaId, dia],
    queryFn: () => localizacaoApi.trajeto(criancaId!, dia),
    enabled: criancaId != null && !!dia,
  })

  if (criancas.length === 0) return <SemCriancas />

  return (
    <div className="space-y-4">
      <div className="grid gap-3 rounded-lg bg-white p-4 shadow-sm sm:grid-cols-2">
        <label className="text-sm font-medium text-gray-700">
          Pessoa
          <select
            value={criancaId ?? ''}
            onChange={(e) => setCriancaId(Number(e.target.value))}
            className="mt-1 block min-h-11 w-full rounded-lg border border-gray-300 px-3"
          >
            {criancas.map((c) => <option key={c.id} value={c.id}>{c.nome}{c.adulto ? ' (adulto)' : ''}</option>)}
          </select>
        </label>
        <label className="text-sm font-medium text-gray-700">
          Dia
          <input
            type="date"
            value={dia}
            max={hojeSaoPaulo()}
            onChange={(e) => setDia(e.target.value)}
            className="mt-1 block min-h-11 w-full rounded-lg border border-gray-300 px-3"
          />
        </label>
      </div>

      {trajeto.isLoading ? (
        <p className="p-4 text-sm text-gray-500">Carregando trajeto...</p>
      ) : trajeto.error ? (
        <p className="rounded-lg bg-red-50 p-4 text-sm text-red-700">
          {mensagemDeErro(trajeto.error, 'Não foi possível carregar o trajeto.')}
        </p>
      ) : trajeto.data ? (
        <DetalheTrajeto trajeto={trajeto.data} lugares={lugares} />
      ) : null}
    </div>
  )
}

function DetalheTrajeto({ trajeto, lugares }: { trajeto: Trajeto; lugares: Lugar[] }) {
  // Divide o percurso nas lacunas (trecho sem sinal), que aparecem tracejadas.
  const { trechos, lacunas } = useMemo(() => {
    const trechos: [number, number][][] = []
    const lacunas: [number, number][][] = []
    let atual: [number, number][] = []
    trajeto.pontos.forEach((ponto, i) => {
      const pos: [number, number] = [ponto.latitude, ponto.longitude]
      if (ponto.lacuna_antes && i > 0) {
        const anterior = trajeto.pontos[i - 1]
        lacunas.push([[anterior.latitude, anterior.longitude], pos])
        if (atual.length > 1) trechos.push(atual)
        atual = []
      }
      atual.push(pos)
    })
    if (atual.length > 1) trechos.push(atual)
    return { trechos, lacunas }
  }, [trajeto])

  const pontos = trajeto.pontos.map((p) => [p.latitude, p.longitude] as [number, number])
  const primeiro = trajeto.pontos[0]
  const ultimo = trajeto.pontos[trajeto.pontos.length - 1]

  if (trajeto.pontos.length === 0) {
    return (
      <p className="rounded-lg bg-white p-4 text-sm text-gray-600 shadow-sm">
        {trajeto.crianca_nome} não enviou localização neste dia.
      </p>
    )
  }

  const numeros = [
    { rotulo: 'Distância', valor: `${trajeto.distancia_km.toLocaleString('pt-BR')} km` },
    { rotulo: 'Velocidade média', valor: `${trajeto.velocidade_media_kmh.toLocaleString('pt-BR')} km/h` },
    { rotulo: 'Velocidade máxima', valor: `${trajeto.velocidade_maxima_kmh.toLocaleString('pt-BR')} km/h` },
    { rotulo: 'Início e fim', valor: `${formatarHora(trajeto.inicio)} – ${formatarHora(trajeto.fim)}` },
  ]

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {numeros.map((n) => (
          <div key={n.rotulo} className="rounded-lg bg-white p-3 shadow-sm">
            <p className="text-xs text-gray-500">{n.rotulo}</p>
            <p className="text-lg font-semibold text-gray-900">{n.valor}</p>
          </div>
        ))}
      </div>

      <MapaBase pontos={pontos} chaveEnquadramento={`${trajeto.crianca_id}|${trajeto.dia}|${pontos.length}`} altura="h-[50vh] min-h-72">
        <CirculosLugares lugares={lugares} />
        {trechos.map((linha, i) => (
          <Polyline key={`t${i}`} positions={linha} pathOptions={{ color: '#7c3aed', weight: 4 }} />
        ))}
        {lacunas.map((linha, i) => (
          <Polyline key={`l${i}`} positions={linha} pathOptions={{ color: '#9ca3af', weight: 3, dashArray: '6 8' }}>
            <Tooltip sticky>Sem sinal neste trecho</Tooltip>
          </Polyline>
        ))}
        {trajeto.paradas.map((parada, i) => (
          <Marker key={`p${i}`} position={[parada.latitude, parada.longitude]} icon={iconeBolinha('#d97706', 'P')}>
            <Tooltip direction="top">
              Parada de {formatarDuracao(parada.duracao_segundos)} ({formatarHora(parada.inicio)} – {formatarHora(parada.fim)})
            </Tooltip>
          </Marker>
        ))}
        <Marker position={[primeiro.latitude, primeiro.longitude]} icon={iconeBolinha('#16a34a', 'I')}>
          <Tooltip direction="top">Início {formatarHora(primeiro.recorded_at)}</Tooltip>
        </Marker>
        {trajeto.pontos.length > 1 && (
          <Marker position={[ultimo.latitude, ultimo.longitude]} icon={iconeBolinha('#dc2626', 'F')}>
            <Tooltip direction="top">Fim {formatarHora(ultimo.recorded_at)}</Tooltip>
          </Marker>
        )}
      </MapaBase>
      <p className="text-xs text-gray-500">
        I = início, F = fim, P = parada. A linha tracejada é um trecho sem sinal, que não entra na distância.
        {trajeto.fonte_velocidade === 'pontos' && ' A velocidade foi calculada pelos pontos, porque o GPS não informou.'}
      </p>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-lg bg-white p-4 shadow-sm">
          <h3 className="mb-2 font-semibold text-gray-900">Chegadas e saídas</h3>
          {trajeto.eventos.length === 0 ? (
            <p className="text-sm text-gray-500">Nenhuma chegada ou saída de lugar cadastrado neste dia.</p>
          ) : (
            <ul className="divide-y divide-gray-100">
              {trajeto.eventos.map((evento) => (
                <li key={evento.id} className="flex items-center justify-between gap-3 py-2 text-sm">
                  <span className={evento.tipo === 'chegada' ? 'text-green-700' : 'text-gray-700'}>{evento.frase}</span>
                  <span className="text-gray-500">{formatarHora(evento.em)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="rounded-lg bg-white p-4 shadow-sm">
          <h3 className="mb-2 font-semibold text-gray-900">Paradas</h3>
          {trajeto.paradas.length === 0 ? (
            <p className="text-sm text-gray-500">Nenhuma parada de 5 minutos ou mais.</p>
          ) : (
            <ul className="divide-y divide-gray-100">
              {trajeto.paradas.map((parada, i) => (
                <li key={i} className="flex items-center justify-between gap-3 py-2 text-sm">
                  <span className="text-gray-700">{formatarHora(parada.inicio)} – {formatarHora(parada.fim)}</span>
                  <span className="text-gray-500">{formatarDuracao(parada.duracao_segundos)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------- Lugares

const LUGAR_VAZIO: LugarEntrada = { nome: '', preposicao: 'em', endereco: '', latitude: NaN, longitude: NaN, raio_m: 150 }

function AbaLugares({ lugares }: { lugares: Lugar[] }) {
  const queryClient = useQueryClient()
  const [editando, setEditando] = useState<{ id: number | null; dados: LugarEntrada } | null>(null)
  const [apagar, setApagar] = useState<Lugar | null>(null)

  const atualizar = () => {
    void queryClient.invalidateQueries({ queryKey: ['localizacao'] })
  }
  const remover = useMutation({
    mutationFn: (id: number) => localizacaoApi.apagarLugar(id),
    onSuccess: () => { setApagar(null); atualizar() },
    onError: (e) => alert(mensagemDeErro(e, 'Não foi possível apagar o lugar.')),
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm text-gray-600">Casa, Escola e outros lugares. O raio define quando a criança "está" no lugar.</p>
        <Button onClick={() => setEditando({ id: null, dados: { ...LUGAR_VAZIO } })} className="flex shrink-0 items-center gap-1">
          <Plus className="h-4 w-4" /> Novo lugar
        </Button>
      </div>

      {lugares.length === 0 ? (
        <p className="rounded-lg bg-white p-4 text-sm text-gray-600 shadow-sm">Nenhum lugar cadastrado ainda.</p>
      ) : (
        <ul className="divide-y divide-gray-100 rounded-lg bg-white shadow-sm">
          {lugares.map((lugar) => (
            <li key={lugar.id} className="flex items-center justify-between gap-3 p-3">
              <div className="min-w-0">
                <p className="font-medium text-gray-900">{lugar.nome}</p>
                <p className="truncate text-xs text-gray-500">
                  {lugar.endereco || `${lugar.latitude.toFixed(5)}, ${lugar.longitude.toFixed(5)}`} · raio de {lugar.raio_m} m
                </p>
              </div>
              <div className="flex shrink-0 gap-1">
                <button
                  type="button"
                  onClick={() => setEditando({ id: lugar.id, dados: { ...lugar, endereco: lugar.endereco || '' } })}
                  className="flex h-10 w-10 items-center justify-center rounded-full text-gray-600 hover:bg-gray-100"
                  aria-label={`Editar ${lugar.nome}`}
                >
                  <Pencil className="h-4 w-4" />
                </button>
                <button
                  type="button"
                  onClick={() => setApagar(lugar)}
                  className="flex h-10 w-10 items-center justify-center rounded-full text-red-600 hover:bg-red-50"
                  aria-label={`Apagar ${lugar.nome}`}
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      {lugares.length > 0 && (
        <MapaBase
          pontos={lugares.map((l) => [l.latitude, l.longitude] as [number, number])}
          chaveEnquadramento={lugares.map((l) => `${l.id}:${l.latitude}:${l.longitude}`).join(',')}
        >
          <CirculosLugares lugares={lugares} />
        </MapaBase>
      )}

      {editando && (
        <FormularioLugar
          id={editando.id}
          inicial={editando.dados}
          outros={lugares.filter((l) => l.id !== editando.id)}
          onFechar={() => setEditando(null)}
          onSalvo={() => { setEditando(null); atualizar() }}
        />
      )}

      <ConfirmDeleteModal
        isOpen={!!apagar}
        onClose={() => setApagar(null)}
        title="Apagar lugar"
        message={apagar ? <>Apagar o lugar <strong>{apagar.nome}</strong>? As chegadas e saídas antigas continuam no histórico.</> : ''}
        confirmLabel="Apagar"
        onConfirm={() => apagar && remover.mutate(apagar.id)}
        isLoading={remover.isPending}
      />
    </div>
  )
}

function FormularioLugar({
  id, inicial, outros, onFechar, onSalvo,
}: {
  id: number | null
  inicial: LugarEntrada
  outros: Lugar[]
  onFechar: () => void
  onSalvo: () => void
}) {
  const [dados, setDados] = useState<LugarEntrada>(inicial)
  const [preposicaoManual, setPreposicaoManual] = useState(id != null)
  const [buscando, setBuscando] = useState(false)
  const [aviso, setAviso] = useState('')
  const temPonto = Number.isFinite(dados.latitude) && Number.isFinite(dados.longitude)

  const salvar = useMutation({
    mutationFn: () => {
      const corpo = { ...dados, nome: dados.nome.trim(), endereco: dados.endereco?.trim() || null }
      return id == null ? localizacaoApi.criarLugar(corpo) : localizacaoApi.editarLugar(id, corpo)
    },
    onSuccess: onSalvo,
    onError: (e) => setAviso(mensagemDeErro(e, 'Não foi possível salvar o lugar.')),
  })

  const buscarEndereco = async () => {
    if (!dados.endereco || dados.endereco.trim().length < 3) {
      setAviso('Digite o endereço para buscar.')
      return
    }
    setBuscando(true)
    setAviso('')
    try {
      const achado = await localizacaoApi.geocodificar(dados.endereco.trim())
      setDados((d) => ({ ...d, latitude: achado.latitude, longitude: achado.longitude }))
      setAviso(`Encontrado: ${achado.endereco_formatado}. Confira no mapa e, se precisar, clique no ponto certo.`)
    } catch (e) {
      setAviso(mensagemDeErro(e, 'Endereço não encontrado. Clique no mapa para marcar o ponto.'))
    } finally {
      setBuscando(false)
    }
  }

  const frase = dados.nome.trim() ? `Fulano está ${dados.preposicao} ${dados.nome.trim()}` : ''
  const podeSalvar = dados.nome.trim().length > 0 && temPonto && !salvar.isPending

  return (
    <Modal isOpen onClose={onFechar} title={id == null ? 'Novo lugar' : 'Editar lugar'}>
      <form
        className="space-y-4"
        onSubmit={(e) => { e.preventDefault(); if (podeSalvar) salvar.mutate() }}
      >
        <div className="grid grid-cols-[1fr_auto] gap-3">
          <label className="text-sm font-medium text-gray-700">
            Nome
            <input
              value={dados.nome}
              maxLength={80}
              required
              placeholder="Casa, Escola..."
              onChange={(e) => {
                const nome = e.target.value
                setDados((d) => ({ ...d, nome, preposicao: preposicaoManual ? d.preposicao : sugerirPreposicao(nome) }))
              }}
              className="mt-1 block min-h-11 w-full rounded-lg border border-gray-300 px-3"
            />
          </label>
          <label className="text-sm font-medium text-gray-700">
            Frase
            <select
              value={dados.preposicao}
              onChange={(e) => { setPreposicaoManual(true); setDados((d) => ({ ...d, preposicao: e.target.value as Preposicao })) }}
              className="mt-1 block min-h-11 rounded-lg border border-gray-300 px-2"
            >
              <option value="em">está em</option>
              <option value="na">está na</option>
              <option value="no">está no</option>
            </select>
          </label>
        </div>
        {frase && <p className="-mt-2 text-xs text-gray-500">Vai aparecer assim: "{frase}"</p>}

        <div>
          <label className="text-sm font-medium text-gray-700" htmlFor="lugar-endereco">Endereço</label>
          <div className="mt-1 flex gap-2">
            <input
              id="lugar-endereco"
              value={dados.endereco || ''}
              maxLength={200}
              placeholder="Rua, número, cidade"
              onChange={(e) => setDados((d) => ({ ...d, endereco: e.target.value }))}
              onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); void buscarEndereco() } }}
              className="block min-h-11 w-full rounded-lg border border-gray-300 px-3"
            />
            <Button type="button" variant="outline" onClick={() => { void buscarEndereco() }} disabled={buscando} className="flex shrink-0 items-center gap-1">
              <Search className="h-4 w-4" /> {buscando ? 'Buscando...' : 'Buscar'}
            </Button>
          </div>
        </div>

        <div>
          <p className="mb-1 text-sm font-medium text-gray-700">Ponto no mapa (clique para marcar)</p>
          <MapaBase
            pontos={temPonto ? [[dados.latitude, dados.longitude]] : outros.map((l) => [l.latitude, l.longitude] as [number, number])}
            chaveEnquadramento={temPonto ? `${dados.latitude.toFixed(4)},${dados.longitude.toFixed(4)}` : 'sem-ponto'}
            altura="h-64"
            onClique={(lat, lng) => setDados((d) => ({ ...d, latitude: lat, longitude: lng }))}
          >
            <CirculosLugares lugares={outros} />
            {temPonto && (
              <>
                <CirculosLugares lugares={[{ id: -1, family_id: 0, nome: dados.nome || 'Novo lugar', preposicao: dados.preposicao, endereco: null, latitude: dados.latitude, longitude: dados.longitude, raio_m: dados.raio_m }]} />
                <Marker position={[dados.latitude, dados.longitude]} icon={iconeBolinha('#7c3aed')} />
              </>
            )}
          </MapaBase>
        </div>

        <label className="block text-sm font-medium text-gray-700">
          Raio: {dados.raio_m} m
          <input
            type="range"
            min={30}
            max={2000}
            step={10}
            value={dados.raio_m}
            onChange={(e) => setDados((d) => ({ ...d, raio_m: Number(e.target.value) }))}
            className="mt-2 block w-full accent-purple-600"
          />
          <span className="text-xs font-normal text-gray-500">Casa: 100 a 150 m costuma bastar. Escola grande: 200 a 300 m.</span>
        </label>

        {aviso && <p className="rounded-lg bg-gray-50 p-3 text-sm text-gray-700">{aviso}</p>}
        {!temPonto && <p className="text-xs text-amber-700">Busque o endereço ou clique no mapa para marcar o ponto.</p>}

        <div className="flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={onFechar}>Cancelar</Button>
          <Button type="submit" disabled={!podeSalvar}>{salvar.isPending ? 'Salvando...' : 'Salvar'}</Button>
        </div>
      </form>
    </Modal>
  )
}

// ---------------------------------------------------------------- Celulares

function AbaCelulares({ criancas }: { criancas: Crianca[] }) {
  const queryClient = useQueryClient()
  const [codigo, setCodigo] = useState<Pareamento | null>(null)
  const [revogar, setRevogar] = useState<{ id: number; nome: string; crianca: string } | null>(null)

  const gerar = useMutation({
    mutationFn: (criancaId: number) => localizacaoApi.parear(criancaId),
    onSuccess: setCodigo,
    onError: (e) => alert(mensagemDeErro(e, 'Não foi possível gerar o código.')),
  })
  const revogacao = useMutation({
    mutationFn: (id: number) => localizacaoApi.revogar(id),
    onSuccess: () => {
      setRevogar(null)
      void queryClient.invalidateQueries({ queryKey: ['localizacao', 'criancas'] })
    },
    onError: (e) => alert(mensagemDeErro(e, 'Não foi possível revogar o celular.')),
  })

  if (criancas.length === 0) return <div className="space-y-4"><BaixarApp /><SemCriancas /></div>

  return (
    <div className="space-y-4">
      <BaixarApp />
      <DestinatariosSos />
      <p className="text-sm text-gray-600">
        Para ligar o celular da criança, gere um código e digite no app do celular. O código vale 15 minutos e serve uma vez só.
      </p>
      {criancas.map((crianca) => (
        <div key={crianca.id} className="rounded-lg bg-white p-4 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-lg font-semibold text-gray-900">
              {crianca.nome}
              {crianca.adulto && <span className="ml-2 rounded-full bg-teal-100 px-2 py-0.5 align-middle text-xs font-medium text-teal-800">Adulto</span>}
            </p>
            {crianca.adulto ? (
              <p className="text-xs text-gray-500">Liga e desliga pelo app, no próprio celular.</p>
            ) : (
              <Button
                variant="outline"
                onClick={() => gerar.mutate(crianca.id)}
                disabled={gerar.isPending}
                className="flex items-center gap-1"
              >
                <Smartphone className="h-4 w-4" /> Gerar código
              </Button>
            )}
          </div>
          <CampoApelido crianca={crianca} />
          {crianca.aparelhos.length === 0 ? (
            <p className="mt-2 text-sm text-gray-500">Nenhum celular pareado.</p>
          ) : (
            <ul className="mt-3 divide-y divide-gray-100">
              {crianca.aparelhos.map((aparelho) => (
                <li key={aparelho.id} className="py-2">
                  <div className="flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <p className={`text-sm font-medium ${aparelho.revogado ? 'text-gray-400 line-through' : 'text-gray-900'}`}>
                      {aparelho.nome}
                    </p>
                    <p className="text-xs text-gray-500">
                      {aparelho.revogado
                        ? 'Revogado'
                        : aparelho.atualizado_em
                          ? `Último envio ${new Date(aparelho.atualizado_em).toLocaleString('pt-BR', { timeZone: 'America/Sao_Paulo', dateStyle: 'short', timeStyle: 'short' })}`
                          : 'Ainda não enviou localização'}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    {!aparelho.revogado && <Bateria nivel={aparelho.bateria} />}
                    {!aparelho.revogado && (
                      <button
                        type="button"
                        onClick={() => setRevogar({ id: aparelho.id, nome: aparelho.nome, crianca: crianca.nome })}
                        className="rounded-lg px-2 py-1 text-sm text-red-600 hover:bg-red-50"
                      >
                        Revogar
                      </button>
                    )}
                  </div>
                  </div>
                  {!aparelho.revogado && <ChecklistCelular aparelho={aparelho} />}
                </li>
              ))}
            </ul>
          )}
        </div>
      ))}

      {codigo && <ModalCodigo pareamento={codigo} onFechar={() => setCodigo(null)} />}

      <ConfirmDeleteModal
        isOpen={!!revogar}
        onClose={() => setRevogar(null)}
        title="Revogar celular"
        message={revogar ? <>Revogar <strong>{revogar.nome}</strong> de {revogar.crianca}? Ele para de enviar localização na hora. Para voltar, gere um código novo.</> : ''}
        confirmLabel="Revogar"
        onConfirm={() => revogar && revogacao.mutate(revogar.id)}
        isLoading={revogacao.isPending}
      />
    </div>
  )
}

function CampoApelido({ crianca }: { crianca: Crianca }) {
  const queryClient = useQueryClient()
  const [valor, setValor] = useState(crianca.apelido || '')
  const [salvo, setSalvo] = useState(false)
  useEffect(() => { setValor(crianca.apelido || '') }, [crianca.apelido])

  const salvar = useMutation({
    mutationFn: () => localizacaoApi.salvarApelido(crianca.id, valor.trim()),
    onSuccess: () => {
      setSalvo(true)
      void queryClient.invalidateQueries({ queryKey: ['localizacao', 'criancas'] })
    },
    onError: (e) => alert(mensagemDeErro(e, 'Não foi possível salvar o apelido.')),
  })
  const mudou = valor.trim() !== (crianca.apelido || '')

  return (
    <form
      className="mt-3 flex flex-wrap items-end gap-2"
      onSubmit={(e) => { e.preventDefault(); if (mudou) salvar.mutate() }}
    >
      <label className="text-sm font-medium text-gray-700">
        Apelido no mapa
        <input
          value={valor}
          maxLength={12}
          placeholder={crianca.nome.slice(0, 2)}
          onChange={(e) => { setValor(e.target.value); setSalvo(false) }}
          className="mt-1 block min-h-10 w-32 rounded-lg border border-gray-300 px-3"
        />
      </label>
      <Button type="submit" variant="outline" disabled={!mudou || salvar.isPending} className="min-h-10">
        {salvar.isPending ? 'Salvando...' : 'Salvar'}
      </Button>
      {salvo && !mudou && <span className="pb-2 text-xs text-green-700">Salvo</span>}
    </form>
  )
}

function ModalCodigo({ pareamento, onFechar }: { pareamento: Pareamento; onFechar: () => void }) {
  const [restante, setRestante] = useState(() => Math.max(0, new Date(pareamento.expira_em).getTime() - Date.now()))
  const [copiado, setCopiado] = useState(false)

  useEffect(() => {
    const t = window.setInterval(() => {
      setRestante(Math.max(0, new Date(pareamento.expira_em).getTime() - Date.now()))
    }, 1000)
    return () => window.clearInterval(t)
  }, [pareamento.expira_em])

  const minutos = Math.floor(restante / 60_000)
  const segundos = Math.floor((restante % 60_000) / 1000)
  const vencido = restante <= 0

  return (
    <Modal isOpen onClose={onFechar} title={`Código para ${pareamento.crianca_nome}`}>
      <div className="space-y-4 text-center">
        <p className={`select-all font-mono text-4xl font-bold tracking-widest ${vencido ? 'text-gray-300 line-through' : 'text-purple-700'}`}>
          {pareamento.codigo}
        </p>
        <p className={`text-sm ${vencido ? 'text-red-600' : 'text-gray-600'}`}>
          {vencido ? 'Código vencido. Gere outro.' : `Vale por mais ${minutos}:${String(segundos).padStart(2, '0')}. Depois de usado, não serve de novo.`}
        </p>
        <p className="text-sm text-gray-600">
          No app do celular, informe o endereço <strong>{window.location.origin}</strong> e este código.
        </p>
        <p className="text-xs text-gray-500">Ainda não instalou o app? Use "Baixar o app" na aba Celulares.</p>
        <div className="flex justify-center gap-2">
          <Button
            variant="outline"
            onClick={() => {
              void navigator.clipboard?.writeText(pareamento.codigo).then(() => setCopiado(true))
            }}
            disabled={vencido}
            className="flex items-center gap-1"
          >
            <Copy className="h-4 w-4" /> {copiado ? 'Copiado' : 'Copiar'}
          </Button>
          <Button onClick={onFechar}>Fechar</Button>
        </div>
      </div>
    </Modal>
  )
}

// ---------------------------------------------------------------- Checklist de envio do celular

const MARCA_DO_ITEM: Record<EstadoItemSite, { simbolo: string; cor: string; rotulo: string }> = {
  ok: { simbolo: '✓', cor: 'text-green-700', rotulo: '' },
  manual: { simbolo: '✓', cor: 'text-green-700', rotulo: ' (confirmado no celular)' },
  falta: { simbolo: '✗', cor: 'text-red-700', rotulo: '' },
  atrasado: { simbolo: '!', cor: 'text-amber-700', rotulo: ' (atrasado)' },
  manual_pendente: { simbolo: '?', cor: 'text-amber-700', rotulo: ' (confirmação manual)' },
  sem_dado: { simbolo: '–', cor: 'text-gray-400', rotulo: ' (sem dado)' },
}

function ChecklistCelular({ aparelho }: { aparelho: Aparelho }) {
  const itens = checklistDoCelular(aparelho)
  const faltam = pendencias(itens)
  const [aberto, setAberto] = useState(false)
  return (
    <div className="mt-1">
      <button
        type="button"
        onClick={() => setAberto(!aberto)}
        className={`text-xs font-medium ${faltam.length ? 'text-amber-700' : 'text-green-700'} hover:underline`}
        aria-expanded={aberto}
      >
        {faltam.length
          ? `Checklist de envio: ${faltam.length} ${faltam.length === 1 ? 'pendência' : 'pendências'}`
          : 'Checklist de envio: tudo certo'}
        {aberto ? ' ▲' : ' ▼'}
      </button>
      {aberto && (
        <ul className="mt-1 space-y-1 rounded-md bg-gray-50 p-2 text-xs">
          {itens.map((item) => {
            const marca = MARCA_DO_ITEM[item.estado]
            return (
              <li key={item.chave}>
                <span className={`font-medium ${marca.cor}`}>{marca.simbolo} {item.nome}{marca.rotulo}</span>
                {item.detalhe && <span className="block text-gray-600">{item.detalhe}</span>}
              </li>
            )
          })}
          {aparelho.checklist_em && (
            <li className="pt-1 text-gray-500">
              Ajustes informados pelo celular em{' '}
              {new Date(aparelho.checklist_em).toLocaleString('pt-BR', { timeZone: 'America/Sao_Paulo', dateStyle: 'short', timeStyle: 'short' })}.
            </li>
          )}
        </ul>
      )}
    </div>
  )
}
