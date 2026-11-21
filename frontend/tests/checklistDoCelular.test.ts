// Rodar: node --experimental-strip-types tests/checklistDoCelular.test.ts (Node 22+)
import assert from 'node:assert/strict'
import { checklistDoCelular, duracao, pendencias, resumoDoChecklist } from '../src/pages/localizacao/checklistDoCelular.ts'

let ok = 0
const teste = (nome: string, fn: () => void) => { fn(); ok++; console.log('ok -', nome) }
const agora = Date.parse('2026-11-21T17:18:00Z')
const ha = (min: number) => new Date(agora - min * 60_000).toISOString()
const tudoCerto = {
  gps: true, sempre: true, precisa: true, bateria_livre: true,
  inicio_automatico: 'confirmado', inicio_automatico_em: '2026-11-21',
}

teste('celular em dia: tudo certo, na ordem do app', () => {
  const itens = checklistDoCelular({ revogado: false, atualizado_em: ha(4), visto_em: ha(4), checklist: tudoCerto, checklist_em: ha(4) }, agora)
  assert.deepEqual(itens.map((i) => i.chave), ['gps', 'sempre', 'precisa', 'bateria', 'envio', 'inicio_automatico', 'rede'])
  assert.deepEqual(pendencias(itens), [])
  const auto = itens.find((i) => i.chave === 'inicio_automatico')!
  assert.equal(auto.estado, 'manual') // nunca "ok": o app não consegue conferir
  assert.match(auto.detalhe, /21\/11\/2026/)
})

teste('caso real do Guilherme: último envio há 5 h 32 min fica atrasado no envio e na internet', () => {
  const itens = checklistDoCelular({ revogado: false, atualizado_em: ha(332), visto_em: ha(332), checklist: null, checklist_em: null }, agora)
  const envio = itens.find((i) => i.chave === 'envio')!
  assert.equal(envio.estado, 'atrasado')
  assert.match(envio.detalhe, /5 h 32 min/)
  assert.match(envio.detalhe, /última posição recebida, não a atual/)
  assert.equal(itens.find((i) => i.chave === 'rede')!.estado, 'atrasado')
  // App 2.0.6 não manda checklist: os ajustes ficam "sem dado", sem inventar.
  for (const chave of ['gps', 'sempre', 'precisa', 'bateria', 'inicio_automatico']) {
    assert.equal(itens.find((i) => i.chave === chave)!.estado, 'sem_dado', chave)
  }
  assert.deepEqual(pendencias(itens).map((i) => i.chave), ['envio', 'rede'])
})

teste('falta bateria e início automático pendente aparecem como pendências', () => {
  const itens = checklistDoCelular({
    revogado: false, atualizado_em: ha(2), visto_em: ha(2),
    checklist: { ...tudoCerto, bateria_livre: false, inicio_automatico: 'pendente', inicio_automatico_em: null },
  }, agora)
  assert.deepEqual(pendencias(itens).map((i) => [i.chave, i.estado]), [['bateria', 'falta'], ['inicio_automatico', 'manual_pendente']])
})

teste('marca sem início automático: o item não aparece', () => {
  const itens = checklistDoCelular({
    revogado: false, atualizado_em: ha(2), visto_em: ha(2),
    checklist: { ...tudoCerto, inicio_automatico: 'nao_se_aplica', inicio_automatico_em: null },
  }, agora)
  assert.ok(!itens.some((i) => i.chave === 'inicio_automatico'))
  assert.equal(itens.length, 6)
})

teste('nunca enviou', () => {
  const itens = checklistDoCelular({ revogado: false, atualizado_em: null, visto_em: null }, agora)
  assert.equal(itens.find((i) => i.chave === 'envio')!.estado, 'falta')
  assert.equal(itens.find((i) => i.chave === 'rede')!.estado, 'sem_dado')
})

teste('durações', () => {
  assert.equal(duracao(30), 'menos de 1 min')
  assert.equal(duracao(45 * 60), '45 min')
  assert.equal(duracao(332 * 60), '5 h 32 min')
  assert.equal(duracao(26 * 3600), '1 dia')
})

teste('QA-A: app antigo em dia (sem checklist) nunca aparece como "tudo certo"', () => {
  const itens = checklistDoCelular({ revogado: false, atualizado_em: ha(3), visto_em: ha(3), checklist: null }, agora)
  assert.deepEqual(pendencias(itens), [])
  assert.deepEqual(resumoDoChecklist(itens), { texto: 'Checklist de envio: sem dado, atualize o app para a versão mais nova', tom: 'neutro' })
  // Sem o campo (resposta antiga) é igual.
  assert.equal(resumoDoChecklist(checklistDoCelular({ revogado: false, atualizado_em: ha(3), visto_em: ha(3) }, agora)).tom, 'neutro')
})

teste('resumo: pendências com e sem dado, e tudo certo só com checklist completo', () => {
  const atrasadoSemDado = checklistDoCelular({ revogado: false, atualizado_em: ha(332), visto_em: ha(332), checklist: null }, agora)
  assert.deepEqual(resumoDoChecklist(atrasadoSemDado), {
    texto: 'Checklist de envio: 2 pendências; ajustes sem dado (atualize o app para a versão mais nova)', tom: 'alerta',
  })
  const umaFalta = checklistDoCelular({
    revogado: false, atualizado_em: ha(2), visto_em: ha(2), checklist: { ...tudoCerto, bateria_livre: false },
  }, agora)
  assert.deepEqual(resumoDoChecklist(umaFalta), { texto: 'Checklist de envio: 1 pendência', tom: 'alerta' })
  const parcial = checklistDoCelular({
    revogado: false, atualizado_em: ha(2), visto_em: ha(2), checklist: { ...tudoCerto, precisa: null },
  }, agora)
  assert.equal(resumoDoChecklist(parcial).tom, 'neutro')
  const certo = checklistDoCelular({ revogado: false, atualizado_em: ha(2), visto_em: ha(2), checklist: tudoCerto }, agora)
  assert.deepEqual(resumoDoChecklist(certo), { texto: 'Checklist de envio: tudo certo', tom: 'ok' })
})

teste('nenhum número de versão fixo nos textos do checklist', () => {
  const textos = [
    ...checklistDoCelular({ revogado: false, atualizado_em: ha(332), visto_em: ha(332), checklist: null }, agora).map((i) => i.detalhe),
    resumoDoChecklist(checklistDoCelular({ revogado: false, atualizado_em: ha(3), visto_em: ha(3), checklist: null }, agora)).texto,
    resumoDoChecklist(checklistDoCelular({ revogado: false, atualizado_em: ha(332), visto_em: ha(332), checklist: null }, agora)).texto,
  ]
  for (const texto of textos) assert.doesNotMatch(texto, /\d+\.\d+\.\d+/, texto)
  assert.ok(textos.some((t) => t.includes('versão mais nova')))
})

console.log(`${ok}/9 OK`)
