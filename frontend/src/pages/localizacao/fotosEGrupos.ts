/**
 * Foto e rótulo de cada pessoa no mapa, e agrupamento de quem está no mesmo lugar.
 * Sem React nem Leaflet, para dar para testar sozinho.
 *
 * A foto vem do cadastro de Saúde (Membros da Família), pelo vínculo que o adulto escolhe na aba Celulares.
 * Nada é adivinhado pelo nome.
 */

/** Só aceita imagem embutida (data:image/...). Base64 puro vira JPEG, como no cadastro. */
export function fotoParaSrc(photo: string | null | undefined): string | null {
  const valor = (photo ?? '').trim()
  if (!valor) return null
  if (valor.startsWith('data:')) return /^data:image\/(png|jpe?g|webp|gif);base64,[A-Za-z0-9+/=\s]+$/i.test(valor) ? valor : null
  // Base64 puro (como o cadastro guarda): só se for base64 válido e começar como imagem
  // (JPEG /9j/, PNG iVBOR, GIF R0lGOD, WebP UklGR). Assim textos soltos como "//evil" não passam.
  const limpo = valor.replace(/\s+/g, '')
  if (!/^[A-Za-z0-9+/]+={0,2}$/.test(limpo) || limpo.length % 4 !== 0) return null
  if (!/^(\/9j\/|iVBOR|R0lGOD|UklGR)/.test(limpo)) return null
  return `data:image/jpeg;base64,${limpo}`
}

/** Foto de cada pessoa (por id), só as que são imagem de verdade. */
export function fotosPorPessoa(fotos: Array<{ pessoa_id: number; foto: string }>): Record<number, string> {
  const saida: Record<number, string> = {}
  for (const { pessoa_id, foto } of fotos) {
    const src = fotoParaSrc(foto)
    if (src) saida[pessoa_id] = src
  }
  return saida
}

/** Texto de quem não tem foto: o apelido ou as duas primeiras letras do nome (irmãos com a mesma inicial não ficam iguais). */
export function rotuloDaPessoa(nome: string, apelido?: string | null): string {
  const letras = nome.trim().slice(0, 2) || '?'
  return apelido?.trim() || letras[0].toUpperCase() + letras.slice(1).toLowerCase()
}

/** Tamanho da letra (px) para o rótulo caber no círculo do marcador: manda a palavra mais comprida. */
export function fonteDoRotulo(rotulo: string): number {
  const maior = Math.max(...rotulo.split(/\s+/).map((palavra) => palavra.length))
  if (rotulo.length <= 2) return 15
  if (rotulo.length === 3) return 13
  return maior <= 5 ? 10 : 8
}

export interface PontoDePessoa {
  id: number
  latitude: number
  longitude: number
}

export interface Grupo<T extends PontoDePessoa> {
  latitude: number
  longitude: number
  pessoas: T[]
}

export function distanciaM(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const raio = 6_371_000
  const rad = Math.PI / 180
  const dLat = (lat2 - lat1) * rad
  const dLon = (lon2 - lon1) * rad
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin(dLon / 2) ** 2
  return 2 * raio * Math.asin(Math.sqrt(a))
}

/**
 * Junta quem está a até raioM metros de alguém do grupo (em cadeia). Só muda a exibição:
 * o grupo aparece no centro das posições, com as pessoas lado a lado, na ordem original.
 */
export function agruparProximos<T extends PontoDePessoa>(pessoas: T[], raioM = 30): Grupo<T>[] {
  const grupoDe = pessoas.map((_, i) => i)
  const raiz = (i: number): number => (grupoDe[i] === i ? i : (grupoDe[i] = raiz(grupoDe[i])))
  for (let i = 0; i < pessoas.length; i++) {
    for (let j = i + 1; j < pessoas.length; j++) {
      if (distanciaM(pessoas[i].latitude, pessoas[i].longitude, pessoas[j].latitude, pessoas[j].longitude) <= raioM) {
        grupoDe[raiz(j)] = raiz(i)
      }
    }
  }
  const porRaiz = new Map<number, T[]>()
  pessoas.forEach((pessoa, i) => {
    const r = raiz(i)
    porRaiz.set(r, [...(porRaiz.get(r) ?? []), pessoa])
  })
  return [...porRaiz.values()].map((membros) => ({
    latitude: membros.reduce((soma, p) => soma + p.latitude, 0) / membros.length,
    longitude: membros.reduce((soma, p) => soma + p.longitude, 0) / membros.length,
    pessoas: membros,
  }))
}
