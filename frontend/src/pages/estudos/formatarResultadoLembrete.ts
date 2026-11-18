export interface ResultadoLembrete {
  enviados?: { filho: string; tarefas?: string[] | null; canal?: 'app' | 'navegador' | null }[] | null
  sem_tarefa?: string[] | null
  sem_inscricao?: string[] | null
}

export function formatarResultadoLembrete(data: ResultadoLembrete | null | undefined): string {
  const blocos: string[] = []
  for (const item of data?.enviados ?? []) {
    const tarefas = item.tarefas ?? []
    const rotulo = tarefas.length > 1 ? 'pendências' : 'pendência'
    const via = item.canal === 'app'
      ? ' pelo app do celular (chega em até 5 min)'
      : item.canal === 'navegador' ? ' pelo navegador' : ''
    blocos.push(`${item.filho}: lembrete enviado${via} — ${rotulo}: ${tarefas.join(', ')}`)
  }
  for (const nome of data?.sem_tarefa ?? []) {
    blocos.push(`${nome}: sem pendências (nenhum envio)`)
  }
  for (const nome of data?.sem_inscricao ?? []) {
    blocos.push(`${nome}: sem o app nem alerta no navegador (nenhum envio)`)
  }
  return blocos.join('\n\n') || 'Nenhum filho para avisar.'
}
