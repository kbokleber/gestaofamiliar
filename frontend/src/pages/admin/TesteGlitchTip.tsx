import { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import api from '../../lib/api'
import Button from '../../components/Button'
import { MENSAGEM_DE_TESTE, TIPO_DE_TESTE } from '../../lib/filtroLgpd'
import { useAuthStore } from '../../stores/authStore'

/**
 * Teste do GlitchTip, sem link no menu. Só funciona para administrador e com GF_SENTRY_TESTE=1 no backend.
 * Como remover: docs/monitoramento-erros-glitchtip.md, seção "Teste em produção".
 */
export default function TesteGlitchTip() {
  const admin = useAuthStore((estado) => estado.user?.is_superuser === true)
  const [aviso, setAviso] = useState('')
  const { data, isLoading } = useQuery({
    queryKey: ['teste-glitchtip'],
    queryFn: async () => (await api.get('/system/teste-glitchtip')).data,
    enabled: admin,
    retry: false,
    staleTime: 0,
  })

  const ligado = data?.ligado === true

  if (!admin) return <Navigate to="/" replace />
  if (isLoading) return <p className="p-4 text-sm text-gray-500">Carregando...</p>
  if (!ligado) return <p className="p-4 text-sm text-gray-700">O teste do GlitchTip está desligado.</p>

  const erroNoBackend = async () => {
    setAviso('Enviando...')
    const status = await api.post('/system/teste-glitchtip').then((r) => r.status, (e) => e?.response?.status)
    setAviso(status === 500
      ? 'Erro gerado no backend. Confira no projeto do backend no GlitchTip.'
      : `O backend não gerou o erro (resposta ${status ?? 'sem conexão'}).`)
  }

  const erroNoSite = () => {
    // Fora do React, como um erro qualquer da página: passa pelo window.onerror.
    setTimeout(() => {
      const erro = new Error(MENSAGEM_DE_TESTE)
      erro.name = TIPO_DE_TESTE
      throw erro
    })
    setAviso('Erro gerado no site. Confira no projeto do site no GlitchTip.')
  }

  return (
    <div className="max-w-xl space-y-4 p-4">
      <h1 className="text-xl font-semibold text-gray-900">Teste do GlitchTip</h1>
      <p className="text-sm text-gray-700">
        Cada botão gera um erro de propósito, com a mensagem fixa “{MENSAGEM_DE_TESTE}” e nenhum dado pessoal.
      </p>
      <div className="flex flex-wrap gap-2">
        <Button type="button" onClick={erroNoBackend}>Gerar erro no backend</Button>
        <Button type="button" onClick={erroNoSite}>Gerar erro no site</Button>
      </div>
      <p className="text-sm text-gray-700" role="status" aria-live="polite">{aviso}</p>
    </div>
  )
}
