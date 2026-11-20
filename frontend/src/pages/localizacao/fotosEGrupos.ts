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
 * Foto de cada pessoa (por id). Regras, sempre dentro da mesma família:
 * 1) nome completo igual (sem acento e sem diferença de maiúsculas) e um só membro com esse nome;
 * 2) senão, primeiro nome igual, um só membro E uma só pessoa no mapa com esse primeiro nome.
 * Qualquer dúvida: sem foto (o marcador mostra a inicial).
 */
export function casarFotos(pessoas: PessoaNoMapa[], membros: MembroComFoto[]): Record<number, string> {
  const fotos: Record<number, string> = {}
  const comFoto = membros
    .map((membro) => ({ ...membro, src: fotoParaSrc(membro.photo) }))
    .filter((membro): membro is MembroComFoto & { src: string } => !!membro.src)
  for (const pessoa of pessoas) {
    const daFamilia = comFoto.filter((membro) => membro.family_id === pessoa.family_id)
    const iguais = daFamilia.filter((membro) => normalizarNome(membro.name) === normalizarNome(pessoa.nome))
    if (iguais.length === 1) {
      fotos[pessoa.id] = iguais[0].src
      continue
    }
    if (iguais.length > 1) continue
    const primeiro = primeiroNome(pessoa.nome)
    if (!primeiro) continue
    const mesmoPrimeiro = daFamilia.filter((membro) => primeiroNome(membro.name) === primeiro)
    const pessoasComEsse = pessoas.filter((outra) => outra.family_id === pessoa.family_id && primeiroNome(outra.nome) === primeiro)
    if (mesmoPrimeiro.length === 1 && pessoasComEsse.length === 1) fotos[pessoa.id] = mesmoPrimeiro[0].src
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
