import { useState, useEffect, useRef } from 'react'
import { formatDateBR } from '../utils/dateUtils'

interface DateInputProps {
  value: string // Formato YYYY-MM-DD
  onChange: (value: string) => void // Retorna YYYY-MM-DD
  required?: boolean
  className?: string
  placeholder?: string
}

/**
 * Input de data customizado que força exibição no formato brasileiro (DD/MM/YYYY)
 * Usa input type="date" internamente mas exibe a data formatada em português
 */
export default function DateInput({ value, onChange, required, className, placeholder }: DateInputProps) {
  const [displayValue, setDisplayValue] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)
  const displayRef = useRef<HTMLInputElement>(null)

  // Atualizar valor de exibição quando o valor mudar
  useEffect(() => {
    if (value) {
      const formatted = formatDateBR(value)
      setDisplayValue(formatted)
    } else {
      setDisplayValue('')
    }
  }, [value])

  const handleDisplayClick = () => {
    // Focar no input de data real
    if (inputRef.current) {
      // Tentar abrir o date picker nativo
      if ('showPicker' in inputRef.current && typeof inputRef.current.showPicker === 'function') {
        inputRef.current.showPicker()
      } else {
        inputRef.current.focus()
      }
    }
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const inputValue = e.target.value
    if (inputValue) {
      // Formatar para exibição
      const formatted = formatDateBR(inputValue)
      setDisplayValue(formatted)
      onChange(inputValue)
    } else {
      setDisplayValue('')
      onChange('')
    }
  }

  const handleBlur = () => {
    // Garantir que o valor de exibição está correto
    if (value) {
      setDisplayValue(formatDateBR(value))
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
        placeholder={placeholder || 'dd/mm/aaaa'}
        required={required}
        className={`${className || ''} cursor-pointer bg-white w-full relative z-10`}
        style={{
          minHeight: '44px',
          fontSize: '16px',
        }}
      />
      {/* Input de data real (oculto, mas funcional) */}
      <input
        ref={inputRef}
        type="date"
        value={value || ''}
        onChange={handleInputChange}
        onBlur={handleBlur}
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

