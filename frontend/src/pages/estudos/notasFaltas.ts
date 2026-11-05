export type Bimestre = 1 | 2 | 3 | 4

export interface NotasDoBimestre {
  b1_nota: number | null
  b1_conceito?: string | null
  b1_faltas: number | null
  b2_nota: number | null
  b2_conceito?: string | null
  b2_faltas: number | null
  b3_nota: number | null
  b3_conceito?: string | null
  b3_faltas: number | null
  b4_nota: number | null
  b4_conceito?: string | null
  b4_faltas: number | null
}

export function notaEFaltas(
  linha: NotasDoBimestre,
  bimestre: Bimestre,
): { nota: number | null; conceito: string | null; faltas: number | null } {
  if (bimestre === 1) {
    return { nota: linha.b1_nota, conceito: linha.b1_conceito ?? null, faltas: linha.b1_faltas }
  }
  if (bimestre === 2) {
    return { nota: linha.b2_nota, conceito: linha.b2_conceito ?? null, faltas: linha.b2_faltas }
  }
  if (bimestre === 3) {
    return { nota: linha.b3_nota, conceito: linha.b3_conceito ?? null, faltas: linha.b3_faltas }
  }
  return { nota: linha.b4_nota, conceito: linha.b4_conceito ?? null, faltas: linha.b4_faltas }
}

export function fmtFaltas(valor: number | null | undefined): string {
  if (valor == null || Number.isNaN(valor)) return '—'
  return String(Math.trunc(valor))
}

function inteiro(valor: unknown): number | null {
  if (valor == null || valor === '' || valor === '—') return null
  if (typeof valor === 'object') {
    const obj = valor as Record<string, unknown>
    if ('faltas' in obj) return inteiro(obj.faltas)
    if ('total' in obj) return inteiro(obj.total)
    if ('valor' in obj) return inteiro(obj.valor)
    return null
  }
  const texto = typeof valor === 'number' ? String(valor) : String(valor).trim().replace(',', '.')
  const n = Number(texto)
  if (!Number.isFinite(n)) return null
  return Math.trunc(n)
}

function indiceDaChave(chave: string): Bimestre | null {
  const normal = chave
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[º°]/g, 'o')
    .toLowerCase()
    .trim()
  const nomes: Record<string, Bimestre> = {
    primeiro: 1,
    segundo: 2,
    terceiro: 3,
    quarto: 4,
  }
  if (nomes[normal]) return nomes[normal]
  const padroes = [
    /^0?([1-4])$/,
    /^b([1-4])(?:_faltas)?$/,
    /^bimestre[\s_-]*([1-4])$/,
    /^([1-4])\s*o(?:\s*bimestre)?$/,
    /^([1-4])\s*bimestre$/,
    /^faltas[\s_-]*([1-4])$/,
    /^([1-4])[\s_-]*faltas$/,
  ]
  for (const padrao of padroes) {
    const achado = normal.match(padrao)
    if (achado) return Number(achado[1]) as Bimestre
  }
  return null
}

function desembrulhar(total: unknown): unknown {
  if (total == null || Array.isArray(total) || typeof total !== 'object') return total
  const obj = total as Record<string, unknown>
  const aninhado = ['faltas', 'totais', 'total', 'por_bimestre', 'bimestres'].find((chave) => chave in obj)
  if (aninhado && (Array.isArray(obj[aninhado]) || (obj[aninhado] && typeof obj[aninhado] === 'object'))) {
    return obj[aninhado]
  }
  return total
}

/** Lê o total de faltas de um bimestre no JSON já gravado pelo sync. */
export function faltasDoBimestre(total: unknown, bimestre: Bimestre): number | null {
  const dados = desembrulhar(total)
  if (Array.isArray(dados)) return inteiro(dados[bimestre - 1])
  if (dados == null || typeof dados !== 'object') return null
  for (const [chave, valor] of Object.entries(dados as Record<string, unknown>)) {
    if (indiceDaChave(chave) === bimestre) return inteiro(valor)
  }
  return null
}
