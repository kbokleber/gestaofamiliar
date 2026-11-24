// Rodar: node --experimental-strip-types tests/fotosEGrupos.test.ts (Node 22+)
import assert from 'node:assert/strict'
import { agruparProximos, fonteDoRotulo, fotoParaSrc, fotosPorPessoa, rotuloDaPessoa } from '../src/pages/localizacao/fotosEGrupos.ts'

const JPG = '/9j/4AAQSkZJRgABAQ=='
let ok = 0
const teste = (nome: string, fn: () => void) => { fn(); ok++; console.log('ok -', nome) }

teste('foto: base64 vira data:image/jpeg; data:image aceito; outros recusados', () => {
  assert.equal(fotoParaSrc(JPG), `data:image/jpeg;base64,${JPG}`)
  assert.equal(fotoParaSrc(`data:image/png;base64,${JPG}`), `data:image/png;base64,${JPG}`)
  assert.equal(fotoParaSrc('javascript:alert(1)'), null)
  assert.equal(fotoParaSrc('data:text/html;base64,PHNjcmlwdD4='), null)
  assert.equal(fotoParaSrc('"><img onerror=x>'), null)
  assert.equal(fotoParaSrc(''), null)
  assert.equal(fotoParaSrc(null), null)
})

teste('mesmo ponto ou a poucos metros: um grupo, na ordem; longe: separado', () => {
  const casa = { latitude: -23.55, longitude: -46.63 }
  const m = 1 / 111_320
  const pessoas = [
    { id: 16, ...casa },
    { id: 17, latitude: casa.latitude + 10 * m, longitude: casa.longitude },
    { id: 3, latitude: casa.latitude + 25 * m, longitude: casa.longitude }, // em cadeia (15 m do 17)
    { id: 1, ...casa },
    { id: 9, latitude: casa.latitude + 500 * m, longitude: casa.longitude },
  ]
  const grupos = agruparProximos(pessoas, 30)
  assert.equal(grupos.length, 2)
  assert.deepEqual(grupos[0].pessoas.map((p) => p.id), [16, 17, 3, 1])
  assert.deepEqual(grupos[1].pessoas.map((p) => p.id), [9])
  assert.ok(Math.abs(grupos[0].latitude - (casa.latitude + 35 * m / 4)) < 1e-9)
})

teste('QA: fotos recusadas (svg, https, aspas, texto solto) e aceita a JPEG em data:image', () => {
  assert.deepEqual(
    ['data:image/svg+xml;base64,PHN2Zz4=', 'https://x/y.jpg', 'data:image/png;base64,AAA"onerror=1', '//evil', 'data:image/jpeg;base64,/9j/AAAA'].map(fotoParaSrc),
    [null, null, null, null, 'data:image/jpeg;base64,/9j/AAAA'],
  )
  assert.equal(fotoParaSrc('iVBORw0K'), 'data:image/jpeg;base64,iVBORw0K')
  assert.equal(fotoParaSrc('/9j/AAA'), null) // tamanho inválido de base64
})

teste('fotos por pessoa: só imagem de verdade entra, uma ruim não derruba as outras', () => {
  assert.deepEqual(fotosPorPessoa([]), {})
  assert.deepEqual(
    fotosPorPessoa([{ pessoa_id: 16, foto: JPG }, { pessoa_id: 17, foto: 'javascript:alert(1)' }, { pessoa_id: 18, foto: '' },
      { pessoa_id: 3, foto: '"><img onerror=x>' }]),
    { 16: `data:image/jpeg;base64,${JPG}` },
  )
})

teste('sem foto: apelido ou as duas primeiras letras', () => {
  assert.equal(rotuloDaPessoa('Guilherme'), 'Gu')
  assert.equal(rotuloDaPessoa('gIOVANA', null), 'Gi')
  assert.equal(rotuloDaPessoa('Kleber', ' Kleber Bueno '), 'Kleber Bueno')
  assert.equal(rotuloDaPessoa('Kleber', '   '), 'Kl')
  assert.equal(rotuloDaPessoa('  ', ''), '?')
})

teste('letra do rótulo: diminui pela palavra mais comprida, até 12 letras', () => {
  assert.deepEqual(['Gu', 'Gui', 'Vovó', 'Ana B', 'Pedro', 'Kleber Bueno', 'Mariaeduarda'].map(fonteDoRotulo), [15, 13, 10, 10, 10, 8, 8])
})

console.log(`${ok}/6 OK`)
