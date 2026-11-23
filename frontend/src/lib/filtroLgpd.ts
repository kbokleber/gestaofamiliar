/**
 * Filtro do que vai para o GlitchTip. O sistema guarda dados de crianças (nome, saúde, localização),
 * então o evento é REMONTADO só com o que está na lista permitida: texto do erro, URL, usuário,
 * navegador, histórico de cliques, cabeçalhos e qualquer campo novo do SDK ficam de fora.
 * Sem imports, para dar para testar sozinho.
 */
export const SEM_TEXTO = '[texto removido]'

type Objeto = Record<string, unknown>

// Identificadores de código: nunca texto livre.
const CODIGO = /^[A-Za-z_$<?][\w.$<>]{0,79}$/
const VERSAO = /^[\w.@+-]{1,80}$/
const ID = /^[0-9a-f]{32}$/
const MECANISMO = /^[a-z_.]{1,60}$/
// Só os arquivos compilados do próprio site; a página aberta (URL) não passa.
const ARQUIVO = /\/(assets\/[\w.-]{1,120}\.m?js|sw\.js|push-sw\.js|workbox-[\w-]{1,40}\.js)$/
const NIVEIS = ['fatal', 'error', 'warning', 'info', 'debug']

const objeto = (v: unknown): Objeto => (v !== null && typeof v === 'object' && !Array.isArray(v) ? (v as Objeto) : {})
const lista = (v: unknown): unknown[] => (Array.isArray(v) ? v : [])
const texto = (v: unknown, formato: RegExp): string | undefined =>
  typeof v === 'string' && formato.test(v) ? v : undefined
const inteiro = (v: unknown): number | undefined =>
  typeof v === 'number' && Number.isInteger(v) && v >= 0 && v < 10_000_000 ? v : undefined
const booleano = (v: unknown): boolean | undefined => (typeof v === 'boolean' ? v : undefined)

function limpo(dados: Objeto): Objeto {
  return Object.fromEntries(Object.entries(dados).filter(([, v]) => v !== undefined))
}

function arquivo(v: unknown): string {
  if (typeof v !== 'string') return '[pagina]'
  const achado = ARQUIVO.exec(v.split(/[?#]/, 1)[0])
  return achado ? `/${achado[1]}` : '[pagina]'
}

function quadro(v: unknown): Objeto {
  const q = objeto(v)
  return limpo({
    filename: arquivo(q.filename),
    function: texto(q.function, CODIGO),
    lineno: inteiro(q.lineno),
    colno: inteiro(q.colno),
    in_app: booleano(q.in_app),
  })
}

function excecao(v: unknown): Objeto {
  const e = objeto(v)
  const mecanismo = objeto(e.mechanism)
  const quadros = lista(objeto(e.stacktrace).frames)
  return {
    type: texto(e.type, CODIGO) ?? 'Erro',
    // A mensagem pode trazer nome, coordenada ou resposta da API: nunca vai.
    value: SEM_TEXTO,
    mechanism: limpo({ type: texto(mecanismo.type, MECANISMO) ?? 'generic', handled: booleano(mecanismo.handled) }),
    ...(quadros.length ? { stacktrace: { frames: quadros.slice(-80).map(quadro) } } : {}),
  }
}

function filtrar(evento: unknown): Objeto | null {
  const ev = objeto(evento)
  // Transações, replays e afins têm "type"; e só erro com exceção interessa.
  if (ev.type) return null
  const valores = lista(objeto(ev.exception).values)
  if (!valores.length) return null
  return limpo({
    event_id: texto(ev.event_id, ID),
    timestamp: typeof ev.timestamp === 'number' && Number.isFinite(ev.timestamp) ? ev.timestamp : undefined,
    platform: 'javascript',
    level: NIVEIS.includes(ev.level as string) ? ev.level : 'error',
    environment: texto(ev.environment, VERSAO),
    release: texto(ev.release, VERSAO),
    tags: { servico: 'gf-site' },
    exception: { values: valores.slice(0, 10).map(excecao) },
  })
}

/** beforeSend: evento novo só com o permitido; qualquer falha no filtro descarta o evento. */
export function filtrarEvento(evento: unknown): Objeto | null {
  try {
    return filtrar(evento)
  } catch {
    return null
  }
}

function sdkSeguro(v: unknown): Objeto {
  const sdk = objeto(v)
  return limpo({ name: texto(sdk.name, MECANISMO), version: texto(sdk.version, VERSAO) })
}

/**
 * Última barreira, no transporte: só sai envelope com erro e nada mais, sem o cabeçalho de rastreio.
 * O filtro roda de novo aqui, porque o SDK acrescenta campos depois do beforeSend.
 */
export function envelopeSoDeErro(envelope: unknown): unknown[] | null {
  const [cabecalho, itens] = lista(envelope)
  const partes = lista(itens)
  if (!partes.length) return null
  const saida: unknown[] = []
  for (const item of partes) {
    const [tipo, conteudo] = lista(item)
    const evento = objeto(tipo).type === 'event' ? filtrarEvento(conteudo) : null
    if (!evento) return null
    // "never": o servidor não deve deduzir o IP de quem enviou.
    const sdk = { ...sdkSeguro(objeto(conteudo).sdk), settings: { infer_ip: 'never' } }
    saida.push([{ type: 'event' }, { ...evento, sdk }])
  }
  const h = objeto(cabecalho)
  const envio = typeof h.sent_at === 'string' && /^[\dTZ:.+-]{10,40}$/.test(h.sent_at) ? h.sent_at : undefined
  return [limpo({ event_id: texto(h.event_id, ID), sent_at: envio, sdk: sdkSeguro(h.sdk) }), saida]
}
