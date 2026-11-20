/**
 * Foto de cada pessoa no mapa e agrupamento de quem está no mesmo lugar.
 * Sem React nem Leaflet, para dar para testar sozinho.
 *
 * A foto vem do cadastro de Saúde (Membros da Família), que não tem ligação com o usuário:
 * por isso o casamento é pelo nome, dentro da mesma família, e só quando não há dúvida.
 */

export interface PessoaNoMapa {
  id: number
  nome: string
  family_id: number
}

export interface MembroComFoto {
  name: string
  family_id: number
  photo?: string | null
}

export function normalizarNome(nome: string): string {
  return nome
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .trim()
}

function primeiroNome(nome: string): string {
  return normalizarNome(nome).split(' ')[0] ?? ''
}

/** Só aceita imagem embutida (data:image/...). Base64 puro vira JPEG, como no cadastro. */
export function fotoParaSrc(photo: string | null | undefined): string | null {
  const valor = (photo ?? '').trim()
  if (!valor) return null
  if (valor.startsWith('data:')) return /^data:image\/(png|jpe?g|webp|gif);base64,[A-Za-z0-9+/=\s]+$/i.test(valor) ? valor : null
  return /^[A-Za-z0-9+/=\s]+$/.test(valor) ? `data:image/jpeg;base64,${valor.replace(/\s+/g, '')}` : null
}

/**
 * Foto de cada pessoa (por id). Casa contra TODOS os membros da mesma família (com ou sem foto)
 * e só depois pega a foto de quem casou; sem foto ou na dúvida, fica sem foto (o marcador mostra a inicial).
 * 1) Nome completo igual (sem acento e sem diferença de maiúsculas), com um só membro assim.
 * 2) Só quando o nome no mapa é apenas o primeiro nome (ex.: "Guilherme"): um só membro com esse
 *    primeiro nome e uma só pessoa no mapa com ele. Se o mapa tem sobrenome e o nome completo não
 *    bate (ex.: "Guilherme Bueno" x "Guilherme Bueno Junior"), não casa.
 * Nome vazio nunca casa.
 */
export function casarFotos(pessoas: PessoaNoMapa[], membros: MembroComFoto[]): Record<number, string> {
  const fotos: Record<number, string> = {}
  for (const pessoa of pessoas) {
    const nome = normalizarNome(pessoa.nome)
    if (!nome) continue
    const daFamilia = membros.filter((membro) => membro.family_id === pessoa.family_id && normalizarNome(membro.name) !== '')
    let escolhido: MembroComFoto | null = null
    const iguais = daFamilia.filter((membro) => normalizarNome(membro.name) === nome)
    if (iguais.length === 1) {
      escolhido = iguais[0]
    } else if (iguais.length === 0 && !nome.includes(' ')) {
      const mesmoPrimeiro = daFamilia.filter((membro) => primeiroNome(membro.name) === nome)
      const pessoasComEsse = pessoas.filter((outra) => outra.family_id === pessoa.family_id && primeiroNome(outra.nome) === nome)
      if (mesmoPrimeiro.length === 1 && pessoasComEsse.length === 1) escolhido = mesmoPrimeiro[0]
    }
    const src = escolhido ? fotoParaSrc(escolhido.photo) : null
    if (src) fotos[pessoa.id] = src
  }
  return fotos
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
