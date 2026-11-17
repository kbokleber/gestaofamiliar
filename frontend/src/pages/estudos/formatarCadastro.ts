const formatoBrasilia = new Intl.DateTimeFormat('pt-BR', {
  timeZone: 'America/Sao_Paulo',
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23',
})

// A timestamp without an offset comes from the server in UTC.
function paraData(iso: string): Date {
  const temFuso = /(Z|[+-]\d{2}:?\d{2})$/i.test(iso)
  return new Date(temFuso ? iso : `${iso}Z`)
}

export function formatarCadastro(
  iso: string | null | undefined,
  tipo: 'atividade' | 'comunicado' = 'atividade',
): string | null {
  if (!iso) return null
  const data = paraData(iso)
  if (Number.isNaN(data.getTime())) return null
  const partes = Object.fromEntries(
    formatoBrasilia.formatToParts(data).map((parte) => [parte.type, parte.value]),
  )
  const rotulo = tipo === 'comunicado' ? 'Cadastrado' : 'Cadastrada'
  return `${rotulo} em ${partes.day}/${partes.month}/${partes.year} às ${partes.hour}:${partes.minute}`
}
