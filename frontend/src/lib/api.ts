import axios from 'axios'
import { rememberBlockedMessage } from '../pages/AcessoNegado'
import { getAccessToken, keycloak, keycloakEnabled, logoutKeycloak } from './keycloak'
import { useAuthStore } from '../stores/authStore'

// URL da API - usar variável de ambiente em produção ou URL relativa
// Em desenvolvimento, o Vite faz proxy de /api para http://localhost:8001
// Em produção, usar URL relativa para evitar Mixed Content (HTTPS -> HTTP)
// Se acessando por IP direto (HTTP), usar URL do backend diretamente
const getApiBaseUrl = () => {
  // Se estiver em desenvolvimento, usar a URL do Vite proxy
  if (import.meta.env.DEV) {
    return '/api/v1'
  }
  
  const envUrl = import.meta.env.VITE_API_URL
  
  // Se a variável de ambiente está definida e é uma URL relativa, usar ela
  if (envUrl && envUrl.trim() !== '' && envUrl.startsWith('/')) {
    return envUrl
  }
  
  // Detectar se está acessando por IP direto (HTTP na porta 5173)
  if (typeof window !== 'undefined') {
    const { protocol, hostname, port } = window.location
    
    // Se está em HTTP e na porta 5173 (acesso direto por IP), usar URL do backend
    if (protocol === 'http:' && port === '5173') {
      // Construir URL do backend (mesmo IP, porta 8001)
      const backendUrl = `http://${hostname}:8001/api/v1`
      console.log('🔧 Acesso por IP direto detectado. Usando backend direto:', backendUrl)
      return backendUrl
    }
    
    // Se a URL começa com http:// e a página está em HTTPS, usar URL relativa
    // Isso evita Mixed Content errors
    if (envUrl && envUrl.startsWith('http://')) {
      if (protocol === 'https:') {
        console.warn('⚠️ URL HTTP detectada em página HTTPS. Usando URL relativa para evitar Mixed Content.')
        // Extrair o path da URL HTTP
        try {
          const url = new URL(envUrl)
          return url.pathname || '/api/v1'
        } catch {
          return '/api/v1'
        }
      }
      // Se a página também é HTTP, pode usar a URL HTTP
      return envUrl
    }
  }
  
  // Fallback: usar URL relativa (funciona com DNS via NPM)
  // O NPM vai fazer o proxy para o backend
  return '/api/v1'
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
function authDetail(error: { response?: { data?: { detail?: unknown } }; message?: string }) {
  const detail = error.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map((item: { msg?: string }) => item?.msg ?? String(item)).join('; ')
  }
  return error.message || ''
}

function isAccessBlocked(status: number | undefined, detail: string) {
  if (status === 403 && (detail.includes('papel') || detail.includes('inativo'))) {
    return true
  }
  return status === 401 && detail.includes('não cadastrado')
}

api.interceptors.request.use(
  async (config) => {
    const token = keycloakEnabled ? await getAccessToken() : useAuthStore.getState().token
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
      if (keycloakEnabled) {
        useAuthStore.setState({ token })
      }
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
  async (error) => {
    const detailText = authDetail(error)
    if (detailText) {
      error.message = detailText
    }
    if (import.meta.env.DEV) {
      console.error('API Error:', error.response?.status, error.response?.data || error.message)
      console.error('Request URL:', error.config?.url)
      console.error('Token presente:', !!useAuthStore.getState().token)
    }

    const status = error.response?.status as number | undefined
    if (isAccessBlocked(status, detailText)) {
      rememberBlockedMessage(detailText)
      useAuthStore.getState().logout()
      if (!window.location.pathname.startsWith('/acesso-negado')) {
        window.location.replace('/acesso-negado')
      }
      return Promise.reject(error)
    }

    const requestConfig = error.config as { _retry?: boolean; headers: { Authorization?: string } } | undefined
    if (status === 401 && keycloakEnabled && keycloak && requestConfig && !requestConfig._retry) {
      requestConfig._retry = true
      try {
        await keycloak.updateToken(10_000)
        if (keycloak.token) {
          requestConfig.headers.Authorization = `Bearer ${keycloak.token}`
          useAuthStore.setState({ token: keycloak.token })
          return api(requestConfig)
        }
      } catch {
        logoutKeycloak()
        return Promise.reject(error)
      }
    }

    if (status === 401) {
      console.warn('Token inválido ou expirado. Fazendo logout e redirecionando...')
      useAuthStore.getState().logout()
      if (keycloakEnabled) {
        logoutKeycloak()
      } else {
        setTimeout(() => {
          window.location.href = '/login'
        }, 100)
      }
    }
    return Promise.reject(error)
  }
)

export default api
