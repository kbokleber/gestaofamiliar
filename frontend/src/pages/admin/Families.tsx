import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../lib/api'
import { useAuthStore } from '../../stores/authStore'
import { Users, Search, RefreshCw, Plus, Edit, Trash2 } from 'lucide-react'
import Modal from '../../components/Modal'
import Button from '../../components/Button'

interface Family {
  id: number
  name: string
  codigo_unico: string
  created_at: string
  updated_at: string | null
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
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></div>
          <p className="mt-2 text-gray-600">Carregando famílias...</p>
        </div>
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
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">{family.name}</h3>
                    </div>
                  </div>
                  <div className="space-y-2 text-sm">
                    <div>
                      <span className="font-medium text-gray-700">Criada em:</span>
                      <span className="ml-2 text-gray-900">{formatDate(family.created_at)}</span>
                    </div>
                  </div>
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
                    <tr key={family.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">{family.name}</div>
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
        }}
        title={`Editar Família - ${selectedFamily?.name}`}
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
    </div>
  )
}

