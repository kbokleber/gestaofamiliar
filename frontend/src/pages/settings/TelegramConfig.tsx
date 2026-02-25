import { useState, useEffect } from 'react'
import { Send, Bot, Sparkles, Unlink, Loader2, CheckCircle, AlertCircle, Building2 } from 'lucide-react'
import api from '../../lib/api'
import { useAuthStore } from '../../stores/authStore'

interface TelegramStatus {
  linked: boolean
  telegram_username: string | null
  use_ai: boolean
  ai_available: boolean
}

interface LinkCodeResponse {
  code: string
  expires_at: string
  bot_username: string | null
}

interface FamilyBotConfig {
  configured: boolean
  bot_username: string | null
}

interface FamilyAIConfig {
  enabled: boolean
  provider: string
  openai_model: string | null
  has_openai_key: boolean
  has_azure_config: boolean
}

export default function TelegramConfig() {
  const { user: currentUser } = useAuthStore()
  const [status, setStatus] = useState<TelegramStatus | null>(null)
  const [familyBot, setFamilyBot] = useState<FamilyBotConfig | null>(null)
  const [familyAi, setFamilyAi] = useState<FamilyAIConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [linkCode, setLinkCode] = useState<LinkCodeResponse | null>(null)
  const [generatingCode, setGeneratingCode] = useState(false)
  const [updatingAi, setUpdatingAi] = useState(false)
  const [unlinking, setUnlinking] = useState(false)

  const isAdmin = currentUser?.is_superuser

  const fetchStatus = async () => {
    try {
      const [statusRes, botRes, aiRes] = await Promise.all([
        api.get<TelegramStatus>('/telegram/me'),
        api.get<FamilyBotConfig>('/telegram/family/bot').catch(() => ({ data: null })),
        api.get<FamilyAIConfig>('/telegram/family/ai').catch(() => ({ data: null })),
      ])
      setStatus(statusRes.data)
      setFamilyBot(botRes.data ?? null)
      setFamilyAi(aiRes.data ?? null)
      setError('')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erro ao carregar configurações.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStatus()
  }, [])

  const handleGenerateCode = async () => {
    setGeneratingCode(true)
    setError('')
    setLinkCode(null)
    try {
      const { data } = await api.post<LinkCodeResponse>('/telegram/link')
      setLinkCode(data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erro ao gerar código.')
    } finally {
      setGeneratingCode(false)
    }
  }

  const handleToggleAi = async (use_ai: boolean) => {
    if (!status?.linked) return
    setUpdatingAi(true)
    setError('')
    try {
      const { data } = await api.put<TelegramStatus>('/telegram/me', { use_ai })
      setStatus(data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erro ao atualizar preferência.')
    } finally {
      setUpdatingAi(false)
    }
  }

  const handleUnlink = async () => {
    if (!confirm('Desvincular sua conta do Telegram? Você poderá vincular novamente depois.')) return
    setUnlinking(true)
    setError('')
    try {
      await api.delete('/telegram/unlink')
      setLinkCode(null)
      await fetchStatus()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erro ao desvincular.')
    } finally {
      setUnlinking(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-orange-500" />
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Send className="h-7 w-7 text-orange-500" />
          Telegram e IA
        </h1>
        <p className="mt-1 text-sm text-gray-600">
          Vincule sua conta Telegram ao bot da família e escolha se quer usar respostas com IA. O bot e a API de IA são configurados por família.
        </p>
      </div>

      {error && (
        <div className="flex items-center gap-2 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
          <AlertCircle className="h-5 w-5 flex-shrink-0" />
          {error}
        </div>
      )}

      {/* Aviso: config do bot e IA fica em Famílias */}
      <section className="bg-purple-50 border border-purple-200 rounded-xl p-4">
        <h2 className="text-sm font-semibold text-purple-900 flex items-center gap-2 mb-2">
          <Building2 className="h-4 w-4 text-purple-500" />
          Onde configurar o bot e a API de IA
        </h2>
        {isAdmin ? (
          <p className="text-sm text-purple-800">
            Para configurar o token do @BotFather e a API de IA (OpenAI ou Azure) de cada família, acesse <strong>Administração → Famílias</strong> e clique em <strong>Editar</strong> na família desejada. As configurações ficam na própria tela de edição da família.
          </p>
        ) : (
          <p className="text-sm text-purple-800">
            O bot do Telegram e a API de IA da sua família são configurados pelo administrador em <strong>Administração → Famílias</strong>, ao editar a família.
          </p>
        )}
        {familyBot?.configured && familyBot.bot_username && (
          <p className="text-sm text-green-700 mt-2 flex items-center gap-2">
            <CheckCircle className="h-4 w-4" />
            Bot da sua família: {familyBot.bot_username}
          </p>
        )}
      </section>

      {/* Seção: Meu vínculo Telegram */}
      <section className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2 mb-4">
          <Bot className="h-5 w-5 text-orange-500" />
          Minha conta Telegram
        </h2>

        {status?.linked ? (
          <div className="space-y-4">
            <div className="flex items-center gap-2 text-green-700">
              <CheckCircle className="h-5 w-5" />
              <span>
                Vinculado {status.telegram_username ? `como ${status.telegram_username}` : 'ao Telegram'}
              </span>
            </div>
            <p className="text-sm text-gray-600">
              Você já pode enviar mensagens ao bot da família e receber respostas.
            </p>
            <button
              type="button"
              onClick={handleUnlink}
              disabled={unlinking}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 rounded-lg border border-red-200 transition-colors disabled:opacity-50"
            >
              {unlinking ? <Loader2 className="h-4 w-4 animate-spin" /> : <Unlink className="h-4 w-4" />}
              Desvincular
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {!familyBot?.configured ? (
              <p className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-lg p-3">
                Configure o bot da família acima (token do @BotFather) para depois vincular sua conta.
              </p>
            ) : !linkCode ? (
              <>
                <p className="text-sm text-gray-600">
                  Gere um código e envie no Telegram para o bot {familyBot.bot_username || 'da família'}. O código vale por 10 minutos.
                </p>
                <button
                  type="button"
                  onClick={handleGenerateCode}
                  disabled={generatingCode}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 font-medium text-sm transition-colors disabled:opacity-50"
                >
                  {generatingCode ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                  Gerar código
                </button>
              </>
            ) : (
              <>
                <p className="text-sm text-gray-600">
                  No Telegram, abra o bot {linkCode.bot_username || 'da família'} e envie:
                </p>
                <div className="bg-gray-100 rounded-lg p-4 font-mono text-lg tracking-wider text-center">
                  /start {linkCode.code}
                </div>
                <p className="text-xs text-gray-500">
                  Código expira em 10 minutos. Após enviar, aguarde a confirmação no Telegram e atualize esta página.
                </p>
                <button
                  type="button"
                  onClick={handleGenerateCode}
                  disabled={generatingCode}
                  className="text-sm text-orange-600 hover:text-orange-700"
                >
                  Gerar outro código
                </button>
              </>
            )}
          </div>
        )}
      </section>

      {/* Preferência: usar IA nas minhas mensagens */}
      <section className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2 mb-4">
          <Sparkles className="h-5 w-5 text-orange-500" />
          Respostas com IA (minha preferência)
        </h2>

        {status?.linked && status.ai_available ? (
          <div className="space-y-4">
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={status.use_ai}
                onChange={(e) => handleToggleAi(e.target.checked)}
                disabled={updatingAi}
                className="h-4 w-4 rounded border-gray-300 text-orange-500 focus:ring-orange-500"
              />
              <span className="text-sm font-medium text-gray-700">
                Usar IA para entender minhas mensagens no Telegram
              </span>
              {updatingAi && <Loader2 className="h-4 w-4 animate-spin text-gray-400" />}
            </label>
            <p className="text-sm text-gray-500">
              Com a IA ativa, você pode escrever em linguagem natural e o bot responderá com dados da família.
            </p>
          </div>
        ) : status?.linked && !status.ai_available ? (
          <p className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-lg p-3">
            A IA da família ainda não foi configurada. O administrador pode configurá-la em Administração → Famílias → Editar na família.
          </p>
        ) : !status?.linked ? (
          <p className="text-sm text-gray-500">
            Vincule seu Telegram acima para poder ativar ou desativar as respostas com IA para você.
          </p>
        ) : null}
      </section>
    </div>
  )
}
