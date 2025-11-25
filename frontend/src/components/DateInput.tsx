import { useState, useEffect } from 'react'

interface DateInputProps {
  value: string // Formato YYYY-MM-DD
  onChange: (value: string) => void // Retorna YYYY-MM-DD
  required?: boolean
  className?: string
  placeholder?: string
}

/**
 * Input de data com calendário nativo (melhor para mobile)
 * Usa input type="date" que mostra calendário nativo
 * Trabalha diretamente com YYYY-MM-DD (formato ISO) para compatibilidade com o backend
 */
export default function DateInput({ value, onChange, required, className, placeholder }: DateInputProps) {
  const [localValue, setLocalValue] = useState('')

  // Sincronizar valor externo com input local
  useEffect(() => {
    // O input type="date" já espera YYYY-MM-DD, então podemos usar diretamente
    setLocalValue(value || '')
  }, [value])

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const inputValue = e.target.value
    setLocalValue(inputValue)
    // O valor já vem no formato YYYY-MM-DD, então podemos passar diretamente
    onChange(inputValue)
  }

  return (
    <input
      type="date"
      value={localValue}
      onChange={handleChange}
      required={required}
      className={`${className || ''} date-input-mobile`}
      placeholder={placeholder}
      autoComplete="off"
      style={{
        minHeight: '44px', // Tamanho mínimo para touch targets no mobile
        fontSize: '16px', // Previne zoom no iOS quando o input recebe foco
      }}
    />
  )
}

