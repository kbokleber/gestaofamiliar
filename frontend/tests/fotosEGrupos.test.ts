// Rodar: node --experimental-strip-types tests/fotosEGrupos.test.ts (Node 22+)
import assert from 'node:assert/strict'
import { agruparProximos, casarFotos, fotoParaSrc } from '../src/pages/localizacao/fotosEGrupos.ts'

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

teste('casa por nome completo, sem acento, e por primeiro nome só sem ambiguidade', () => {
  const pessoas = [
    { id: 16, nome: 'Guilherme', family_id: 1 },
    { id: 17, nome: 'Giovana', family_id: 1 },
    { id: 3, nome: 'Mãe Bueno', family_id: 1 },
    { id: 1, nome: 'Kleber', family_id: 1 },
  ]
  const membros = [
    { name: 'Guilherme Bueno de Oliveira', family_id: 1, photo: JPG },
    { name: 'Giovana Bueno', family_id: 1, photo: null }, // sem foto: inicial
    { name: 'MAE BUENO', family_id: 1, photo: JPG },
    { name: 'Kleber Bueno', family_id: 2, photo: JPG }, // outra família: nunca
  ]
  const fotos = casarFotos(pessoas, membros)
  assert.deepEqual(Object.keys(fotos).sort(), ['16', '3'])
})

teste('dois membros com o mesmo primeiro nome: sem foto (não arrisca)', () => {
  const fotos = casarFotos(
    [{ id: 16, nome: 'Guilherme', family_id: 1 }],
    [{ name: 'Guilherme Bueno', family_id: 1, photo: JPG }, { name: 'Guilherme Avô', family_id: 1, photo: JPG }],
  )
  assert.deepEqual(fotos, {})
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

teste('QA-A: "Guilherme Bueno" (pai) não pega a foto de "Guilherme Bueno Junior" (filho)', () => {
  const fotos = casarFotos(
    [{ id: 1, nome: 'Guilherme Bueno', family_id: 1 }],
    [{ name: 'Guilherme Bueno Junior', family_id: 1, photo: JPG }],
  )
  assert.deepEqual(fotos, {})
  // Com o cadastro do pai também, cada um fica com a própria foto (nome completo).
  const PAI = '/9j/UEFJUEFJ'
  const ambos = casarFotos(
    [{ id: 1, nome: 'Guilherme Bueno', family_id: 1 }, { id: 2, nome: 'Guilherme Bueno Junior', family_id: 1 }],
    [{ name: 'Guilherme Bueno Junior', family_id: 1, photo: JPG }, { name: 'Guilherme Bueno', family_id: 1, photo: PAI }],
  )
  assert.equal(ambos[1], `data:image/jpeg;base64,${PAI}`)
  assert.equal(ambos[2], `data:image/jpeg;base64,${JPG}`)
})

teste('QA-B: "Ana Maria" sem foto não pega a foto de "Ana Clara"', () => {
  const membros = [{ name: 'Ana Maria', family_id: 1, photo: null }, { name: 'Ana Clara', family_id: 1, photo: JPG }]
  assert.deepEqual(casarFotos([{ id: 5, nome: 'Ana Maria', family_id: 1 }], membros), {})
  // Só o primeiro nome "Ana" com duas Anas no cadastro (uma sem foto): ambíguo, sem foto.
  assert.deepEqual(casarFotos([{ id: 5, nome: 'Ana', family_id: 1 }], membros), {})
  // A Ana Clara continua com a dela.
  assert.equal(casarFotos([{ id: 6, nome: 'Ana Clara', family_id: 1 }], membros)[6], `data:image/jpeg;base64,${JPG}`)
})

teste('nome vazio não casa com membro de nome vazio', () => {
  assert.deepEqual(casarFotos([{ id: 7, nome: '  ', family_id: 1 }], [{ name: '', family_id: 1, photo: JPG }]), {})
})

console.log(`${ok}/7 OK`)
