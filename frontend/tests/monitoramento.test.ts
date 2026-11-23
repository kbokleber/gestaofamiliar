// Rodar: npx esbuild tests/monitoramento.test.ts --bundle --platform=node --format=esm --log-level=error | node --input-type=module -
import assert from 'node:assert/strict'
import { envelopeSoDeErro, filtrarEvento, MAX_CAUSAS, SEM_TEXTO } from '../src/lib/filtroLgpd.ts'

let ok = 0
const teste = (nome: string, fn: () => void) => { fn(); ok++; console.log('ok -', nome) }

const SEGREDOS = ['Guilhermina-Segredo', 'Zacarias', 'crianca.segredo@example.com', '-23.987654', '-46.123987',
  'eyJhbGciOiJIUzI1NiJ9.segredo-jwt', 'sessao-segredo-789', '13999887766', 'Ritalinassegredo', '203.0.113.77']
const sujo = SEGREDOS.join(' ')
const SITE = 'https://gestaofamiliar.kbosolucoes.com.br'
const AGORA = Date.now() / 1000
const CARREGADOS = new Set(['index-Ab_12xYz.js', 'pdf.worker.min-rsCePomN.mjs'].map((a) => `${SITE}/assets/${a}`).concat(`${SITE}/sw.js`, `${SITE}/workbox-66610c77.js`))
const AQUI = { origem: SITE, carregados: CARREGADOS }
const semSegredos = (v: unknown) => {
  const t = JSON.stringify(v)
  for (const s of SEGREDOS) assert.ok(!t.includes(s), `vazou: ${s}`)
}

const cheio = () => ({
  event_id: 'a'.repeat(32), timestamp: AGORA, platform: sujo, level: sujo, environment: sujo, release: sujo,
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
      { filename: 'https://gestaofamiliar.kbosolucoes.com.br/assets/index-Ab_12xYz.js?x=Zacarias', function: 'abrirMapa', lineno: 1, colno: 2345, in_app: true, vars: { nome: sujo }, context_line: sujo },
      { filename: `https://gestaofamiliar.kbosolucoes.com.br/localizacao/${SEGREDOS[0]}#${SEGREDOS[5]}`, function: sujo, lineno: sujo },
      { filename: sujo, abs_path: sujo, function: 'eval', module_metadata: sujo },
    ] },
  }, { type: sujo, value: sujo }] },
})

teste('evento cheio de dados pessoais: sai só o permitido', () => {
  const saida = filtrarEvento(cheio(), AQUI) as any
  semSegredos(saida)
  assert.deepEqual(Object.keys(saida).sort(), ['event_id', 'exception', 'level', 'platform', 'tags', 'timestamp'])
  assert.deepEqual(saida.exception.values[0], {
    type: 'AxiosError', value: SEM_TEXTO, mechanism: { type: 'auto.browser.global_handlers.onerror', handled: false },
    stacktrace: { frames: [
      { filename: '/assets/index-Ab_12xYz.js', lineno: 1, colno: 2345, in_app: true },
      { filename: '[pagina]' }, { filename: '[pagina]' },
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

// ---------------------------------------------------------------- correções do QA

const PALAVRAS = ['Guilhermina', 'Conceição', 'Guilhermina-Segredo', 'guilhermina', 'Ritalinassegredo', 'Guilhermina_Segredo',
  '-23.987654', '23.987654', '203.0.113.77', '13999887766', 'crianca.segredo@example.com', 'auto.guilhermina',
  'eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxNiJ9.c2VncmVkbw', 'gf-site@Guilhermina,x', '/assets/Guilhermina.js',
  `${SITE}/assets/Guilhermina.js`, `${SITE}/assets/Guilhermina-23.987654.js`, 'https://outro.com/assets/Guilhermina-Ab_12xYz.js']
const exc = (x: object) => ({ exception: { values: [{ type: 'Error', ...x }] } })
const quadroCom = (x: object) => exc({ stacktrace: { frames: [x] } })
const CAMPOS: Record<string, (p: string) => object> = {
  type: (p) => exc({ type: p }), value: (p) => exc({ value: p }), module: (p) => exc({ module: p }),
  mecanismo: (p) => exc({ mechanism: { type: p, handled: p } }),
  function: (p) => quadroCom({ function: p }), filename: (p) => quadroCom({ filename: p }),
  'quadro do próprio site': (p) => quadroCom({ filename: `${SITE}/assets/index-Ab_12xYz.js`, function: p, module: p, lineno: p, colno: p }),
  transaction: (p) => ({ ...exc({}), transaction: p, logger: p }), timestamp: (p) => ({ ...exc({}), timestamp: p }),
  environment: (p) => ({ ...exc({}), environment: p }), release: (p) => ({ ...exc({}), release: p }),
  level: (p) => ({ ...exc({}), level: p, platform: p }), event_id: (p) => ({ ...exc({}), event_id: p }),
  tags: (p) => ({ ...exc({}), tags: { causas_cortadas: p, [p]: p } }), novo: (p) => ({ ...exc({}), novo: p, [p]: p }),
}

teste('palavra única não passa em nenhum campo, nas duas passadas', () => {
  for (const p of PALAVRAS) for (const [campo, montar] of Object.entries(CAMPOS)) {
    for (const opcoes of [AQUI, { ...AQUI, jaFiltrado: true }, {}]) {
      const t = JSON.stringify(filtrarEvento(montar(p), opcoes))
      assert.ok(!t.includes(p), `vazou ${p} em ${campo}: ${t}`)
    }
    semPalavra(p, envelopeSoDeErro([{ event_id: p, sent_at: p, sdk: { name: p, version: p } }, [[{ type: 'event' }, { ...montar(p), sdk: { name: p, version: p } }]]]), campo)
  }
})
function semPalavra(p: string, v: unknown, campo: string) { assert.ok(!JSON.stringify(v).includes(p), `vazou ${p} em ${campo} (transporte)`) }

teste('arquivo: só o compilado do próprio domínio', () => {
  const nome = (filename: unknown, origem: string | undefined = SITE, extras: string[] = []) =>
    (filtrarEvento(quadroCom({ filename }), { origem, carregados: new Set([...CARREGADOS, ...extras, filename as string]) }) as any).exception.values[0].stacktrace.frames[0].filename
  assert.equal(nome(`${SITE}/assets/index-Ab_12xYz.js`), '/assets/index-Ab_12xYz.js')
  assert.equal(nome(`${SITE}/assets/pdf.worker.min-rsCePomN.mjs?v=1#x`), '/assets/pdf.worker.min-rsCePomN.mjs')
  assert.equal(nome(`${SITE}/sw.js`), '/sw.js')
  assert.equal(nome(`${SITE}/workbox-66610c77.js`), '/workbox-66610c77.js')
  for (const f of ['https://outro.com/assets/index-Ab_12xYz.js', `${SITE.replace('gestao', 'xxxxxx')}/assets/index-Ab_12xYz.js`, `${SITE}.outro.com/assets/index-Ab_12xYz.js`, `${SITE}:8443/assets/index-Ab_12xYz.js`,
    'http://gestaofamiliar.kbosolucoes.com.br/assets/index-Ab_12xYz.js', `https://outro.com/${SITE}/assets/index-Ab_12xYz.js`,
    `${SITE}/Guilhermina/assets/index-Ab_12xYz.js`, `${SITE}/assets/a/../Guilhermina-Ab_12xYz.js`, `${SITE}/Guilhermina/sw.js`, `${SITE}/assets/Guilhermina.js`,
    `${SITE}/workbox-guilhermina.js`, '/assets/index-Ab_12xYz.js', 'blob:' + SITE + '/assets/index-Ab_12xYz.js', '', null, 3]) assert.equal(nome(f), '[pagina]', String(f))
  assert.equal(nome(`${SITE}/assets/index-Ab_12xYz.js`, ''), '[pagina]')
})

const FALSO = 'falha\n    at Guilhermina_Segredo (https://x.com/assets/Guilhermina_Segredo.js:1:2)'
const comPilha = (value: string) => ({ type: 'Error', value, stacktrace: { frames: [{ filename: `${SITE}/assets/index-Ab_12xYz.js`, function: 'Guilhermina_Segredo', lineno: 1 }] } })
const temPilha = (valores: unknown[], erro?: unknown) =>
  JSON.stringify(filtrarEvento({ exception: { values: valores } }, { ...AQUI, erro })).includes('stacktrace')

teste('arquivo que a página não carregou nunca sai, mesmo com cara de arquivo do site', () => {
  const falso = `${SITE}/assets/Guilhermina_Segredo-Ab_12xYz.js`
  for (const opcoes of [AQUI, { origem: SITE }, { origem: SITE, carregados: new Set<string>() }]) {
    assert.ok(!JSON.stringify(filtrarEvento(quadroCom({ filename: falso }), opcoes)).includes('Guilhermina'))
  }
  // A mensagem foi encurtada para a primeira linha: a pilha parece boa, mas o arquivo não existe.
  const e = new Error(`a\n    at G (${falso}:1:2)`); assert.ok(e.stack); e.message = 'a'
  assert.ok(!JSON.stringify(filtrarEvento(quadroCom({ filename: falso }), { ...AQUI, erro: e })).includes('Guilhermina'))
})

teste('mensagem (ou causa) com quebra de linha: o evento sai sem nenhum quadro', () => {
  assert.equal(temPilha([comPilha('uma linha')]), true)
  for (const m of [FALSO, 'a\r\nb', 'a\rb', 'a b', 'a b', 'fim\n']) {
    assert.equal(temPilha([comPilha(m)]), false, JSON.stringify(m))
    assert.equal(temPilha([comPilha(m), comPilha('ok')]), false)
    assert.equal(temPilha([comPilha(m), ...Array(15).fill(comPilha('ok'))]), false, 'causa já cortada também conta')
  }
  const saida = filtrarEvento({ exception: { values: [comPilha(FALSO)] } }, AQUI)
  assert.ok(!JSON.stringify(saida).includes('Guilhermina'))
})

teste('pilha que não bate com a mensagem também é descartada (erro, causa e grupo)', () => {
  const limpo = new Error('uma linha')
  assert.equal(temPilha([comPilha('x')], limpo), true)
  assert.equal(temPilha([comPilha('x')], new TypeError('')), true)
  // A mensagem foi trocada depois: a pilha ainda guarda o texto antigo, com o quadro falso.
  const trocado = new Error(FALSO)
  assert.ok(trocado.stack?.includes('Guilhermina')) // o Node só monta a pilha quando ela é lida
  trocado.message = 'uma linha'
  assert.equal(temPilha([comPilha('uma linha')], trocado), false)
  const nome = new Error('x'); nome.name = 'a\nb'
  assert.equal(temPilha([comPilha('x')], nome), false)
  assert.equal(temPilha([comPilha('x')], new Error('x', { cause: new Error('y', { cause: new Error(FALSO) }) })), false)
  assert.equal(temPilha([comPilha('x')], new AggregateError([limpo, new Error(FALSO)], 'x')), false)
  // A mensagem foi encurtada para a primeira linha do texto original.
  const encurtado = new Error('uma linha\ntexto\n    at Guilhermina_Segredo (https://x.com/a.js:1:2)')
  assert.ok(encurtado.stack)
  encurtado.message = 'uma linha'
  assert.equal(temPilha([comPilha('uma linha')], encurtado), false)
  const nomeFirefox = new Error('x'); nomeFirefox.stack = `abrir@${SITE}/a.js:1:2`; nomeFirefox.name = 'a\nb'
  assert.equal(temPilha([comPilha('x')], nomeFirefox), false)
  const ciclo: any = new Error('x'); ciclo.cause = ciclo
  assert.equal(temPilha([comPilha('x')], ciclo), true)
  // Firefox e Safari: a mensagem não entra na pilha.
  const firefox = new Error('x'); firefox.stack = `abrir@${SITE}/assets/index-Ab_12xYz.js:1:2`
  assert.equal(temPilha([comPilha('x')], firefox), true)
})

teste('cadeia longa: avisa só a quantidade cortada e mantém a ponta', () => {
  const cadeia = (n: number) => ({ exception: { values: [...Array(n - 1).fill({ type: 'Error', value: sujo }), { type: 'TypeError', value: sujo }] }, tags: { causas_cortadas: sujo } })
  const curta = filtrarEvento(cadeia(MAX_CAUSAS)) as any
  assert.deepEqual(curta.tags, { servico: 'gf-site' })
  const longa = filtrarEvento(cadeia(32)) as any
  assert.deepEqual(longa.tags, { servico: 'gf-site', causas_cortadas: '22' })
  assert.equal(longa.exception.values.length, MAX_CAUSAS); assert.equal(longa.exception.values.at(-1).type, 'TypeError')
  semSegredos(longa)
  // O aviso sobrevive à segunda passada, no transporte.
  assert.equal((envelopeSoDeErro([{}, [[{ type: 'event' }, longa]]]) as any)[1][0][1].tags.causas_cortadas, '22')
})

teste('hora: só perto de agora', () => {
  const hora = (timestamp: unknown) => (filtrarEvento({ ...exc({}), timestamp }) as any).timestamp
  assert.equal(hora(AGORA), AGORA)
  for (const t of [-23.987654, 13999887766, 1399988776, NaN, Infinity, '2026-11-23', null, {}]) assert.equal(hora(t), undefined, String(t))
})

teste('nome da função nunca sai', () => {
  const t = JSON.stringify(filtrarEvento(quadroCom({ filename: `${SITE}/assets/index-Ab_12xYz.js`, function: 'abrirMapa', lineno: 1 }), AQUI))
  assert.ok(!t.includes('function') && !t.includes('abrirMapa'))
})

console.log(`${ok}/14 OK`)
