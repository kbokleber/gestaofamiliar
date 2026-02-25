import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../lib/api'
import { useAuthStore } from '../../stores/authStore'
import { Users, Search, RefreshCw, Plus, Edit, Trash2, UserPlus, ChevronDown, ChevronUp, Bot, Sparkles, Key, Loader2, CheckCircle } from 'lucide-react'
import Modal from '../../components/Modal'
import Button from '../../components/Button'
import Loading from '../../components/Loading'

interface Family {
  id: number
  name: string
  codigo_unico: string
  created_at: string
  updated_at: string | null
}

interface FamilyUser {
  id: number
  username: string
  email: string
  first_name: string
  last_name: string
  is_active: boolean
  is_staff: boolean
  is_superuser: boolean
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

export default function AdminFamilies() {
  const { user: currentUser } = useAuthStore()
  const queryClient = useQueryClient()
  const [searchTerm, setSearchTerm] = useState('')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [selectedFamily, setSelectedFamily] = useState<Family | null>(null)
  const [familyData, setFamilyData] = useState({
    name: ''
  })
  const [error, setError] = useState('')
  const [expandedFamily, setExpandedFamily] = useState<number | null>(null)
  const [showAddUserModal, setShowAddUserModal] = useState(false)
  const [selectedUserToAdd, setSelectedUserToAdd] = useState<number | null>(null)

  // Telegram e IA (no modal de edição)
  const [botToken, setBotToken] = useState('')
  const [savingBot, setSavingBot] = useState(false)
  const [aiEnabled, setAiEnabled] = useState(true)
  const [aiProvider, setAiProvider] = useState<'openai' | 'azure' | 'none'>('openai')
  const [openaiKey, setOpenaiKey] = useState('')
  const [openaiModel, setOpenaiModel] = useState('gpt-4o-mini')
  const [azureEndpoint, setAzureEndpoint] = useState('')
  const [azureKey, setAzureKey] = useState('')
  const [azureDeployment, setAzureDeployment] = useState('')
  const [savingAi, setSavingAi] = useState(false)
  const [telegramError, setTelegramError] = useState('')
  const [telegramSuccess, setTelegramSuccess] = useState('')
  const [aiSuccess, setAiSuccess] = useState('')

  // Verificar se é admin (apenas superuser)
  const isAdmin = currentUser?.is_superuser

  // Buscar famílias
  const { data: families = [], isLoading, refetch } = useQuery<Family[]>({
    queryKey: ['families'],
    queryFn: async () => {
      const response = await api.get('/families/')
      return response.data
    },
    enabled: !!isAdmin,
  })

  // Filtrar famílias
  const filteredFamilies = families.filter(family =>
    family.name.toLowerCase().includes(searchTerm.toLowerCase())
  )

  // Carregar config Telegram/IA da família ao abrir modal de edição
  const familyIdForConfig = showEditModal && selectedFamily ? selectedFamily.id : null
  const { data: familyBotConfig } = useQuery<FamilyBotConfig>({
    queryKey: ['telegram', 'family', 'bot', familyIdForConfig],
    queryFn: async () => {
      const { data } = await api.get('/telegram/family/bot', { params: { family_id: familyIdForConfig } })
      return data
    },
    enabled: !!familyIdForConfig,
  })
  const { data: familyAIConfig, refetch: refetchFamilyAI } = useQuery<FamilyAIConfig>({
    queryKey: ['telegram', 'family', 'ai', familyIdForConfig],
    queryFn: async () => {
      const { data } = await api.get('/telegram/family/ai', { params: { family_id: familyIdForConfig } })
      return data
    },
    enabled: !!familyIdForConfig,
  })

  const handleSaveFamilyBot = async () => {
    if (!selectedFamily) return
    setSavingBot(true)
    setTelegramError('')
    setTelegramSuccess('')
    try {
      const { data } = await api.put('/telegram/family/bot', { bot_token: botToken }, { params: { family_id: selectedFamily.id } })
      queryClient.invalidateQueries({ queryKey: ['telegram', 'family', 'bot', selectedFamily.id] })
      setBotToken('')
      setTelegramSuccess(data?.bot_username ? `Token salvo. Bot configurado: ${data.bot_username}` : 'Token do bot salvo com sucesso.')
    } catch (err: any) {
      const d = err.response?.data?.detail
      setTelegramError(typeof d === 'string' ? d : Array.isArray(d) ? d.map((x: any) => x.msg || JSON.stringify(x)).join('. ') : 'Erro ao salvar token.')
    } finally {
      setSavingBot(false)
    }
  }

  const handleSaveFamilyAI = async () => {
    if (!selectedFamily) return
    setSavingAi(true)
    setTelegramError('')
    setAiSuccess('')
    try {
      await api.put(
        '/telegram/family/ai',
        {
          enabled: aiEnabled,
          provider: aiProvider,
          openai_api_key: openaiKey || undefined,
          openai_model: openaiModel,
          azure_endpoint: azureEndpoint || undefined,
          azure_api_key: azureKey || undefined,
          azure_deployment: azureDeployment || undefined,
        },
        { params: { family_id: selectedFamily.id } }
      )
      queryClient.invalidateQueries({ queryKey: ['telegram', 'family', 'ai', selectedFamily.id] })
      refetchFamilyAI()
      setAiSuccess('Configuração de IA salva com sucesso.')
    } catch (err: any) {
      const detail = err.response?.data?.detail
      const msg = typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail.map((d: any) => d.msg || JSON.stringify(d)).join('. ')
          : 'Erro ao salvar configuração de IA.'
      setTelegramError(msg)
    } finally {
      setSavingAi(false)
    }
  }

  // Sincronizar formulário de IA quando carregar config da família
  useEffect(() => {
    if (!familyAIConfig) return
    setAiEnabled(familyAIConfig.enabled)
    setAiProvider((familyAIConfig.provider as 'openai' | 'azure' | 'none') || 'openai')
    setOpenaiModel(familyAIConfig.openai_model || 'gpt-4o-mini')
  }, [familyAIConfig])

  // Limpar campos sensíveis e mensagens ao trocar de família
  useEffect(() => {
    if (!selectedFamily) return
    setBotToken('')
    setOpenaiKey('')
    setAzureEndpoint('')
    setAzureKey('')
    setAzureDeployment('')
    setTelegramError('')
    setTelegramSuccess('')
    setAiSuccess('')
  }, [selectedFamily?.id])

  // Mutação para criar família
  const createFamilyMutation = useMutation({
    mutationFn: async (data: { name: string }) => {
      const response = await api.post('/families/', data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['families'] })
      setShowCreateModal(false)
      setFamilyData({ name: '' })
      setError('')
      alert('Família criada com sucesso!')
    },
    onError: (error: any) => {
      setError(error.response?.data?.detail || 'Erro ao criar família')
    }
  })

  // Mutação para atualizar família
  const updateFamilyMutation = useMutation({
    mutationFn: async ({ id, data }: { id: number; data: { name?: string } }) => {
      const response = await api.put(`/families/${id}`, data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['families'] })
      setShowEditModal(false)
      setSelectedFamily(null)
      setFamilyData({ name: '' })
      setError('')
      alert('Família atualizada com sucesso!')
    },
    onError: (error: any) => {
      setError(error.response?.data?.detail || 'Erro ao atualizar família')
    }
  })

  // Mutação para deletar família
  const deleteFamilyMutation = useMutation({
    mutationFn: async (id: number) => {
      const response = await api.delete(`/families/${id}`)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['families'] })
      setShowDeleteModal(false)
      setSelectedFamily(null)
      alert('Família deletada com sucesso!')
    },
    onError: (error: any) => {
      alert(error.response?.data?.detail || 'Erro ao deletar família')
    }
  })

  const handleCreate = () => {
    if (!familyData.name.trim()) {
      setError('Nome da família é obrigatório')
      return
    }
    createFamilyMutation.mutate({
      name: familyData.name
    })
  }

  const handleUpdate = () => {
    if (!selectedFamily) return
    if (!familyData.name.trim()) {
      setError('Nome da família é obrigatório')
      return
    }
    updateFamilyMutation.mutate({
      id: selectedFamily.id,
      data: {
        name: familyData.name
      }
    })
  }

  const handleDelete = () => {
    if (!selectedFamily) return
    deleteFamilyMutation.mutate(selectedFamily.id)
  }

  const toggleFamilyExpansion = (familyId: number) => {
    if (expandedFamily === familyId) {
      setExpandedFamily(null)
    } else {
      setExpandedFamily(familyId)
    }
  }

  // Buscar usuários da família quando expandida ou quando o modal está aberto
  const { data: familyUsers = [] } = useQuery<FamilyUser[]>({
    queryKey: ['family-users', expandedFamily || selectedFamily?.id],
    queryFn: async () => {
      const familyId = expandedFamily || selectedFamily?.id
      if (!familyId) return []
      const response = await api.get(`/families/${familyId}/users`)
      return response.data
    },
    enabled: !!(expandedFamily || selectedFamily?.id) && !!isAdmin,
  })

  // Buscar todos os usuários para o modal de adicionar
  const { data: allUsers = [] } = useQuery<FamilyUser[]>({
    queryKey: ['users'],
    queryFn: async () => {
      const response = await api.get('/users/')
      return response.data
    },
    enabled: !!isAdmin && showAddUserModal,
  })

  // Filtrar usuários que já estão na família
  const availableUsers = allUsers.filter(user => {
    if (!selectedFamily) return false
    // Verificar se o usuário já está na família
    const isInFamily = familyUsers.some(fu => fu.id === user.id)
    return !isInFamily
  })

  // Mutação para adicionar usuário à família
  const addUserToFamilyMutation = useMutation({
    mutationFn: async ({ userId, familyId }: { userId: number; familyId: number }) => {
      // Buscar usuário para verificar se é admin ou staff
      const userResponse = await api.get(`/users/${userId}`)
      const user = userResponse.data
      
      if (user.is_superuser) {
        // Para admins, adicionar à lista de famílias (many-to-many)
        const currentFamilyIds = user.family_ids || []
        if (!currentFamilyIds.includes(familyId)) {
          await api.put(`/users/${userId}/permissions`, {
            is_staff: user.is_staff,
            is_superuser: user.is_superuser,
            family_ids: [...currentFamilyIds, familyId]
          })
        }
      } else {
        // Para staff, definir como família principal
        await api.put(`/users/${userId}/permissions`, {
          is_staff: user.is_staff,
          is_superuser: user.is_superuser,
          family_id: familyId
        })
      }
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['family-users', variables.familyId] })
      queryClient.invalidateQueries({ queryKey: ['users'] })
      setShowAddUserModal(false)
      setSelectedUserToAdd(null)
      alert('Usuário adicionado à família com sucesso!')
    },
    onError: (error: any) => {
      alert(error.response?.data?.detail || 'Erro ao adicionar usuário à família')
    }
  })

  const handleAddUserToFamily = () => {
    if (!selectedUserToAdd || !selectedFamily) return
    addUserToFamilyMutation.mutate({
      userId: selectedUserToAdd,
      familyId: selectedFamily.id
    })
  }

  // Mutação para remover usuário da família
  const removeUserFromFamilyMutation = useMutation({
    mutationFn: async ({ userId, familyId }: { userId: number; familyId: number }) => {
      // Buscar usuário para verificar se é admin ou staff
      const userResponse = await api.get(`/users/${userId}`)
      const user = userResponse.data
      
      if (user.is_superuser) {
        // Para admins, pode estar associado via family_id ou family_ids (many-to-many)
        const currentFamilyIds = user.family_ids || []
        const isInFamilyIds = currentFamilyIds.includes(familyId)
        const isInFamilyId = user.family_id === familyId
        
        // Verificar se o usuário realmente está na família (qualquer uma das formas)
        if (!isInFamilyIds && !isInFamilyId) {
          throw new Error('Usuário não está associado a esta família')
        }
        
        // Se estiver apenas em family_id, precisamos migrar para family_ids primeiro
        let updatedFamilyIds = [...currentFamilyIds]
        
        if (isInFamilyId && !isInFamilyIds) {
          // Está apenas em family_id, adicionar a family_ids para poder remover
          updatedFamilyIds = [...currentFamilyIds, familyId]
        }
        
        // Remover da lista
        updatedFamilyIds = updatedFamilyIds.filter((id: number) => id !== familyId)
        
        await api.put(`/users/${userId}/permissions`, {
          is_staff: user.is_staff,
          is_superuser: user.is_superuser,
          family_ids: updatedFamilyIds  // Pode ser array vazio, o backend vai tratar
        })
      } else {
        // Para staff, remover a família principal (definir como null se for a família atual)
        if (user.family_id !== familyId) {
          throw new Error('Usuário não está associado a esta família')
        }
        
        // Criar payload apenas com os campos necessários
        const payload: any = {
          is_staff: user.is_staff,
          is_superuser: user.is_superuser
        }
        
        // Explicitamente definir family_id como null para remover
        payload.family_id = null
        
        await api.put(`/users/${userId}/permissions`, payload)
      }
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['family-users', variables.familyId] })
      queryClient.invalidateQueries({ queryKey: ['users'] })
      alert('Usuário removido da família com sucesso!')
    },
    onError: (error: any) => {
      console.error('Erro completo ao remover usuário da família:', error)
      console.error('Response:', error.response)
      console.error('Data:', error.response?.data)
      
      let errorMessage = 'Erro ao remover usuário da família'
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail
      } else if (error.message) {
        errorMessage = error.message
      } else if (error.response?.data?.message) {
        errorMessage = error.response.data.message
      }
      
      alert(errorMessage)
    }
  })

  const handleRemoveUserFromFamily = (userId: number, familyId: number) => {
    if (!confirm('Tem certeza que deseja remover este usuário da família?')) return
    removeUserFromFamilyMutation.mutate({ userId, familyId })
  }

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'Nunca'
    try {
      const date = new Date(dateString)
      if (isNaN(date.getTime())) return 'Data inválida'
      // Formato brasileiro: DD/MM/YYYY HH:MM
      return date.toLocaleDateString('pt-BR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        timeZone: 'America/Sao_Paulo'
      })
    } catch (error) {
      return 'Data inválida'
    }
  }

  if (!isAdmin) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">Acesso negado. Apenas administradores podem acessar esta página.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="p-4 sm:p-6">
      <div className="mb-6">
        <h1 className="text-xl sm:text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Users className="w-5 h-5 sm:w-6 sm:h-6" />
          Administração de Famílias
        </h1>
        <p className="text-sm sm:text-base text-gray-600 mt-1">Gerencie as famílias do sistema</p>
      </div>

      {/* Barra de busca */}
      <div className="mb-6">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
          <input
            type="text"
            placeholder="Buscar por nome..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
          />
        </div>
      </div>

      {/* Botões de ação */}
      <div className="mb-4 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
        <Button
          onClick={() => {
            setShowCreateModal(true)
            setError('')
            setFamilyData({ name: '' })
          }}
          className="flex items-center gap-2 w-full sm:w-auto"
        >
          <Plus className="w-4 h-4" />
          Nova Família
        </Button>
        <Button
          onClick={() => refetch()}
          variant="outline"
          className="flex items-center gap-2 w-full sm:w-auto"
        >
          <RefreshCw className="w-4 h-4" />
          Atualizar
        </Button>
      </div>

      {/* Loading */}
      {isLoading && (
        <Loading message="Carregando famílias..." />
      )}

      {/* Lista de famílias */}
      {!isLoading && (
        <>
          {/* Visualização em Cards para Mobile/Tablet */}
          <div className="lg:hidden space-y-4">
            {filteredFamilies.length === 0 ? (
              <div className="bg-white rounded-lg shadow p-6 text-center">
                <p className="text-gray-500">Nenhuma família encontrada</p>
              </div>
            ) : (
              filteredFamilies.map((family) => (
                <div key={family.id} className="bg-white rounded-lg shadow p-4">
                  <div className="flex justify-between items-start mb-3">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => toggleFamilyExpansion(family.id)}
                        className="text-purple-600 hover:text-purple-900"
                      >
                        {expandedFamily === family.id ? (
                          <ChevronUp className="w-4 h-4" />
                        ) : (
                          <ChevronDown className="w-4 h-4" />
                        )}
                      </button>
                      <h3 className="text-lg font-semibold text-gray-900">{family.name}</h3>
                    </div>
                  </div>
                  <div className="space-y-2 text-sm">
                    <div>
                      <span className="font-medium text-gray-700">Criada em:</span>
                      <span className="ml-2 text-gray-900">{formatDate(family.created_at)}</span>
                    </div>
                  </div>
                  
                  {/* Seção expandida com usuários */}
                  {expandedFamily === family.id && (
                    <div className="mt-4 pt-4 border-t border-gray-200">
                      {/* Usuários da Família */}
                      <div>
                        <div className="flex justify-between items-center mb-2">
                          <h4 className="font-semibold text-gray-900 text-sm">Usuários</h4>
                          <button
                            onClick={() => {
                              setSelectedFamily(family)
                              setShowAddUserModal(true)
                            }}
                            className="text-sm text-purple-600 hover:text-purple-900 flex items-center gap-1"
                          >
                            <UserPlus className="w-4 h-4" />
                            Adicionar
                          </button>
                        </div>
                        {familyUsers.length === 0 ? (
                          <p className="text-sm text-gray-500">Nenhum usuário associado</p>
                        ) : (
                          <div className="space-y-1">
                            {familyUsers.map((user) => (
                              <div key={user.id} className="flex items-center justify-between text-sm text-gray-700 group">
                                <div className="flex items-center gap-2">
                                  <span>• {user.first_name || user.last_name ? `${user.first_name} ${user.last_name}`.trim() : user.username} ({user.email})</span>
                                  {user.is_superuser && (
                                    <span className="px-2 py-0.5 text-xs bg-purple-100 text-purple-800 rounded">Admin</span>
                                  )}
                                  {user.is_staff && !user.is_superuser && (
                                    <span className="px-2 py-0.5 text-xs bg-blue-100 text-blue-800 rounded">Staff</span>
                                  )}
                                </div>
                                <button
                                  onClick={() => handleRemoveUserFromFamily(user.id, family.id)}
                                  className="opacity-0 group-hover:opacity-100 transition-opacity text-red-600 hover:text-red-900 p-1"
                                  title="Remover usuário da família"
                                  disabled={removeUserFromFamilyMutation.isPending}
                                >
                                  <Trash2 className="w-4 h-4" />
                                </button>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  <div className="mt-4 flex gap-2">
                    <button
                      onClick={() => {
                        setSelectedFamily(family)
                        setFamilyData({ name: family.name })
                        setShowEditModal(true)
                        setError('')
                      }}
                      className="flex-1 flex items-center justify-center gap-2 px-3 py-2 border border-purple-600 text-purple-600 text-sm rounded-md hover:bg-purple-50"
                    >
                      <Edit className="w-4 h-4" />
                      Editar
                    </button>
                    <button
                      onClick={() => {
                        setSelectedFamily(family)
                        setShowDeleteModal(true)
                      }}
                      className="flex-1 flex items-center justify-center gap-2 px-3 py-2 border border-red-600 text-red-600 text-sm rounded-md hover:bg-red-50"
                    >
                      <Trash2 className="w-4 h-4" />
                      Excluir
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Visualização em Tabela para Desktop */}
          <div className="hidden lg:block bg-white shadow rounded-lg overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Nome
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Criada em
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Ações
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredFamilies.length === 0 ? (
                  <tr>
                    <td colSpan={3} className="px-6 py-4 text-center text-gray-500">
                      Nenhuma família encontrada
                    </td>
                  </tr>
                ) : (
                  filteredFamilies.map((family) => (
                    <>
                      <tr key={family.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => toggleFamilyExpansion(family.id)}
                              className="text-purple-600 hover:text-purple-900"
                            >
                              {expandedFamily === family.id ? (
                                <ChevronUp className="w-4 h-4" />
                              ) : (
                                <ChevronDown className="w-4 h-4" />
                              )}
                            </button>
                            <div className="text-sm font-medium text-gray-900">{family.name}</div>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-500">{formatDate(family.created_at)}</div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => {
                                setSelectedFamily(family)
                                setFamilyData({ name: family.name })
                                setShowEditModal(true)
                                setError('')
                              }}
                              className="text-purple-600 hover:text-purple-900 flex items-center gap-1"
                              title="Editar família"
                            >
                              <Edit className="w-4 h-4" />
                              Editar
                            </button>
                            <button
                              onClick={() => {
                                setSelectedFamily(family)
                                setShowDeleteModal(true)
                              }}
                              className="text-red-600 hover:text-red-900 flex items-center gap-1"
                              title="Excluir família"
                            >
                              <Trash2 className="w-4 h-4" />
                              Excluir
                            </button>
                          </div>
                        </td>
                      </tr>
                      {expandedFamily === family.id && (
                        <tr>
                          <td colSpan={3} className="px-6 py-4 bg-gray-50">
                            {/* Usuários da Família */}
                            <div>
                                <div className="flex justify-between items-center mb-2">
                                  <h4 className="font-semibold text-gray-900 text-sm">Usuários</h4>
                                  <button
                                    onClick={() => {
                                      setSelectedFamily(family)
                                      setShowAddUserModal(true)
                                    }}
                                    className="text-sm text-purple-600 hover:text-purple-900 flex items-center gap-1"
                                  >
                                    <UserPlus className="w-4 h-4" />
                                    Adicionar
                                  </button>
                                </div>
                                {familyUsers.length === 0 ? (
                                  <p className="text-sm text-gray-500">Nenhum usuário associado</p>
                                ) : (
                                  <div className="space-y-1">
                                    {familyUsers.map((user) => (
                                      <div key={user.id} className="flex items-center justify-between text-sm text-gray-700 group">
                                        <div className="flex items-center gap-2">
                                          <span>• {user.first_name || user.last_name ? `${user.first_name} ${user.last_name}`.trim() : user.username} ({user.email})</span>
                                          {user.is_superuser && (
                                            <span className="px-2 py-0.5 text-xs bg-purple-100 text-purple-800 rounded">Admin</span>
                                          )}
                                          {user.is_staff && !user.is_superuser && (
                                            <span className="px-2 py-0.5 text-xs bg-blue-100 text-blue-800 rounded">Staff</span>
                                          )}
                                        </div>
                                        <button
                                          onClick={() => handleRemoveUserFromFamily(user.id, family.id)}
                                          className="opacity-0 group-hover:opacity-100 transition-opacity text-red-600 hover:text-red-900 p-1"
                                          title="Remover usuário da família"
                                          disabled={removeUserFromFamilyMutation.isPending}
                                        >
                                          <Trash2 className="w-4 h-4" />
                                        </button>
                                      </div>
                                    ))}
                                  </div>
                                )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* Modal de criação */}
      <Modal
        isOpen={showCreateModal}
        onClose={() => {
          setShowCreateModal(false)
          setFamilyData({ name: '' })
          setError('')
        }}
        title="Criar Nova Família"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Nome da Família *
            </label>
            <input
              type="text"
              value={familyData.name}
              onChange={(e) => {
                setFamilyData({ ...familyData, name: e.target.value })
                setError('')
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              placeholder="Ex: Família Silva"
            />
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
            <p className="text-sm text-blue-800">
              <strong>Nota:</strong> O código único será gerado automaticamente pelo sistema após a criação da família.
            </p>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3">
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}

          <div className="flex justify-end gap-2 pt-4">
            <Button
              variant="outline"
              onClick={() => {
                setShowCreateModal(false)
                setFamilyData({ name: '' })
                setError('')
              }}
            >
              Cancelar
            </Button>
            <Button
              onClick={handleCreate}
              disabled={createFamilyMutation.isPending}
            >
              {createFamilyMutation.isPending ? 'Criando...' : 'Criar Família'}
            </Button>
          </div>
        </div>
      </Modal>

      {/* Modal de edição */}
      <Modal
        isOpen={showEditModal}
        onClose={() => {
          setShowEditModal(false)
          setSelectedFamily(null)
          setFamilyData({ name: '' })
          setError('')
          setTelegramError('')
          setBotToken('')
        }}
        title={`Editar Família - ${selectedFamily?.name}`}
      >
        <div className="space-y-6 max-h-[80vh] overflow-y-auto">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Nome da Família *
            </label>
            <input
              type="text"
              value={familyData.name}
              onChange={(e) => {
                setFamilyData({ ...familyData, name: e.target.value })
                setError('')
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              placeholder="Ex: Família Silva"
            />
          </div>

          {/* Telegram e IA - só para esta família */}
          <div className="border-t border-gray-200 pt-4">
            <h3 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <Bot className="h-4 w-4 text-purple-500" />
              Bot da família (Telegram)
            </h3>
            <p className="text-xs text-gray-600 mb-2">
              Token do @BotFather. Só precisa fazer uma vez por família.
            </p>
            {familyBotConfig?.configured && (
              <div className="space-y-1 mb-2">
                <div className="flex items-center gap-2 text-green-700 text-sm">
                  <CheckCircle className="h-4 w-4 flex-shrink-0" />
                  <span>Token do bot: <strong>incluído</strong> (oculto por segurança)</span>
                </div>
                {familyBotConfig.bot_username && (
                  <div className="flex items-center gap-2 text-green-700 text-sm pl-6">
                    Bot: {familyBotConfig.bot_username}
                  </div>
                )}
              </div>
            )}
            {!familyBotConfig?.configured && (
              <p className="text-xs text-gray-500 mb-1">O token nunca é exibido após salvar (segurança). Após salvar, aparecerá aqui que foi incluído.</p>
            )}
            <div className="flex flex-wrap gap-2">
              <input
                type="password"
                placeholder={familyBotConfig?.configured ? 'Novo token (só para alterar)' : 'Token do bot (ex: 123456:ABC...)'}
                value={botToken}
                onChange={(e) => setBotToken(e.target.value)}
                className="flex-1 min-w-[180px] px-3 py-2 border border-gray-300 rounded-lg text-sm"
              />
              <Button
                onClick={handleSaveFamilyBot}
                disabled={savingBot || !botToken.trim()}
                className="inline-flex items-center gap-2"
              >
                {savingBot ? <Loader2 className="h-4 w-4 animate-spin" /> : <Key className="h-4 w-4" />}
                Salvar token
              </Button>
            </div>
          </div>

          <div className="border-t border-gray-200 pt-4">
            <h3 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-purple-500" />
              API de IA da família
            </h3>
            <p className="text-xs text-gray-600 mb-3">
              Para o bot responder em linguagem natural (OpenAI ou Azure). Cada família usa sua própria chave.
            </p>
            <div className="space-y-3">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={aiEnabled}
                  onChange={(e) => setAiEnabled(e.target.checked)}
                  className="h-4 w-4 rounded border-gray-300 text-purple-500 focus:ring-purple-500"
                />
                <span className="text-sm font-medium text-gray-700">IA ativada para esta família</span>
              </label>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Provedor</label>
                <select
                  value={aiProvider}
                  onChange={(e) => setAiProvider(e.target.value as 'openai' | 'azure' | 'none')}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                >
                  <option value="openai">OpenAI (GPT)</option>
                  <option value="azure">Azure OpenAI</option>
                  <option value="none">Desligado</option>
                </select>
              </div>
              {aiProvider === 'openai' && (
                <>
                  {familyAIConfig?.has_openai_key && (
                    <div className="flex items-center gap-2 text-green-700 text-sm mb-2">
                      <CheckCircle className="h-4 w-4 flex-shrink-0" />
                      <span>Chave OpenAI/GPT: <strong>já incluída</strong> (oculta por segurança)</span>
                    </div>
                  )}
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">Chave da API OpenAI (GPT)</label>
                    <input
                      type="password"
                      placeholder={familyAIConfig?.has_openai_key ? '•••••••• (deixe em branco para manter)' : 'sk-...'}
                      value={openaiKey}
                      onChange={(e) => setOpenaiKey(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">Modelo</label>
                    <input
                      type="text"
                      value={openaiModel}
                      onChange={(e) => setOpenaiModel(e.target.value)}
                      placeholder="gpt-4o-mini"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                    />
                  </div>
                </>
              )}
              {aiProvider === 'azure' && (
                <>
                  {familyAIConfig?.has_azure_config && (
                    <div className="flex items-center gap-2 text-green-700 text-xs mb-1">
                      <CheckCircle className="h-3.5 w-3.5 flex-shrink-0" />
                      <span>Configuração Azure <strong>incluída</strong> (oculta)</span>
                    </div>
                  )}
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">URL do recurso Azure</label>
                    <input
                      type="url"
                      placeholder="https://seu-recurso.openai.azure.com"
                      value={azureEndpoint}
                      onChange={(e) => setAzureEndpoint(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">Chave da API Azure</label>
                    <input
                      type="password"
                      placeholder={familyAIConfig?.has_azure_config ? '•••••••• (deixe em branco para manter)' : ''}
                      value={azureKey}
                      onChange={(e) => setAzureKey(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">Deployment (ex: gpt-4o)</label>
                    <input
                      type="text"
                      value={azureDeployment}
                      onChange={(e) => setAzureDeployment(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                    />
                  </div>
                </>
              )}
              <Button
                onClick={handleSaveFamilyAI}
                disabled={savingAi}
                className="inline-flex items-center gap-2"
              >
                {savingAi ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                Salvar configuração de IA
              </Button>
            </div>
          </div>

          {telegramSuccess && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-3 flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-green-600 flex-shrink-0" />
              <p className="text-sm text-green-800">{telegramSuccess}</p>
            </div>
          )}
          {aiSuccess && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-3 flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-green-600 flex-shrink-0" />
              <p className="text-sm text-green-800">{aiSuccess}</p>
            </div>
          )}
          {telegramError && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3">
              <p className="text-sm text-red-800">{telegramError}</p>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3">
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}

          <div className="flex justify-end gap-2 pt-4">
            <Button
              variant="outline"
              onClick={() => {
                setShowEditModal(false)
                setSelectedFamily(null)
                setFamilyData({ name: '' })
                setError('')
              }}
            >
              Cancelar
            </Button>
            <Button
              onClick={handleUpdate}
              disabled={updateFamilyMutation.isPending}
            >
              {updateFamilyMutation.isPending ? 'Salvando...' : 'Salvar Alterações'}
            </Button>
          </div>
        </div>
      </Modal>

      {/* Modal de confirmação de exclusão */}
      <Modal
        isOpen={showDeleteModal}
        onClose={() => {
          setShowDeleteModal(false)
          setSelectedFamily(null)
        }}
        title="Confirmar Exclusão"
      >
        <div className="space-y-4">
          <p className="text-gray-700">
            Tem certeza que deseja excluir a família <strong>{selectedFamily?.name}</strong>?
          </p>
          <p className="text-sm text-red-600">
            <strong>Atenção:</strong> Esta ação não pode ser desfeita. A família só pode ser excluída se não houver usuários associados.
          </p>

          <div className="flex justify-end gap-2 pt-4">
            <Button
              variant="outline"
              onClick={() => {
                setShowDeleteModal(false)
                setSelectedFamily(null)
              }}
            >
              Cancelar
            </Button>
            <Button
              variant="danger"
              onClick={handleDelete}
              disabled={deleteFamilyMutation.isPending}
            >
              {deleteFamilyMutation.isPending ? 'Excluindo...' : 'Excluir Família'}
            </Button>
          </div>
        </div>
      </Modal>

      {/* Modal de adicionar usuário à família */}
      <Modal
        isOpen={showAddUserModal}
        onClose={() => {
          setShowAddUserModal(false)
          setSelectedUserToAdd(null)
        }}
        title={`Adicionar Usuário à Família - ${selectedFamily?.name}`}
      >
        <div className="space-y-4">
          <p className="text-gray-700 text-sm">
            Selecione um usuário para adicionar à família <strong>{selectedFamily?.name}</strong>:
          </p>

          {availableUsers.length === 0 ? (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
              <p className="text-sm text-yellow-800">
                Todos os usuários já estão associados a esta família ou não há usuários disponíveis.
              </p>
            </div>
          ) : (
            <div className="max-h-96 overflow-y-auto border border-gray-200 rounded-lg">
              <div className="divide-y divide-gray-200">
                {availableUsers.map((user) => (
                  <button
                    key={user.id}
                    onClick={() => setSelectedUserToAdd(user.id)}
                    className={`w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors ${
                      selectedUserToAdd === user.id ? 'bg-purple-50 border-l-4 border-purple-600' : ''
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-medium text-gray-900">
                          {user.first_name || user.last_name
                            ? `${user.first_name || ''} ${user.last_name || ''}`.trim()
                            : user.username}
                        </div>
                        <div className="text-sm text-gray-500">{user.email}</div>
                      </div>
                      <div className="flex gap-2">
                        {user.is_superuser && (
                          <span className="px-2 py-0.5 text-xs bg-purple-100 text-purple-800 rounded">
                            Admin
                          </span>
                        )}
                        {user.is_staff && !user.is_superuser && (
                          <span className="px-2 py-0.5 text-xs bg-blue-100 text-blue-800 rounded">
                            Staff
                          </span>
                        )}
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3">
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}

          <div className="flex justify-end gap-2 pt-4">
            <Button
              variant="outline"
              onClick={() => {
                setShowAddUserModal(false)
                setSelectedUserToAdd(null)
                setError('')
              }}
            >
              Cancelar
            </Button>
            <Button
              onClick={handleAddUserToFamily}
              disabled={!selectedUserToAdd || addUserToFamilyMutation.isPending}
            >
              {addUserToFamilyMutation.isPending ? 'Adicionando...' : 'Adicionar Usuário'}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}

