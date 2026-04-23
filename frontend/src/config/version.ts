const FALLBACK_VERSION = 'dev-local'
const FALLBACK_BUILD_LABEL = 'indisponível'

export const APP_VERSION = import.meta.env.VITE_APP_VERSION || FALLBACK_VERSION
export const APP_BUILD_TIME = import.meta.env.VITE_BUILD_TIME || ''

export function extractRevision(value?: string | null): string {
  if (!value) return 'dev'
  const match = value.match(/[a-f0-9]{7,40}/i)
  return match ? match[0].slice(0, 7).toLowerCase() : 'dev'
}

export function formatBuildTimestamp(value?: string | null): string {
  if (!value) return FALLBACK_BUILD_LABEL
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return FALLBACK_BUILD_LABEL
  return date.toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

