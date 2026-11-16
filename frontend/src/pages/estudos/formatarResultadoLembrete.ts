export interface ResultadoLembrete {
  enviados?: { filho: string; tarefas: string[] }[]
  sem_tarefa?: string[]
  sem_inscricao?: string[]
}

export function formatarResultadoLembrete(data: ResultadoLembrete): string {
  const blocos: string[] = []
  for (const item of data.enviados ?? []) {
    const rotulo = item.tarefas.length > 1 ? 'pendências' : 'pendência'
    blocos.push(`${item.filho}: lembrete enviado — ${rotulo}: ${item.tarefas.join(', ')}`)
  }
  for (const nome of data.sem_tarefa ?? []) {
    blocos.push(`${nome}: sem pendências (nenhum envio)`)
  }
  for (const nome of data.sem_inscricao ?? []) {
    blocos.push(`${nome}: sem alerta no celular (nenhum envio)`)
  }
  return blocos.join('\n\n') || 'Nenhum filho para avisar.'
}
