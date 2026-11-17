// Elements inside a clickable row that keep their own behavior.
export const SELETOR_INTERATIVO = 'button, a, input, select, textarea, label, [data-no-row-click]'

interface AlvoClique {
  closest(seletor: string): unknown
}

/**
 * True when a click on a row should open it: not on a control or marked
 * element, and not the end of a text selection.
 */
export function deveAbrirPeloClique(alvo: AlvoClique | null, textoSelecionado: string): boolean {
  if (textoSelecionado.trim().length > 0) return false
  if (alvo && alvo.closest(SELETOR_INTERATIVO)) return false
  return true
}

/** True for Enter or Space pressed on the row itself, not on a control inside it. */
export function deveAbrirPeloTeclado(tecla: string, noProprioElemento: boolean): boolean {
  return noProprioElemento && (tecla === 'Enter' || tecla === ' ')
}
