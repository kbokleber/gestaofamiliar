import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App.tsx'
import ErrorBoundary from './components/ErrorBoundary'
import { rememberBlockedMessage } from './pages/AcessoNegado'
import { initKeycloak, keycloak, keycloakEnabled } from './lib/keycloak'
import { authService } from './services/authService'
import { useAuthStore } from './stores/authStore'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      refetchOnWindowFocus: false,
    },
  },
})

function renderApp() {
  ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <ErrorBoundary>
        <QueryClientProvider client={queryClient}>
          <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
            <App />
          </BrowserRouter>
        </QueryClientProvider>
      </ErrorBoundary>
    </React.StrictMode>,
  )
}

async function prepareKeycloakSession() {
  if (!keycloakEnabled || !keycloak) {
    return
  }
  const client = keycloak
  const authenticated = await initKeycloak()
  if (!authenticated || !client.token) {
    return
  }

  useAuthStore.setState({ token: client.token, isAuthenticated: true })
  try {
    const user = await authService.getMe()
    useAuthStore.getState().setAuth(user, client.token)
  } catch (error: unknown) {
    const response = (error as { response?: { status?: number; data?: { detail?: unknown } } }).response
    const detail = response?.data?.detail
    const message = typeof detail === 'string' ? detail : 'Acesso negado.'
    if (response?.status === 401 || response?.status === 403) {
      rememberBlockedMessage(message)
      useAuthStore.getState().logout()
      if (!window.location.pathname.startsWith('/acesso-negado')) {
        window.history.replaceState({}, '', '/acesso-negado')
      }
    } else {
      throw error
    }
  }

  window.setInterval(() => {
    if (!client.authenticated) {
      return
    }
    client.updateToken(60).then(() => {
      if (!client.token) {
        return
      }
      const current = useAuthStore.getState()
      if (current.user) {
        current.setAuth(current.user, client.token)
      } else {
        useAuthStore.setState({ token: client.token })
      }
    }).catch(() => {
      void client.login()
    })
  }, 20000)
}

prepareKeycloakSession()
  .then(renderApp)
  .catch((error) => {
    console.error(error)
    const root = document.getElementById('root')
    if (root) {
      root.textContent = 'Não foi possível iniciar o login.'
    }
  })

