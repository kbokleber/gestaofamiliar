// Rodar: npx esbuild tests/monitoramento.test.ts --bundle --platform=node --format=esm --log-level=error | node --input-type=module -
import assert from 'node:assert/strict'
import { envelopeSoDeErro, filtrarEvento, SEM_TEXTO } from '../src/lib/filtroLgpd.ts'

let ok = 0
const teste = (nome: string, fn: () => void) => { fn(); ok++; console.log('ok -', nome) }

const SEGREDOS = ['Guilhermina-Segredo', 'Zacarias', 'crianca.segredo@example.com', '-23.987654', '-46.123987',
  'eyJhbGciOiJIUzI1NiJ9.segredo-jwt', 'sessao-segredo-789', '13999887766', 'Ritalinassegredo', '203.0.113.77']
const sujo = SEGREDOS.join(' ')
const semSegredos = (v: unknown) => {
  const t = JSON.stringify(v)
  for (const s of SEGREDOS) assert.ok(!t.includes(s), `vazou: ${s}`)
}

const cheio = () => ({
  event_id: 'a'.repeat(32), timestamp: 1795438618.5, platform: sujo, level: sujo, environment: sujo, release: sujo,
  transaction: `/criancas/${sujo}`, server_name: sujo, logger: sujo, message: sujo, fingerprint: [sujo],
  user: { id: 1, email: sujo, ip_address: '203.0.113.77' },
  request: { url: `https://site/localizacao?lat=-23.987654&nome=${sujo}`, headers: { Authorization: sujo, Referer: sujo, 'User-Agent': sujo }, cookies: sujo, data: sujo },
  breadcrumbs: [{ category: 'fetch', data: { url: sujo } }], extra: { __serialized__: { nome: sujo }, arguments: [sujo] },
  contexts: { react: { componentStack: sujo }, trace: { data: sujo }, culture: { timezone: sujo } }, tags: { a: sujo },
  sdkProcessingMetadata: { request: sujo }, debug_meta: { images: [sujo] }, campo_novo_do_sdk: sujo,
  exception: { values: [{
    type: 'AxiosError', value: `Erro de ${sujo}`, module: sujo, thread_id: sujo,
    mechanism: { type: 'auto.browser.global_handlers.onerror', handled: false, data: { a: sujo }, source: sujo },
    stacktrace: { frames: [
      { filename: 'https://gestaofamiliar.kbosolucoes.com.br/assets/index-Ab_12.js?x=Zacarias', function: 'abrirMapa', lineno: 1, colno: 2345, in_app: true, vars: { nome: sujo }, context_line: sujo },
      { filename: `https://gestaofamiliar.kbosolucoes.com.br/localizacao/${SEGREDOS[0]}#${SEGREDOS[5]}`, function: sujo, lineno: sujo },
      { filename: sujo, abs_path: sujo, function: 'eval', module_metadata: sujo },
    ] },
  }, { type: sujo, value: sujo }] },
})

teste('evento cheio de dados pessoais: sai só o permitido', () => {
  const saida = filtrarEvento(cheio()) as any
  semSegredos(saida)
  assert.deepEqual(Object.keys(saida).sort(), ['event_id', 'exception', 'level', 'platform', 'tags', 'timestamp'])
  assert.deepEqual(saida.exception.values[0], {
    type: 'AxiosError', value: SEM_TEXTO, mechanism: { type: 'auto.browser.global_handlers.onerror', handled: false },
    stacktrace: { frames: [
      { filename: '/assets/index-Ab_12.js', function: 'abrirMapa', lineno: 1, colno: 2345, in_app: true },
      { filename: '[pagina]' }, { filename: '[pagina]', function: 'eval' },
    ] },
  })
  assert.equal(saida.exception.values[1].type, 'Erro')
})

teste('versão e ambiente válidos passam', () => {
  const s = filtrarEvento({ ...cheio(), release: 'gf-site@2026.11.23-969866a', environment: 'production', level: 'fatal' }) as any
  assert.equal(s.release, 'gf-site@2026.11.23-969866a'); assert.equal(s.environment, 'production'); assert.equal(s.level, 'fatal')
})

teste('transação, replay, mensagem solta e lixo são descartados', () => {
  for (const e of [null, undefined, 'x', 1, [], {}, { type: 'transaction', exception: { values: [{}] } },
    { type: 'replay_event', exception: { values: [{}] } }, { message: sujo }, { exception: { values: [] } }]) assert.equal(filtrarEvento(e), null)
})

teste('formatos estranhos não vazam nem quebram', () => {
  semSegredos(filtrarEvento({ exception: { values: [null, sujo, 1, { stacktrace: { frames: [null, sujo, { filename: 3 }] }, mechanism: sujo }] }, level: { a: sujo }, timestamp: sujo }))
  const armadilha = { exception: { get values(): unknown { throw new Error(sujo) } } }
  assert.equal(filtrarEvento(armadilha), null)
})

teste('transporte: refiltra o que o SDK acrescenta e tira o rastreio', () => {
  const depois = { ...cheio(), sdk: { name: 'sentry.javascript.react', version: '10.78.0', packages: [{ name: sujo }], settings: { infer_ip: 'auto' } } }
  const saida = envelopeSoDeErro([{ event_id: 'a'.repeat(32), sent_at: '2026-11-23T12:00:00.000Z', trace: { transaction: sujo }, dsn: sujo, sdk: { name: 'sentry.javascript.react', version: '10.78.0', extra: sujo } }, [[{ type: 'event', extra: sujo }, depois]]]) as any
  semSegredos(saida)
  assert.deepEqual(Object.keys(saida[0]).sort(), ['event_id', 'sdk', 'sent_at'])
  assert.deepEqual(saida[1][0][1].sdk, { name: 'sentry.javascript.react', version: '10.78.0', settings: { infer_ip: 'never' } })
})

teste('transporte: qualquer outro item descarta o envelope inteiro', () => {
  const ev = [{ type: 'event' }, cheio()]
  for (const tipo of ['session', 'transaction', 'attachment', 'log', 'replay_event', 'feedback', 'client_report', 'profile']) {
    assert.equal(envelopeSoDeErro([{}, [[{ type: tipo }, { a: sujo }]]]), null, tipo)
    assert.equal(envelopeSoDeErro([{}, [ev, [{ type: tipo }, { a: sujo }]]]), null, `erro + ${tipo}`)
  }
  for (const lixo of [null, [], [{}], [{}, []], 'x']) assert.equal(envelopeSoDeErro(lixo), null)
})

console.log(`${ok}/6 OK`)
