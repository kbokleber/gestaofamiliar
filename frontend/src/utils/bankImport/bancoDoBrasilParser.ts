/**
 * Parser heurístico para extratos do Banco do Brasil (.xls/.xlsx).
 * Layouts variam; detectamos linha de cabeçalho e colunas de data, histórico e crédito/débito.
 */

export interface ParsedBbRow {
  date: string
  description: string
  amount: number
  type: 'INCOME' | 'EXPENSE'
}

function stripAccents(s: string): string {
  return s.normalize('NFD').replace(/[\u0300-\u036f]/g, '')
}

function normCell(v: string | number | null | boolean | undefined): string {
  if (v === null || v === undefined) return ''
  if (typeof v === 'boolean') return v ? 'TRUE' : 'FALSE'
  if (typeof v === 'number' && !Number.isNaN(v)) return String(v)
  if (Object.prototype.toString.call(v) === '[object Date]') {
    const dt = v as unknown as Date
    const y = dt.getFullYear()
    const m = String(dt.getMonth() + 1).padStart(2, '0')
    const d = String(dt.getDate()).padStart(2, '0')
    return `${d}/${m}/${y}`
  }
  return String(v).trim()
}

function normalizeHeader(s: string): string {
  return stripAccents(s).toLowerCase().replace(/\s+/g, ' ').trim()
}

/** Linhas só de posição de saldo no extrato (não são lançamentos). Inclui "S A L D O", "SALDO:", "Saldo do dia", etc. */
export function isSaldoBalanceLine(description: string): boolean {
  const raw = stripAccents(description).trim()
  if (!raw) return false
  const t = raw.toLowerCase()
  // Só letras: ignora espaços normais, NBSP, zero-width, etc. ("S A L D O", "S\u200bA L D O" → "saldo")
  const lettersOnly = t.replace(/[^a-z]/g, '')
  if (lettersOnly === 'saldo') return true
  if (lettersOnly.startsWith('saldo')) {
    const restLetters = lettersOnly.slice(5)
    if (!restLetters) return true
    if (
      /^(dodia|do|da|de|no|em|anterior|disponivel|atual|final|conta|dia|competencia)/.test(restLetters)
    ) {
      return true
    }
  }
  // BB às vezes exporta letras separadas: "S A L D O"
  const collapsed = t.replace(/\s/g, '')
  if (collapsed === 'saldo') return true
  if (/^saldo\b/.test(t)) return true
  if (/^s\s*a\s*l\s*d\s*o(\b|[\s:.,;!?\-]|$)/i.test(raw)) return true
  if (collapsed.startsWith('saldo')) {
    const rest = collapsed.slice(5)
    if (!rest) return true
    if (/^[^a-z]/.test(rest)) return true
    if (
      /^(dodia|do|da|de|no|em|anterior|disponivel|disponível|atual|final|conta|dia|competencia|competência)/.test(
        rest
      )
    ) {
      return true
    }
  }
  return false
}

export function parseBrNumber(raw: string): number {
  const t = raw.replace(/\u00a0/g, ' ').trim()
  if (!t) return NaN
  const neg = /^[\(-]/.test(t) || t.includes('-')
  const cleaned = t.replace(/[R$\s()]/gi, '')
  const lastComma = cleaned.lastIndexOf(',')
  const lastDot = cleaned.lastIndexOf('.')
  let n = cleaned.replace(/[^\d,.-]/g, '')
  if (lastComma > lastDot) {
    n = n.replace(/\./g, '').replace(',', '.')
  } else if (lastDot > lastComma) {
    n = n.replace(/,/g, '')
  } else if (lastComma >= 0) {
    n = n.replace(',', '.')
  }
  const v = parseFloat(n)
  if (Number.isNaN(v)) return NaN
  return neg && v > 0 ? -v : v
}

export function parseBrDateToIso(cell: string): string | null {
  const s = cell.trim()
  const m = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{2,4})$/)
  if (!m) return null
  let y = parseInt(m[3], 10)
  if (y < 100) y += y >= 70 ? 1900 : 2000
  const d = parseInt(m[1], 10)
  const mo = parseInt(m[2], 10)
  if (mo < 1 || mo > 12 || d < 1 || d > 31) return null
  return `${y}-${String(mo).padStart(2, '0')}-${String(d).padStart(2, '0')}`
}

function scoreHeaderRow(cells: string[]): number {
  const n = cells.map(normalizeHeader)
  let score = 0
  if (n.some((c) => c === 'data')) score += 2
  if (n.some((c) => c.includes('detalhe'))) score += 2
  if (n.some((c) => c.includes('historico') || c.includes('lancamento') || c.includes('descricao') || c.includes('identificacao'))) score += 2
  if (n.some((c) => c.includes('credito') || c.includes('credit'))) score += 1
  if (n.some((c) => c.includes('debito') || c.includes('debit'))) score += 1
  if (n.some((c) => c.includes('valor'))) score += 1
  return score
}

function findHeaderRow(matrix: (string | number | null | boolean)[][]): number {
  let best = -1
  let bestScore = 0
  for (let i = 0; i < Math.min(matrix.length, 40); i++) {
    const row = matrix[i].map(normCell)
    if (row.every((c) => !c)) continue
    const sc = scoreHeaderRow(row)
    if (sc > bestScore) {
      bestScore = sc
      best = i
    }
  }
  return bestScore >= 3 ? best : -1
}

function matchCol(headers: string[], pred: (h: string) => boolean): number {
  for (let i = 0; i < headers.length; i++) {
    if (pred(normalizeHeader(headers[i]))) return i
  }
  return -1
}

/** Coluna de texto do lançamento: prioriza Detalhes (extrato BB web), depois histórico/descrição. */
function findDescriptionCol(headers: string[]): number {
  const detalhes = matchCol(headers, (h) => h === 'detalhes' || h.includes('detalhe'))
  if (detalhes >= 0) return detalhes
  return matchCol(
    headers,
    (h) =>
      h.includes('historico') ||
      h.includes('descricao') ||
      h.includes('identificacao') ||
      h.includes('memo') ||
      h.includes('lancamento')
  )
}

/**
 * Extrai lançamentos do extrato BB. Retorna vazio se não reconhecer o layout.
 */
export function parseBancoDoBrasilExtrato(matrix: (string | number | null | boolean)[][]): ParsedBbRow[] {
  if (!matrix.length) return []

  const headerIdx = findHeaderRow(matrix)
  if (headerIdx < 0) return []

  const headers = matrix[headerIdx].map(normCell)
  const dataCol = matchCol(headers, (h) => h === 'data')
  const descCol = findDescriptionCol(headers)
  const lancamentoCol = matchCol(
    headers,
    (h) => h.includes('lancamento') && !h.includes('tipo')
  )
  let creditCol = matchCol(headers, (h) => h.includes('credito') && !h.includes('saldo'))
  let debitCol = matchCol(headers, (h) => h.includes('debito') && !h.includes('saldo'))
  const valorCol = matchCol(headers, (h) => h === 'valor' || (h.includes('valor') && !h.includes('saldo')))

  if (dataCol < 0 || descCol < 0) return []

  if (creditCol < 0 || debitCol < 0) {
    creditCol = -1
    debitCol = -1
  }

  const out: ParsedBbRow[] = []

  for (let r = headerIdx + 1; r < matrix.length; r++) {
    const row = matrix[r].map(normCell)
    if (!row.length) continue

    const dateStr = row[dataCol] || ''
    let desc = (row[descCol] || '').trim()
    if (!desc && lancamentoCol >= 0 && lancamentoCol !== descCol) {
      desc = (row[lancamentoCol] || '').trim()
    }
    if (!desc && !dateStr) continue

    const iso = parseBrDateToIso(dateStr)
    if (!iso) continue

    let amount = NaN
    let type: 'INCOME' | 'EXPENSE' = 'EXPENSE'

    if (creditCol >= 0 && debitCol >= 0) {
      const cVal = parseBrNumber(row[creditCol] || '')
      const dVal = parseBrNumber(row[debitCol] || '')
      const c = Number.isNaN(cVal) ? 0 : Math.abs(cVal)
      const d = Number.isNaN(dVal) ? 0 : Math.abs(dVal)
      if (d > 0) {
        amount = d
        type = 'EXPENSE'
      } else if (c > 0) {
        amount = c
        type = 'INCOME'
      }
    } else if (valorCol >= 0) {
      const v = parseBrNumber(row[valorCol] || '')
      if (!Number.isNaN(v) && v !== 0) {
        amount = Math.abs(v)
        type = v >= 0 ? 'INCOME' : 'EXPENSE'
      }
    }

    if (Number.isNaN(amount) || amount <= 0) continue

    if (isSaldoBalanceLine(desc)) continue

    out.push({ date: iso, description: desc.slice(0, 200), amount, type })
  }

  return out
}
