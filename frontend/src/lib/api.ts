import axios from 'axios'
import { useAuthStore } from '../stores/authStore'

// URL da API - usar variável de ambiente em produção ou URL relativa em desenvolvimento
// Em desenvolvimento, o Vite faz proxy de /api para http://localhost:8001
// Em produção, usar VITE_API_URL se definido, senão usar /api/v1 (relativo)
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1'

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
      console.log('API Request:', config.method?.toUpperCase(), config.baseURL + config.url)
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
