import type { Document } from '../components/DocumentUpload'

/** Lê o campo "documents" da API (string JSON com uma lista). Devolve [] se vazio ou inválido. */
export function lerDocumentos(raw: unknown): Document[] {
  if (Array.isArray(raw)) return raw as Document[]
  if (typeof raw !== 'string' || raw.trim() === '') return []
  try {
    const lista = JSON.parse(raw)
    return Array.isArray(lista) ? (lista as Document[]) : []
  } catch {
    return []
  }
}
