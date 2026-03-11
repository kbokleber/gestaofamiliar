import { useState, useEffect } from 'react'
import { Key, Copy, RefreshCw, Trash2, Loader2, CheckCircle, AlertCircle, Eye, EyeOff } from 'lucide-react'
import api from '../../lib/api'
import { useAuthStore } from '../../stores/authStore'

export default function ApiTokenConfig() {
  const { user } = useAuthStore()
  const [token, setToken] = useState<string | null>(user?.api_token || null)
  const [loading, setLoading] = useState(false)
  const [revoking, setRevoking] = useState(false)
  const [copied, setCopied] = useState(false)
  const [visible, setVisible] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  // Carregar token do perfil do usuário ao montar
  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const { data } = await api.get('/users/me')
        setToken(data.api_token || null)
      } catch {
        // silently fail
      }
    }
    fetchProfile()
  }, [])

  const handleGenerate = async () => {
    if (token && !confirm('Isso vai invalidar o token atual e gerar um novo. Tem certeza?')) return
    setLoading(true)
    setError('')
    setSuccess('')
    try {
      const { data } = await api.post<{ api_token: string }>('/users/me/api-token')
      setToken(data.api_token)
      setVisible(true)
      setSuccess('Token gerado com sucesso! Copie agora — ele não ficará visível na próxima vez que entrar.')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erro ao gerar token.')
    } finally {
      setLoading(false)
    }
  }

  const handleRevoke = async () => {
    if (!confirm('Revogar o token de API? Qualquer sistema usando este token perderá acesso imediatamente.')) return
    setRevoking(true)
    setError('')
    setSuccess('')
    try {
      await api.delete('/users/me/api-token')
      setToken(null)
      setVisible(false)
      setSuccess('Token revogado com sucesso.')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erro ao revogar token.')
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
          <Key className="h-7 w-7 text-orange-500" />
          Token de API
        </h1>
        <p className="mt-1 text-sm text-gray-600">
          Use este token para autenticar chamadas de API externas (IA, scripts, integrações) sem precisar de login.
          Envie o token no header <code className="bg-gray-100 px-1 py-0.5 rounded text-xs font-mono">X-API-Token</code> em suas requisições.
        </p>
      </div>

      {error && (
        <div className="flex items-center gap-2 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
          <AlertCircle className="h-5 w-5 flex-shrink-0" />
          {error}
        </div>
      )}
      {success && (
        <div className="flex items-center gap-2 bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg text-sm">
          <CheckCircle className="h-5 w-5 flex-shrink-0" />
          {success}
        </div>
      )}

      {/* Token display */}
      <section className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-4">
        <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
          <Key className="h-5 w-5 text-orange-500" />
          Seu Token de API
        </h2>

        {token ? (
          <>
            <div className="flex items-center gap-2">
              <div className="flex-1 bg-gray-50 border border-gray-200 rounded-lg px-4 py-3 font-mono text-sm text-gray-800 break-all">
                {visible ? token : maskedToken}
              </div>
              <button
                type="button"
                onClick={() => setVisible(!visible)}
                className="p-2 text-gray-400 hover:text-gray-700 rounded-lg transition-colors"
                title={visible ? 'Ocultar token' : 'Mostrar token'}
              >
                {visible ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
              </button>
              <button
                type="button"
                onClick={handleCopy}
                className="p-2 text-gray-400 hover:text-orange-600 rounded-lg transition-colors"
                title="Copiar token"
              >
                {copied ? <CheckCircle className="h-5 w-5 text-green-600" /> : <Copy className="h-5 w-5" />}
              </button>
            </div>

            <div className="flex gap-3 flex-wrap">
              <button
                type="button"
                onClick={handleGenerate}
                disabled={loading}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium bg-orange-500 text-white rounded-lg hover:bg-orange-600 disabled:opacity-50 transition-colors"
              >
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
                Regenerar token
              </button>
              <button
                type="button"
                onClick={handleRevoke}
                disabled={revoking}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-red-600 border border-red-200 rounded-lg hover:bg-red-50 disabled:opacity-50 transition-colors"
              >
                {revoking ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
                Revogar token
              </button>
            </div>
          </>
        ) : (
          <div className="space-y-3">
            <p className="text-sm text-gray-500">
              Nenhum token de API gerado ainda. Clique em <strong>Gerar token</strong> para criar um.
            </p>
            <button
              type="button"
              onClick={handleGenerate}
              disabled={loading}
              className="inline-flex items-center gap-2 px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 font-medium text-sm disabled:opacity-50 transition-colors"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Key className="h-4 w-4" />}
              Gerar token
            </button>
          </div>
        )}
      </section>

      {/* Como usar */}
      <section className="bg-blue-50 border border-blue-200 rounded-xl p-5 space-y-3">
        <h2 className="text-sm font-semibold text-blue-900">Como usar o token</h2>
        <p className="text-sm text-blue-800">
          Inclua o token em qualquer requisição usando o header HTTP:
        </p>
        <div className="bg-blue-900 text-blue-100 rounded-lg px-4 py-3 font-mono text-xs overflow-x-auto">
          <div>GET https://seusite.com/api/v1/healthcare/members</div>
          <div className="text-blue-300">X-API-Token: {token ? (visible ? token : (token.substring(0, 8) + '...')) : 'seu-token-aqui'}</div>
        </div>
        <p className="text-xs text-blue-700">
          ⚠️ Guarde o token em local seguro. Quem tiver o token terá o mesmo acesso que você no sistema.
        </p>
      </section>
    </div>
  )
}
