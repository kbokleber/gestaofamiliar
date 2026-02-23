import { Loader2 } from 'lucide-react'

interface LoadingProps {
  message?: string
  fullScreen?: boolean
  size?: 'sm' | 'md' | 'lg'
}

export default function Loading({ 
  message = 'Carregando...', 
  fullScreen = true,
  size = 'lg' 
}: LoadingProps) {
  const sizeClasses = {
    sm: 'h-6 w-6',
    md: 'h-10 w-10',
    lg: 'h-16 w-16'
  }

  const textSizeClasses = {
    sm: 'text-sm',
    md: 'text-base',
    lg: 'text-lg'
  }

  const content = (
    <div
      className="flex flex-col items-center justify-center gap-4"
      role="status"
      aria-live="polite"
      aria-label={message}
    >
      {/* Spinner animado */}
      <div className="relative">
        {/* Círculo externo com gradiente */}
        <div className={`${sizeClasses[size]} rounded-full border-4 border-blue-100`} />
        {/* Spinner interno */}
        <Loader2 
          className={`${sizeClasses[size]} text-blue-600 animate-spin absolute top-0 left-0`}
        />
      </div>
      
      {/* Mensagem */}
      <div className="flex flex-col items-center gap-1">
        <p className={`${textSizeClasses[size]} font-medium text-gray-700`}>
          {message}
        </p>
        {/* Indicador de progresso animado */}
        <div className="flex gap-1">
          <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
          <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
          <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
        </div>
      </div>
    </div>
  )

  if (fullScreen) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center bg-gray-50/50">
        {content}
      </div>
    )
  }

  return content
}

// Componente de loading inline para uso em botões ou cards
export function LoadingSpinner({ className = '' }: { className?: string }) {
  return (
    <Loader2 className={`animate-spin ${className}`} />
  )
}

// Skeleton loader para cards
export function LoadingSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className="space-y-4">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="bg-white rounded-lg shadow p-4 animate-pulse">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-gray-200 rounded-full" />
            <div className="flex-1 space-y-2">
              <div className="h-4 bg-gray-200 rounded w-3/4" />
              <div className="h-3 bg-gray-200 rounded w-1/2" />
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

