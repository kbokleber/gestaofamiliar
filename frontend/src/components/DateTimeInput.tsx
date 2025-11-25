import { useState, useEffect } from 'react'

interface DateTimeInputProps {
  value: string // Formato YYYY-MM-DDTHH:mm (ou com timezone)
  onChange: (value: string) => void // Retorna YYYY-MM-DDTHH:mm:ss-03:00
  required?: boolean
  className?: string
  placeholder?: string
}

/**
 * Input de data/hora com calendário nativo (melhor para mobile)
 * Usa input type="datetime-local" que mostra calendário nativo
 * Converte automaticamente para timezone do Brasil (-03:00) ao enviar
 */
export default function DateTimeInput({ value, onChange, required, className, placeholder }: DateTimeInputProps) {
  const [localValue, setLocalValue] = useState('')

  // Converte YYYY-MM-DDTHH:mm (ou com timezone) para YYYY-MM-DDTHH:mm (formato datetime-local)
  const formatToLocal = (isoDateTime: string): string => {
    if (!isoDateTime) return ''
    // Remover timezone se presente (ex: -03:00 ou +00:00 ou Z)
    const cleaned = isoDateTime.replace(/[+-]\d{2}:\d{2}$/, '').replace(/Z$/, '')
    // Extrair apenas YYYY-MM-DDTHH:mm (remover segundos se houver)
    const match = cleaned.match(/^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2})/)
    return match ? match[1] : ''
  }

  // Converte YYYY-MM-DDTHH:mm (do datetime-local) para YYYY-MM-DDTHH:mm:ss-03:00 (timezone do Brasil)
  const formatToISO = (localDateTime: string): string => {
    if (!localDateTime) return ''
    // Adicionar segundos e timezone do Brasil (UTC-3)
    // O backend espera DateTime(timezone=True), então precisamos enviar com timezone
    return `${localDateTime}:00-03:00`
  }

  // Sincronizar valor externo com input local
  useEffect(() => {
    setLocalValue(formatToLocal(value))
  }, [value])

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const inputValue = e.target.value
    setLocalValue(inputValue)
    
    // Converter para formato com timezone e notificar
    if (inputValue) {
      const isoDateTime = formatToISO(inputValue)
      onChange(isoDateTime)
    } else {
      onChange('')
    }
  }

  return (
    <input
      type="datetime-local"
      value={localValue}
      onChange={handleChange}
      required={required}
      className={`${className || ''} datetime-input-mobile`}
      placeholder={placeholder}
      autoComplete="off"
      style={{
        minHeight: '44px', // Tamanho mínimo para touch targets no mobile
        fontSize: '16px', // Previne zoom no iOS quando o input recebe foco
      }}
    />
  )
}

