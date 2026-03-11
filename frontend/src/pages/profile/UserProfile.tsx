import { useState, useEffect } from 'react'
import {
  Key, Copy, RefreshCw, Trash2, Loader2, CheckCircle, AlertCircle,
  Eye, EyeOff, User
} from 'lucide-react'
import api from '../../lib/api'
import { useAuthStore } from '../../stores/authStore'

export default function UserProfile() {
  const { user } = useAuthStore()

  const [token, setToken] = useState<string | null>(null)
  const [tokenLoading, setTokenLoading] = useState(false)
  const [revoking, setRevoking] = useState(false)
  const [copied, setCopied] = useState(false)
  const [visible, setVisible] = useState(false)
  const [tokenError, setTokenError] = useState('')
  const [tokenSuccess, setTokenSuccess] = useState('')

  useEffect(() => {
    api.get('/users/me').then(({ data }) => {
      setToken(data.api_token || null)
    }).catch(() => {})
  }, [])

  const handleGenerate = async () => {
    if (token && !confirm('Isso vai invalidar o token atual e gerar um novo. Tem certeza?')) return
    setTokenLoading(true); setTokenError(''); setTokenSuccess('')
    try {
      const { data } = await api.post<{ api_token: string }>('/users/me/api-token')
      setToken(data.api_token)
      setVisible(true)
      setTokenSuccess('Token gerado! Copie agora — ele será parcialmente ocultado na próxima visita.')
    } catch (err: any) {
      setTokenError(err.response?.data?.detail || 'Erro ao gerar token.')
    } finally {
      setTokenLoading(false)
    }
  }

  const handleRevoke = async () => {
    if (!confirm('Revogar o token de API? Qualquer integração que usa este token perderá acesso.')) return
    setRevoking(true); setTokenError(''); setTokenSuccess('')
    try {
      await api.delete('/users/me/api-token')
      setToken(null); setVisible(false)
      setTokenSuccess('Token revogado com sucesso.')
    } catch (err: any) {
      setTokenError(err.response?.data?.detail || 'Erro ao revogar token.')
    } finally {
      setRevoking(false)
    }
  }

  const handleCopy = async () => {
    if (!token) return
    await navigator.clipboard.writeText(token)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const maskedToken = token
    ? token.substring(0, 8) + '•'.repeat(Math.max(0, token.length - 12)) + token.substring(token.length - 4)
    : null

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <User className="h-7 w-7 text-orange-500" />
          Meu Perfil
        </h1>
        <p className="mt-1 text-sm text-gray-600">Gerencie suas informações e token de acesso à API.</p>
      </div>

      {/* User info */}
      <section className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 flex items-center gap-4">
        <div className="h-12 w-12 rounded-full bg-orange-100 flex items-center justify-center">
          <span className="text-orange-600 font-bold text-lg">
            {(user?.first_name?.[0] || user?.username?.[0] || '?').toUpperCase()}
          </span>
        </div>
        <div>
          <p className="font-semibold text-gray-900">
            {user?.first_name && user?.last_name ? `${user.first_name} ${user.last_name}` : user?.username}
          </p>
          <p className="text-sm text-gray-500">{user?.email}</p>
          <p className="text-xs text-gray-400 mt-0.5">
            {user?.is_superuser ? 'Administrador' : user?.is_staff ? 'Staff' : 'Usuário'}
          </p>
        </div>
      </section>

      {/* API Token */}
      <section className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-4">
        <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
          <Key className="h-5 w-5 text-orange-500" />
          Token de API
        </h2>
        <p className="text-sm text-gray-500">
          Use este token para autenticar chamadas externas (IA, scripts, integrações) via header{' '}
          <code className="bg-gray-100 px-1 py-0.5 rounded text-xs font-mono">X-API-Token</code>.
        </p>

        {tokenError && (
          <div className="flex items-center gap-2 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
            <AlertCircle className="h-4 w-4 flex-shrink-0" />{tokenError}
          </div>
        )}
        {tokenSuccess && (
          <div className="flex items-center gap-2 bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg text-sm">
            <CheckCircle className="h-4 w-4 flex-shrink-0" />{tokenSuccess}
          </div>
        )}

        {token ? (
          <>
            <div className="flex items-center gap-2">
              <div className="flex-1 bg-gray-50 border border-gray-200 rounded-lg px-4 py-3 font-mono text-sm text-gray-800 break-all">
                {visible ? token : maskedToken}
              </div>
              <button onClick={() => setVisible(!visible)} className="p-2 text-gray-400 hover:text-gray-700 rounded-lg transition-colors" title={visible ? 'Ocultar' : 'Mostrar'}>
                {visible ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
              </button>
              <button onClick={handleCopy} className="p-2 text-gray-400 hover:text-orange-600 rounded-lg transition-colors" title="Copiar">
                {copied ? <CheckCircle className="h-5 w-5 text-green-600" /> : <Copy className="h-5 w-5" />}
              </button>
            </div>
            <div className="flex gap-3 flex-wrap">
              <button onClick={handleGenerate} disabled={tokenLoading}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium bg-orange-500 text-white rounded-lg hover:bg-orange-600 disabled:opacity-50 transition-colors">
                {tokenLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
                Regenerar
              </button>
              <button onClick={handleRevoke} disabled={revoking}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-red-600 border border-red-200 rounded-lg hover:bg-red-50 disabled:opacity-50 transition-colors">
                {revoking ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
                Revogar
              </button>
            </div>
          </>
        ) : (
          <div className="space-y-3">
            <p className="text-sm text-gray-500">Nenhum token gerado ainda.</p>
            <button onClick={handleGenerate} disabled={tokenLoading}
              className="inline-flex items-center gap-2 px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 font-medium text-sm disabled:opacity-50 transition-colors">
              {tokenLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Key className="h-4 w-4" />}
              Gerar token
            </button>
          </div>
        )}

        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 space-y-2">
          <p className="text-xs font-semibold text-blue-800">Como usar:</p>
          <div className="bg-blue-900 text-blue-100 rounded px-3 py-2 font-mono text-xs overflow-x-auto">
            <div>GET /api/v1/healthcare/members</div>
            <div className="text-blue-300">X-API-Token: {token ? maskedToken : 'seu-token-aqui'}</div>
          </div>
          <p className="text-xs text-blue-700">⚠️ Guarde em local seguro. O token tem os mesmos acessos que sua conta.</p>
        </div>
      </section>
    </div>
  )
}
