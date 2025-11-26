import { useState, useEffect, useRef } from 'react'
import { formatDateTimeBR } from '../utils/dateUtils'

interface DateTimeInputProps {
  value: string // Formato YYYY-MM-DDTHH:mm (ou com timezone)
  onChange: (value: string) => void // Retorna YYYY-MM-DDTHH:mm:ss-03:00
  required?: boolean
  className?: string
  placeholder?: string
}

/**
 * Input de data/hora customizado que força exibição no formato brasileiro (DD/MM/YYYY HH:MM)
 * Usa input type="datetime-local" internamente mas exibe a data formatada em português
 */
export default function DateTimeInput({ value, onChange, required, className, placeholder }: DateTimeInputProps) {
  const [displayValue, setDisplayValue] = useState('')
  const [localValue, setLocalValue] = useState('')
  const [isFocused, setIsFocused] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const displayRef = useRef<HTMLInputElement>(null)

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

  // Sincronizar valor externo com input local e display
  useEffect(() => {
    const local = formatToLocal(value)
    setLocalValue(local)
    if (local) {
      const formatted = formatDateTimeBR(value)
      setDisplayValue(formatted)
    } else {
      setDisplayValue('')
    }
  }, [value])

  const handleDisplayClick = () => {
    // Focar no input de data/hora real
    if (inputRef.current) {
      // Tentar abrir o date picker nativo
      if ('showPicker' in inputRef.current && typeof inputRef.current.showPicker === 'function') {
        inputRef.current.showPicker()
      } else {
        inputRef.current.focus()
      }
    }
    setIsFocused(true)
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const inputValue = e.target.value
    setLocalValue(inputValue)
    
    // Converter para formato com timezone e notificar
    if (inputValue) {
      const isoDateTime = formatToISO(inputValue)
      const formatted = formatDateTimeBR(isoDateTime)
      setDisplayValue(formatted)
      onChange(isoDateTime)
    } else {
      setDisplayValue('')
      onChange('')
    }
  }

  const handleBlur = () => {
    setIsFocused(false)
    // Garantir que o valor de exibição está correto
    if (value) {
      setDisplayValue(formatDateTimeBR(value))
    }
  }

  return (
    <div className="relative w-full">
      {/* Input de exibição (sempre mostra formato brasileiro) */}
      <input
        ref={displayRef}
        type="text"
        value={displayValue}
        onClick={handleDisplayClick}
        readOnly
        placeholder={placeholder || 'dd/mm/aaaa hh:mm'}
        required={required}
        className={`${className || ''} cursor-pointer bg-white w-full relative z-10`}
        style={{
          minHeight: '44px',
          fontSize: '16px',
        }}
      />
      {/* Input de data/hora real (oculto, mas funcional) */}
      <input
        ref={inputRef}
        type="datetime-local"
        value={localValue}
        onChange={handleInputChange}
        onBlur={handleBlur}
        onFocus={() => setIsFocused(true)}
        required={required}
        className="absolute inset-0 opacity-0 cursor-pointer pointer-events-none w-full h-full"
        style={{
          width: '100%',
          height: '100%',
          zIndex: 1,
        }}
        lang="pt-BR"
        autoComplete="off"
        tabIndex={-1}
      />
    </div>
  )
}

