import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App.tsx'
import ErrorBoundary from './components/ErrorBoundary'
import { rememberBlockedMessage } from './pages/AcessoNegado'
import { CAMINHO_RETORNO_APP, initKeycloak, keycloak, keycloakEnabled } from './lib/keycloak'
import { authService } from './services/authService'
import { useAuthStore } from './stores/authStore'
import { canSeeMenu } from './lib/menus'
import { avisarSessaoAoApp, dentroDoApp } from './lib/appNativo'
import { capturarErro, iniciarMonitoramento } from './lib/monitoramento'
import './index.css'
import { registerSW } from 'virtual:pwa-register'

// Erros para o GlitchTip, sem dados pessoais. Sem DSN na compilação, não faz nada.
iniciarMonitoramento()

if (import.meta.env.DEV && 'serviceWorker' in navigator) {
  navigator.serviceWorker.getRegistrations().then(async (registros) => {
    await Promise.all(
      registros
        .filter((registro) => !registro.active?.scriptURL.endsWith('/push-sw.js'))
        .map((registro) => registro.unregister()),
    )
    await navigator.serviceWorker.register('/push-sw.js', { scope: '/' })
  })
} else {
  registerSW({ immediate: true })
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      refetchOnWindowFocus: false,
    },
  },
})

// Dentro do app Android: avisa quem está logado (o app liga localização para criança ou alertas para adulto).
let ultimaSessao = ''
useAuthStore.subscribe((estado) => {
  const chave = estado.user && estado.token ? `${estado.user.id}` : ''
  if (chave === ultimaSessao) return
  ultimaSessao = chave
  avisarSessaoAoApp(estado.token, estado.user)
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
  // O login no app volta por /app-login; depois de entrar, segue para a página inicial.
  if (window.location.pathname === CAMINHO_RETORNO_APP) {
    window.history.replaceState({}, '', '/')
  }
  try {
    const user = await authService.getMe()
    useAuthStore.getState().setAuth(user, client.token)
    if (user.is_child && canSeeMenu(user, 'estudos')) {
      const path = window.location.pathname
      if (path === '/' || path === '/estudos') {
        window.history.replaceState({}, '', '/estudos/atividades')
      }
    }
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

/** Páginas abertas sem login (ex.: /app, aberta no celular da criança para baixar o app). */
function ehRotaPublica(caminho: string): boolean {
  return caminho === '/app' || caminho === '/app/'
}

const PACOTE_APP = 'br.com.kbosolucoes.gestaofamiliar.crianca'

/**
 * Login pelo Google feito no navegador do celular: o Keycloak devolve para /app-login no navegador,
 * e esta página entrega o resultado (que vem depois do #) de volta ao app. Fora do app, nada de sessão aqui.
 */
function devolverLoginAoApp() {
  const resultado = window.location.hash.slice(1)
  const destino = `intent://${window.location.host}${CAMINHO_RETORNO_APP}?retorno=${encodeURIComponent(resultado)}` +
    `#Intent;scheme=https;package=${PACOTE_APP};end`
  const root = document.getElementById('root')
  if (root) {
    root.innerHTML = ''
    const caixa = document.createElement('div')
    caixa.style.cssText = 'font-family:system-ui,sans-serif;max-width:360px;margin:20vh auto;padding:24px;text-align:center'
    const titulo = document.createElement('p')
    titulo.textContent = 'Login feito. Volte ao app Gestão Familiar.'
    titulo.style.cssText = 'font-size:18px;font-weight:600;color:#111827'
    const botao = document.createElement('a')
    botao.href = destino
    botao.textContent = 'Voltar ao app'
    botao.style.cssText = 'display:inline-block;margin-top:16px;padding:14px 24px;border-radius:12px;background:#7c3aed;color:#fff;text-decoration:none;font-weight:600'
    caixa.append(titulo, botao)
    root.append(caixa)
  }
  window.location.replace(destino)
}

const noRetornoForaDoApp = window.location.pathname === CAMINHO_RETORNO_APP && !dentroDoApp()

// Com o Keycloak em login-required, o redirecionamento acontece antes do React Router;
// por isso a página pública é desenhada direto, sem iniciar a sessão.
const iniciar = noRetornoForaDoApp
  ? new Promise<void>(() => devolverLoginAoApp())
  : ehRotaPublica(window.location.pathname) ? Promise.resolve() : prepareKeycloakSession()

iniciar
  .then(renderApp)
  .catch((error) => {
    console.error(error)
    capturarErro(error)
    const root = document.getElementById('root')
    if (root) {
      root.textContent = 'Não foi possível iniciar o login.'
    }
  })

