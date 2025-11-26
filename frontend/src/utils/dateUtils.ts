/**
 * Utilitários para formatação de datas no padrão brasileiro
 */

/**
 * Formata uma data ISO para o formato brasileiro DD/MM/YYYY
 * Lida com datas sem considerar timezone para evitar mudança de dia
 */
export const formatDateBR = (dateString: string | null | undefined): string => {
  if (!dateString) return '-'
  
  // Se a data vier como YYYY-MM-DD (sem hora), processar diretamente
  const dateOnly = dateString.split('T')[0]
  const parts = dateOnly.split('-')
  
  if (parts.length === 3) {
    const [year, month, day] = parts
    return `${day}/${month}/${year}`
  }
  
  // Fallback para datas com formato diferente
  const date = new Date(dateString)
  if (isNaN(date.getTime())) return '-'
  
  const day = date.getDate().toString().padStart(2, '0')
  const month = (date.getMonth() + 1).toString().padStart(2, '0')
  const year = date.getFullYear()
  
  return `${day}/${month}/${year}`
}

/**
 * Formata uma data ISO para o formato brasileiro DD/MM/YYYY HH:MM
 * Extrai diretamente da string para evitar problemas de timezone
 */
export const formatDateTimeBR = (dateString: string | null | undefined): string => {
  if (!dateString) return '-'
  
  // Remover timezone se presente (ex: -03:00 ou +00:00 ou Z)
  const cleaned = dateString.replace(/[+-]\d{2}:\d{2}$/, '').replace(/Z$/, '')
  
  // Tentar extrair diretamente da string (formato: YYYY-MM-DDTHH:mm:ss ou YYYY-MM-DDTHH:mm)
  const match = cleaned.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?/)
  if (match) {
    const [, year, month, day, hours, minutes] = match
    return `${day}/${month}/${year} ${hours}:${minutes}`
  }
  
  // Fallback: usar Date (pode ter problemas de timezone, mas é melhor que nada)
  const date = new Date(dateString)
  if (isNaN(date.getTime())) return '-'
  
  const day = date.getDate().toString().padStart(2, '0')
  const month = (date.getMonth() + 1).toString().padStart(2, '0')
  const year = date.getFullYear()
  const hours = date.getHours().toString().padStart(2, '0')
  const minutes = date.getMinutes().toString().padStart(2, '0')
  
  return `${day}/${month}/${year} ${hours}:${minutes}`
}

/**
 * Converte uma data ISO para o formato usado em inputs date (YYYY-MM-DD)
 * Lida com datas sem considerar timezone
 */
export const toDateInputValue = (dateString: string | null | undefined): string => {
  if (!dateString) return ''
  
  // Se a data vier como YYYY-MM-DD (sem hora), retornar diretamente
  const dateOnly = dateString.split('T')[0]
  
  // Validar formato YYYY-MM-DD
  if (/^\d{4}-\d{2}-\d{2}$/.test(dateOnly)) {
    return dateOnly
  }
  
  // Fallback para datas com formato diferente
  const date = new Date(dateString)
  if (isNaN(date.getTime())) return ''
  
  const year = date.getFullYear()
  const month = (date.getMonth() + 1).toString().padStart(2, '0')
  const day = date.getDate().toString().padStart(2, '0')
  
  return `${year}-${month}-${day}`
}

/**
 * Converte uma data ISO para o formato usado em inputs datetime-local (YYYY-MM-DDTHH:mm)
 * Extrai diretamente da string para evitar problemas de timezone
 */
export const toDateTimeInputValue = (dateString: string | null | undefined): string => {
  if (!dateString) return ''
  
  // Remover timezone se presente (ex: -03:00 ou +00:00 ou Z)
  const cleaned = dateString.replace(/[+-]\d{2}:\d{2}$/, '').replace(/Z$/, '')
  
  // Tentar extrair diretamente da string (formato: YYYY-MM-DDTHH:mm:ss ou YYYY-MM-DDTHH:mm)
  const match = cleaned.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?/)
  if (match) {
    const [, year, month, day, hours, minutes] = match
    return `${year}-${month}-${day}T${hours}:${minutes}`
  }
  
  // Fallback: usar Date (pode ter problemas de timezone, mas é melhor que nada)
  const date = new Date(dateString)
  if (isNaN(date.getTime())) return ''
  
  const year = date.getFullYear()
  const month = (date.getMonth() + 1).toString().padStart(2, '0')
  const day = date.getDate().toString().padStart(2, '0')
  const hours = date.getHours().toString().padStart(2, '0')
  const minutes = date.getMinutes().toString().padStart(2, '0')
  
  return `${year}-${month}-${day}T${hours}:${minutes}`
}

/**
 * Calcula a idade a partir de uma data de nascimento
 */
export const calculateAge = (birthDate: string): number => {
  const today = new Date()
  const birth = new Date(birthDate)
  let age = today.getFullYear() - birth.getFullYear()
  const monthDiff = today.getMonth() - birth.getMonth()
  
  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
    age--
  }
  
  return age
}

/**
 * Formata uma data para o formato por extenso em português
 * Ex: "6 de Novembro de 2025"
 */
export const formatDateFullBR = (dateString: string | null | undefined): string => {
  if (!dateString) return '-'
  
  const months = [
    'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
  ]
  
  // Se a data vier como YYYY-MM-DD (sem hora), processar diretamente
  const dateOnly = dateString.split('T')[0]
  const parts = dateOnly.split('-')
  
  if (parts.length === 3) {
    const [year, month, day] = parts
    const monthIndex = parseInt(month, 10) - 1
    if (monthIndex >= 0 && monthIndex < 12) {
      return `${parseInt(day, 10)} de ${months[monthIndex]} de ${year}`
    }
  }
  
  // Fallback para datas com formato diferente
  const date = new Date(dateString)
  if (isNaN(date.getTime())) return '-'
  
  const day = date.getDate()
  const monthIndex = date.getMonth()
  const year = date.getFullYear()
  
  return `${day} de ${months[monthIndex]} de ${year}`
}

/**
 * Compara uma data ISO com a data/hora atual, sem considerar timezone
 * Retorna true se a data for futura (maior que agora)
 * Extrai os valores diretamente da string para evitar problemas de timezone
 */
export const isFutureDateTime = (dateString: string | null | undefined): boolean => {
  if (!dateString) return false
  
  // Remover timezone se presente (ex: -03:00 ou +00:00 ou Z)
  const cleaned = dateString.replace(/[+-]\d{2}:\d{2}$/, '').replace(/Z$/, '')
  
  // Extrair data/hora da string ISO
  const match = cleaned.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?(?:\.(\d+))?/)
  if (!match) return false
  
  const [, year, month, day, hours, minutes, seconds = '0', milliseconds = '0'] = match
  
  // Criar Date object usando valores locais (sem conversão de timezone)
  const appointmentDate = new Date(
    parseInt(year, 10),
    parseInt(month, 10) - 1, // month é 0-indexed
    parseInt(day, 10),
    parseInt(hours, 10),
    parseInt(minutes, 10),
    parseInt(seconds, 10),
    parseInt(milliseconds.substring(0, 3), 10) // pegar apenas os primeiros 3 dígitos dos milissegundos
  )
  
  // Obter data/hora atual no timezone local
  const now = new Date()
  
  return appointmentDate > now
}

