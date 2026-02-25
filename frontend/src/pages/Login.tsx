import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import { authService } from '../services/authService'
import { Heart } from 'lucide-react'
import { APP_VERSION } from '../config/version'

export default function Login() {
  const navigate = useNavigate()
  const setAuth = useAuthStore((state) => state.setAuth)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [formData, setFormData] = useState({
    username: '',
    password: '',
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      console.log('Tentando fazer login com:', formData.username)
      const { access_token } = await authService.login(formData)
      console.log('Login bem-sucedido! Token:', access_token.substring(0, 20) + '...')
      
      // IMPORTANTE: Salvar o token ANTES de buscar os dados do usuário
      // para que o interceptor possa usá-lo
      useAuthStore.setState({ token: access_token })
      
      // Buscar dados do usuário
      console.log('Buscando dados do usuário...')
      const userData = await authService.getMe()
      console.log('Dados do usuário:', userData)
      
      setAuth(userData, access_token)
      navigate('/')
    } catch (err: any) {
      if (import.meta.env.DEV) {
        console.error('Erro no login:', err)
      }
      // Erro de rede / servidor não responde
      if (err.code === 'ECONNREFUSED' || err.code === 'ERR_NETWORK' || err.message?.includes('Network Error')) {
        setError('Não foi possível conectar ao servidor. Verifique se o backend está rodando (ex: porta 8001 ou 8081).')
        return
      }
      if (err.code === 'ECONNABORTED') {
        setError('O servidor demorou para responder. Tente novamente.')
        return
      }
      const raw = err.response?.data?.detail ?? err.message ?? 'Erro ao fazer login'
      const errorMsg = Array.isArray(raw) ? raw.map((x: { msg?: string }) => x?.msg ?? String(x)).join('. ') : String(raw)
      setError(errorMsg || 'Erro ao fazer login')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 px-4">
      <div className="max-w-md w-full space-y-8 bg-white p-8 rounded-xl shadow-lg">
        <div className="text-center">
          <div className="flex justify-center">
            <Heart className="h-12 w-12 text-indigo-600" />
          </div>
          <h2 className="mt-6 text-3xl font-bold text-gray-900">
            Gestão Familiar
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            Entre com sua conta
          </p>
          <p className="mt-1 text-xs text-gray-500">
            Versão {APP_VERSION}
          </p>
        </div>

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-md text-sm">
              {error}
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label htmlFor="username" className="block text-sm font-medium text-gray-700">
                Usuário
              </label>
              <input
                id="username"
                type="text"
                required
                value={formData.username}
                onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                Senha
              </label>
              <input
                id="password"
                type="password"
                required
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full flex justify-center py-3 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Entrando...' : 'Entrar'}
          </button>
        </form>
      </div>
    </div>
  )
}

