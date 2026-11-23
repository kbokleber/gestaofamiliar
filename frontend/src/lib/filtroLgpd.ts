/**
 * Filtro do que vai para o GlitchTip. O sistema guarda dados de crianças (nome, saúde, localização),
 * então o evento é REMONTADO só com o que está na lista permitida: texto do erro, URL, usuário,
 * navegador, histórico de cliques, cabeçalhos e qualquer campo novo do SDK ficam de fora.
 * Sem imports, para dar para testar sozinho.
 */
export const SEM_TEXTO = '[texto removido]'
// Teste de ponta a ponta: o único texto de erro que sai, e só igual a este, letra por letra.
export const TIPO_DE_TESTE = 'ErroDeTesteGlitchTip'
export const MENSAGEM_DE_TESTE = 'TESTE-GLITCHTIP (pode ignorar)'

type Objeto = Record<string, unknown>

// Tipos de erro conhecidos. Nome criado na hora (error.name = "...") vira "Erro".
const TIPOS = new Set([
  'Error', 'TypeError', 'RangeError', 'ReferenceError', 'SyntaxError', 'EvalError', 'URIError', 'AggregateError',
  'InternalError', 'UnhandledRejection', 'AxiosError', 'CanceledError', 'ChunkLoadError', 'DOMException', 'AbortError',
  'NetworkError', 'NotAllowedError', 'NotFoundError', 'NotSupportedError', 'NotReadableError', 'InvalidStateError',
  'QuotaExceededError', 'SecurityError', 'TimeoutError', 'DataCloneError', 'InvalidAccessError', 'OperationError',
  TIPO_DE_TESTE,
])
const MECANISMOS = new Set([
  'generic', 'chained', 'instrument', 'onerror', 'onunhandledrejection', 'auto.browser.global_handlers.onerror',
  'auto.browser.global_handlers.onunhandledrejection', 'auto.core.linked_errors',
])
const VERSAO = /^gf-site@[\w.+-]{1,60}$/
const AMBIENTES = ['production', 'development', 'test']
const ID = /^[0-9a-f]{32}$/
const SDK = /^sentry\.javascript\.[a-z]{1,20}$/
const VERSAO_SDK = /^\d{1,3}\.\d{1,3}\.\d{1,3}$/
// Só os arquivos compilados do próprio site, no formato do Vite: /assets/nome-<8 caracteres>.js
const ARQUIVO = /^\/(assets\/[A-Za-z][\w.]{0,60}-[\w-]{8}\.m?js|sw\.js|push-sw\.js|workbox-[0-9a-f]{8}\.js)$/
const NIVEIS = ['fatal', 'error', 'warning', 'info', 'debug']
// Quebra de linha na mensagem: o navegador copia a mensagem para a pilha, e o SDK poderia ler
// uma linha dela como se fosse um quadro.
const QUEBRA = /[\n\r\u2028\u2029]/
export const MAX_CAUSAS = 10
const DOIS_DIAS_S = 2 * 24 * 60 * 60

interface Opcoes {
  /** Origem do site (location.origin): só arquivo desta origem sai com nome. */
  origem?: string
  /** Endereços que a página carregou de verdade: arquivo inventado num texto não está aqui. */
  carregados?: ReadonlySet<string>
  /** O erro de verdade (hint.originalException), para conferir a pilha de todas as causas. */
  erro?: unknown
  /** Segunda passada, no transporte: o evento já foi filtrado. */
  jaFiltrado?: boolean
}

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

function arquivo(v: unknown, { origem, carregados, jaFiltrado }: Opcoes): string {
  if (typeof v !== 'string') return '[pagina]'
  let caminho = v
  if (!jaFiltrado) {
    const endereco = v.split(/[?#]/, 1)[0]
    if (!origem || !endereco.startsWith(`${origem}/`) || !carregados?.has(endereco)) return '[pagina]'
    caminho = endereco.slice(origem.length)
  }
  return ARQUIVO.test(caminho) ? caminho : '[pagina]'
}

// O nome da função não sai: no site compilado vem encurtado e era por ele que um texto podia escapar.
function quadro(v: unknown, opcoes: Opcoes): Objeto {
  const q = objeto(v)
  return limpo({
    filename: arquivo(q.filename, opcoes),
    lineno: inteiro(q.lineno),
    colno: inteiro(q.colno),
    in_app: booleano(q.in_app),
  })
}

/** A pilha de um erro é confiável? Só quando a mensagem tem uma linha e a pilha começa por ela. */
function pilhaConfiavel(erro: Error): boolean {
  const mensagem = String(erro.message ?? '')
  if (QUEBRA.test(mensagem) || QUEBRA.test(String(erro.name ?? ''))) return false
  const pilha = typeof erro.stack === 'string' ? erro.stack : ''
  if (!/^\s+at /m.test(pilha)) return true // Firefox e Safari não põem a mensagem na pilha
  const linhas = pilha.split('\n')
  const cabecalhoOk = mensagem === ''
    ? /^[\w$.]*$/.test(linhas[0])
    : linhas[0] === mensagem || linhas[0].endsWith(`: ${mensagem}`)
  return cabecalhoOk && /^\s+at /.test(linhas[1] ?? '')
}

/** Confere o erro, as causas e os erros agrupados. Cadeia enorme conta como não confiável. */
function cadeiaConfiavel(erro: unknown): boolean {
  const fila: unknown[] = [erro]
  const vistos = new Set<unknown>()
  while (fila.length) {
    const atual = fila.pop()
    if (!(atual instanceof Error) || vistos.has(atual)) continue
    vistos.add(atual)
    if (vistos.size > 200 || !pilhaConfiavel(atual)) return false
    fila.push((atual as { cause?: unknown }).cause, ...lista((atual as { errors?: unknown }).errors))
  }
  return true
}

function excecao(v: unknown, comPilha: boolean, opcoes: Opcoes): Objeto {
  const e = objeto(v)
  const mecanismo = objeto(e.mechanism)
  const quadros = comPilha ? lista(objeto(e.stacktrace).frames) : []
  return {
    type: typeof e.type === 'string' && TIPOS.has(e.type) ? e.type : 'Erro',
    // A mensagem pode trazer nome, coordenada ou resposta da API: nunca vai.
    // A única exceção é a mensagem fixa do erro de teste, comparada por inteiro.
    value: e.type === TIPO_DE_TESTE && e.value === MENSAGEM_DE_TESTE ? MENSAGEM_DE_TESTE : SEM_TEXTO,
    mechanism: limpo({
      type: typeof mecanismo.type === 'string' && MECANISMOS.has(mecanismo.type) ? mecanismo.type : 'generic',
      handled: booleano(mecanismo.handled),
    }),
    ...(quadros.length ? { stacktrace: { frames: quadros.slice(-80).map((q) => quadro(q, opcoes)) } } : {}),
  }
}

/** Hora em segundos, perto de agora: um telefone ou coordenada não passa por data. */
function momento(v: unknown): number | undefined {
  return typeof v === 'number' && Math.abs(v - Date.now() / 1000) < DOIS_DIAS_S ? v : undefined
}

function causasCortadas(ev: Objeto, total: number, jaFiltrado?: boolean): string | undefined {
  if (jaFiltrado) return texto(objeto(ev.tags).causas_cortadas, /^\d{1,4}$/)
  return total > MAX_CAUSAS ? String(total - MAX_CAUSAS) : undefined
}

function filtrar(evento: unknown, opcoes: Opcoes): Objeto | null {
  const ev = objeto(evento)
  // Transações, replays e afins têm "type"; e só erro com exceção interessa.
  if (ev.type) return null
  const valores = lista(objeto(ev.exception).values)
  if (!valores.length) return null
  const comPilha = cadeiaConfiavel(opcoes.erro) && !valores.some((v) => {
    const { type, value } = objeto(v)
    return QUEBRA.test(String(value ?? '')) || QUEBRA.test(String(type ?? ''))
  })
  return limpo({
    event_id: texto(ev.event_id, ID),
    timestamp: momento(ev.timestamp),
    platform: 'javascript',
    level: NIVEIS.includes(ev.level as string) ? ev.level : 'error',
    environment: AMBIENTES.includes(ev.environment as string) ? ev.environment : undefined,
    release: texto(ev.release, VERSAO),
    // Aviso de que a cadeia de causas foi cortada: só a quantidade.
    tags: limpo({ servico: 'gf-site', causas_cortadas: causasCortadas(ev, valores.length, opcoes.jaFiltrado) }),
    // As últimas da cadeia: a última é a que chegou ao fim.
    exception: { values: valores.slice(-MAX_CAUSAS).map((v) => excecao(v, comPilha, opcoes)) },
  })
}

/** beforeSend: evento novo só com o permitido; qualquer falha no filtro descarta o evento. */
export function filtrarEvento(evento: unknown, opcoes: Opcoes = {}): Objeto | null {
  try {
    return filtrar(evento, opcoes)
  } catch {
    return null
  }
}

function sdkSeguro(v: unknown): Objeto {
  const sdk = objeto(v)
  return limpo({ name: texto(sdk.name, SDK), version: texto(sdk.version, VERSAO_SDK) })
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
    const evento = objeto(tipo).type === 'event' ? filtrarEvento(conteudo, { jaFiltrado: true }) : null
    if (!evento) return null
    // "never": o servidor não deve deduzir o IP de quem enviou.
    const sdk = { ...sdkSeguro(objeto(conteudo).sdk), settings: { infer_ip: 'never' } }
    saida.push([{ type: 'event' }, { ...evento, sdk }])
  }
  const h = objeto(cabecalho)
  const envio = typeof h.sent_at === 'string' && /^20\d\d-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d{1,6})?Z$/.test(h.sent_at) ? h.sent_at : undefined
  return [limpo({ event_id: texto(h.event_id, ID), sent_at: envio, sdk: sdkSeguro(h.sdk) }), saida]
}
