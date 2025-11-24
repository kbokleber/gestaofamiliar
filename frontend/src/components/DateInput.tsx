import { useState, useEffect } from 'react'

interface DateInputProps {
  value: string // Formato YYYY-MM-DD
  onChange: (value: string) => void // Retorna YYYY-MM-DD
  required?: boolean
  className?: string
  placeholder?: string
}

/**
 * Input de data customizado que exibe e aceita entrada no formato DD/MM/YYYY
 * Mas trabalha internamente com YYYY-MM-DD para compatibilidade com o backend
 */
export default function DateInput({ value, onChange, required, className, placeholder }: DateInputProps) {
  const [displayValue, setDisplayValue] = useState('')

  // Converte YYYY-MM-DD para DD/MM/YYYY
  const formatToDisplay = (isoDate: string): string => {
    if (!isoDate) return ''
    const parts = isoDate.split('-')
    if (parts.length === 3) {
      return `${parts[2]}/${parts[1]}/${parts[0]}`
    }
    return ''
  }

  // Converte DD/MM/YYYY para YYYY-MM-DD
  const formatToISO = (brDate: string): string => {
    const cleaned = brDate.replace(/\D/g, '')
    if (cleaned.length === 8) {
      const day = cleaned.substring(0, 2)
      const month = cleaned.substring(2, 4)
      const year = cleaned.substring(4, 8)
      return `${year}-${month}-${day}`
    }
    return ''
  }

  // Aplica máscara DD/MM/YYYY
  const applyMask = (input: string): string => {
    const cleaned = input.replace(/\D/g, '')
    let masked = cleaned
    
    if (cleaned.length > 2) {
      masked = cleaned.substring(0, 2) + '/' + cleaned.substring(2)
    }
    if (cleaned.length > 4) {
      masked = cleaned.substring(0, 2) + '/' + cleaned.substring(2, 4) + '/' + cleaned.substring(4, 8)
    }
    
    return masked
  }

  // Sincronizar valor externo com display
  useEffect(() => {
    setDisplayValue(formatToDisplay(value))
  }, [value])

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const input = e.target.value
    const masked = applyMask(input)
    setDisplayValue(masked)

    // Se a data está completa (10 caracteres: DD/MM/YYYY), converter e notificar
    if (masked.length === 10) {
      const isoDate = formatToISO(masked)
      if (isoDate) {
        onChange(isoDate)
      }
    } else if (input === '') {
      onChange('')
    } else {
      // Campo incompleto - notificar com string vazia
      onChange('')
    }
  }

  const handleBlur = () => {
    // Ao sair do campo, validar se está completo
    if (displayValue && displayValue.length < 10) {
      alert('Por favor, preencha a data completamente no formato DD/MM/AAAA')
      setDisplayValue('')
      onChange('')
    }
  }

  return (
    <input
      type="text"
      value={displayValue}
      onChange={handleChange}
      onBlur={handleBlur}
      required={required}
      className={className}
      placeholder={placeholder || 'DD/MM/AAAA'}
      maxLength={10}
    />
  )
}

