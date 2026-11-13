/** Nome usado no download. Preserva o nome real e completa a extensão de PDF. */
export function nomeParaDownload(nome: string | null | undefined, tipo = ''): string {
  const base = String(nome || '')
    .replace(/[\r\n"]/g, '')
    .replace(/[\\/]/g, '_')
    .trim()
  const ehPdf = tipo.toLowerCase().includes('pdf') || base.toLowerCase().endsWith('.pdf')
  if (!base) return ehPdf ? 'documento.pdf' : 'arquivo'
  if (ehPdf && !base.toLowerCase().endsWith('.pdf')) return `${base}.pdf`
  return base
}

export function ehPdf(tipo?: string | null, nome?: string | null): boolean {
  return (tipo || '').toLowerCase().includes('pdf') || (nome || '').toLowerCase().endsWith('.pdf')
}

/**
 * Dispara o download com o nome real.
 * Um blob aberto em about:blank ou iframe vira, no Chrome do Android,
 * um chip "Abrir" com nome UUID e o PDF não aparece.
 */
export function baixarBlob(conteudo: Blob, nome: string, tipo?: string): void {
  const mime = tipo || conteudo.type || 'application/octet-stream'
  const arquivo = new File([conteudo], nome, { type: mime })
  const url = URL.createObjectURL(arquivo)
  const link = document.createElement('a')
  link.href = url
  link.download = nome
  link.rel = 'noopener'
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000)
}
