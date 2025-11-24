import axios from 'axios'
import { useAuthStore } from '../stores/authStore'

// URL da API - usar variável de ambiente em produção ou URL relativa em desenvolvimento
// Em desenvolvimento, o Vite faz proxy de /api para http://localhost:8001
// Em produção, usar VITE_API_URL se definido, senão usar URL completa com IP padrão
const getApiBaseUrl = () => {
  const envUrl = import.meta.env.VITE_API_URL
  
  // Se a variável de ambiente está definida e válida, usar ela
  if (envUrl && envUrl.trim() !== '' && !envUrl.startsWith(':')) {
    return envUrl
  }
  
  // Se começar com : (sem protocolo), adicionar http:// e IP
  if (envUrl && envUrl.startsWith(':')) {
    return `http://89.116.186.192${envUrl}`
  }
  
  // Fallback: usar URL completa com IP padrão
  return 'http://89.116.186.192:8001/api/v1'
}

const API_BASE_URL = getApiBaseUrl()

// Debug: log da URL da API (sempre logar para debug)
if (typeof window !== 'undefined') {
  console.log('🔧 API Configuration:')
  console.log('  - API Base URL:', API_BASE_URL)
  console.log('  - VITE_API_URL env:', import.meta.env.VITE_API_URL)
  console.log('  - Mode:', import.meta.env.MODE)
  console.log('  - Dev:', import.meta.env.DEV)
}

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Interceptor para adicionar token em todas as requisições
api.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().token
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    // Debug em desenvolvimento
    if (import.meta.env.DEV) {
      const method = config.method?.toUpperCase() || 'UNKNOWN'
      const url = (config.baseURL || '') + (config.url || '')
      console.log('API Request:', method, url)
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Interceptor para lidar com erros de autenticação
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Debug em desenvolvimento
    if (import.meta.env.DEV) {
      console.error('API Error:', error.response?.status, error.response?.data || error.message)
      console.error('Request URL:', error.config?.url)
      console.error('Token presente:', !!useAuthStore.getState().token)
    }
    if (error.response?.status === 401) {
      console.warn('Token inválido ou expirado. Fazendo logout e redirecionando...')
      useAuthStore.getState().logout()
      // Usar setTimeout para garantir que o logout seja processado antes do redirecionamento
      setTimeout(() => {
        window.location.href = '/login'
      }, 100)
    }
    return Promise.reject(error)
  }
)

export default api
