import { useState, useEffect } from 'react'

interface DateTimeInputProps {
  value: string // Formato YYYY-MM-DDTHH:mm
  onChange: (value: string) => void // Retorna YYYY-MM-DDTHH:mm
  required?: boolean
  className?: string
  placeholder?: string
}

/**
 * Input de data/hora customizado que exibe no formato DD/MM/YYYY HH:MM
 * Mas trabalha internamente com YYYY-MM-DDTHH:mm para compatibilidade com o backend
 */
export default function DateTimeInput({ value, onChange, required, className, placeholder }: DateTimeInputProps) {
  const [displayValue, setDisplayValue] = useState('')

  // Converte YYYY-MM-DDTHH:mm para DD/MM/YYYY HH:MM
  const formatToDisplay = (isoDateTime: string): string => {
    if (!isoDateTime) return ''
    const [datePart, timePart] = isoDateTime.split('T')
    if (datePart) {
      const parts = datePart.split('-')
      if (parts.length === 3) {
        const formattedDate = `${parts[2]}/${parts[1]}/${parts[0]}`
        return timePart ? `${formattedDate} ${timePart}` : formattedDate
      }
    }
    return ''
  }

  // Converte DD/MM/YYYY HH:MM para YYYY-MM-DDTHH:mm
  const formatToISO = (brDateTime: string): string => {
    const cleaned = brDateTime.replace(/[^\d]/g, '')
    if (cleaned.length >= 12) {
      const day = cleaned.substring(0, 2)
      const month = cleaned.substring(2, 4)
      const year = cleaned.substring(4, 8)
      const hour = cleaned.substring(8, 10)
      const minute = cleaned.substring(10, 12)
      return `${year}-${month}-${day}T${hour}:${minute}`
    }
    return ''
  }

  // Aplica máscara DD/MM/YYYY HH:MM
  const applyMask = (input: string): string => {
    const cleaned = input.replace(/[^\d]/g, '')
    let masked = cleaned
    
    if (cleaned.length > 2) {
      masked = cleaned.substring(0, 2) + '/' + cleaned.substring(2)
    }
    if (cleaned.length > 4) {
      masked = cleaned.substring(0, 2) + '/' + cleaned.substring(2, 4) + '/' + cleaned.substring(4)
    }
    if (cleaned.length > 8) {
      masked = cleaned.substring(0, 2) + '/' + cleaned.substring(2, 4) + '/' + 
               cleaned.substring(4, 8) + ' ' + cleaned.substring(8)
    }
    if (cleaned.length > 10) {
      masked = cleaned.substring(0, 2) + '/' + cleaned.substring(2, 4) + '/' + 
               cleaned.substring(4, 8) + ' ' + cleaned.substring(8, 10) + ':' + 
               cleaned.substring(10, 12)
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

    // Se a data/hora está completa (16 caracteres: DD/MM/YYYY HH:MM), converter e notificar
    if (masked.length === 16) {
      const isoDateTime = formatToISO(masked)
      if (isoDateTime) {
        onChange(isoDateTime)
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
    if (displayValue && displayValue.length < 16) {
      alert('Por favor, preencha a data e hora completamente no formato DD/MM/AAAA HH:MM')
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
      placeholder={placeholder || 'DD/MM/AAAA HH:MM'}
      maxLength={16}
    />
  )
}

