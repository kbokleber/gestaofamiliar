// Rodar: npx esbuild tests/documentos.test.ts --bundle --platform=node --format=esm | node --input-type=module -
import assert from 'node:assert/strict'
import { lerDocumentos } from '../src/utils/documentos'

let ok = 0
const teste = (nome: string, fn: () => void) => { fn(); ok++; console.log('ok -', nome) }

const doc = (name: string) => ({ name, type: 'image/jpeg', size: 10, data: 'AAAA' })

teste('string JSON com 2 anexos vira lista com 2 itens', () => {
  const lista = lerDocumentos(JSON.stringify([doc('condensadora.jpg'), doc('etiqueta.jpg')]))
  assert.equal(lista.length, 2)
  assert.deepEqual(lista.map(d => d.name), ['condensadora.jpg', 'etiqueta.jpg'])
})

teste('sem anexos (null, undefined, vazio) vira lista vazia', () => {
  assert.deepEqual(lerDocumentos(null), [])
  assert.deepEqual(lerDocumentos(undefined), [])
  assert.deepEqual(lerDocumentos(''), [])
  assert.deepEqual(lerDocumentos('[]'), [])
})

teste('JSON inválido ou que não é lista vira lista vazia', () => {
  assert.deepEqual(lerDocumentos('{quebrado'), [])
  assert.deepEqual(lerDocumentos('{"name":"x"}'), [])
  assert.deepEqual(lerDocumentos('"texto"'), [])
})

teste('lista já decodificada é aceita', () => {
  assert.equal(lerDocumentos([doc('a.jpg')]).length, 1)
})

console.log(`${ok} testes ok`)
