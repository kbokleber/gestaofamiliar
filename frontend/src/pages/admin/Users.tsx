import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../lib/api'
import { useAuthStore } from '../../stores/authStore'
import { Users, Lock, UserCheck, UserX, Search, RefreshCw, Plus } from 'lucide-react'
import Modal from '../../components/Modal'
import Button from '../../components/Button'

interface User {
  id: number
  username: string
  email: string
  first_name: string
  last_name: string
  is_active: boolean
  is_staff: boolean
  is_superuser: boolean
  date_joined: string
  last_login: string | null
}

export default function AdminUsers() {
  const { user: currentUser } = useAuthStore()
  const queryClient = useQueryClient()
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedUser, setSelectedUser] = useState<User | null>(null)
  const [showPasswordModal, setShowPasswordModal] = useState(false)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showPermissionsModal, setShowPermissionsModal] = useState(false)
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [passwordError, setPasswordError] = useState('')
  const [newUserData, setNewUserData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    first_name: '',
    last_name: ''
  })
  const [createUserError, setCreateUserError] = useState('')

  // Verificar se é admin
  const isAdmin = currentUser?.is_superuser || currentUser?.is_staff

  // Buscar usuários
  const { data: users = [], isLoading, refetch } = useQuery<User[]>({
    queryKey: ['users'],
    queryFn: async () => {
      const response = await api.get('/users/')
      return response.data
    },
    enabled: !!isAdmin,
  })

  // Filtrar usuários
  const filteredUsers = users.filter(user =>
    user.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
    user.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
    `${user.first_name} ${user.last_name}`.toLowerCase().includes(searchTerm.toLowerCase())
  )

  // Mutação para atualizar senha
  const updatePasswordMutation = useMutation({
    mutationFn: async ({ userId, password }: { userId: number; password: string }) => {
      const response = await api.put(`/users/${userId}/password`, {
        new_password: password
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      setShowPasswordModal(false)
      setNewPassword('')
      setConfirmPassword('')
      setPasswordError('')
      setSelectedUser(null)
      alert('Senha atualizada com sucesso!')
    },
    onError: (error: any) => {
      setPasswordError(error.response?.data?.detail || 'Erro ao atualizar senha')
    }
  })

  // Mutação para ativar/desativar usuário
  const toggleActiveMutation = useMutation({
    mutationFn: async (userId: number) => {
      const response = await api.put(`/users/${userId}/activate`)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
    },
    onError: (error: any) => {
      alert(error.response?.data?.detail || 'Erro ao alterar status do usuário')
    }
  })

  // Mutação para criar usuário
  const createUserMutation = useMutation({
    mutationFn: async (userData: {
      username: string
      email: string
      password: string
      first_name: string
      last_name: string
    }) => {
      const response = await api.post('/users/', userData)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      setShowCreateModal(false)
      setNewUserData({
        username: '',
        email: '',
        password: '',
        confirmPassword: '',
        first_name: '',
        last_name: ''
      })
      setCreateUserError('')
      alert('Usuário criado com sucesso!')
    },
    onError: (error: any) => {
      setCreateUserError(error.response?.data?.detail || 'Erro ao criar usuário')
    }
  })

  // Mutação para atualizar permissões
  const updatePermissionsMutation = useMutation({
    mutationFn: async ({ userId, isStaff, isSuperuser }: { userId: number; isStaff: boolean; isSuperuser: boolean }) => {
      const response = await api.put(`/users/${userId}/permissions`, {
        is_staff: isStaff,
        is_superuser: isSuperuser
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      setShowPermissionsModal(false)
      setSelectedUser(null)
      alert('Permissões atualizadas com sucesso!')
    },
    onError: (error: any) => {
      alert(error.response?.data?.detail || 'Erro ao atualizar permissões')
    }
  })

  const handleOpenPasswordModal = (user: User) => {
    setSelectedUser(user)
    setShowPasswordModal(true)
    setNewPassword('')
    setConfirmPassword('')
    setPasswordError('')
  }

  const handleUpdatePassword = () => {
    if (!newPassword || !confirmPassword) {
      setPasswordError('Preencha ambos os campos de senha')
      return
    }

    if (newPassword.length < 6) {
      setPasswordError('A senha deve ter pelo menos 6 caracteres')
      return
    }

    if (newPassword !== confirmPassword) {
      setPasswordError('As senhas não coincidem')
      return
    }

    if (!selectedUser) return

    updatePasswordMutation.mutate({
      userId: selectedUser.id,
      password: newPassword
    })
  }

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'Nunca'
    const date = new Date(dateString)
    return date.toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
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
          Administração de Usuários
        </h1>
        <p className="text-sm sm:text-base text-gray-600 mt-1">Gerencie usuários e senhas do sistema</p>
      </div>

      {/* Barra de busca */}
      <div className="mb-6">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
          <input
            type="text"
            placeholder="Buscar por nome, usuário ou email..."
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
            setCreateUserError('')
            setNewUserData({
              username: '',
              email: '',
              password: '',
              confirmPassword: '',
              first_name: '',
              last_name: ''
            })
          }}
          className="flex items-center gap-2 w-full sm:w-auto"
        >
          <Plus className="w-4 h-4" />
          Novo Usuário
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

      {/* Lista de usuários */}
      {isLoading ? (
        <div className="text-center py-12">
          <p className="text-gray-500">Carregando usuários...</p>
        </div>
      ) : filteredUsers.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-gray-500">Nenhum usuário encontrado</p>
        </div>
      ) : (
        <>
          {/* Visualização em Cards para Mobile/Tablet */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:hidden gap-4 mb-6">
            {filteredUsers.map((user) => (
              <div key={user.id} className="bg-white shadow rounded-lg p-4 space-y-3">
                {/* Cabeçalho do Card */}
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-gray-900">{user.username}</h3>
                    <div className="text-sm text-gray-500 mt-1">{user.email}</div>
                    {(user.first_name || user.last_name) && (
                      <div className="text-sm text-gray-700 mt-1">
                        {user.first_name} {user.last_name}
                      </div>
                    )}
                  </div>
                  <div className="flex flex-col items-end gap-2">
                    {user.is_active ? (
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                        <UserCheck className="w-3 h-3 mr-1" />
                        Ativo
                      </span>
                    ) : (
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                        <UserX className="w-3 h-3 mr-1" />
                        Inativo
                      </span>
                    )}
                  </div>
                </div>

                {/* Informações do Card */}
                <div className="space-y-2 text-sm">
                  <div>
                    <span className="font-medium text-gray-700">Permissões:</span>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {user.is_superuser && (
                        <span className="inline-block px-2 py-0.5 text-xs font-medium bg-purple-100 text-purple-800 rounded">
                          Admin
                        </span>
                      )}
                      {user.is_staff && (
                        <span className="inline-block px-2 py-0.5 text-xs font-medium bg-blue-100 text-blue-800 rounded">
                          Staff
                        </span>
                      )}
                      {!user.is_superuser && !user.is_staff && (
                        <span className="text-gray-400 text-xs">Nenhuma</span>
                      )}
                    </div>
                  </div>
                  <div>
                    <span className="font-medium text-gray-700">Último Login:</span>
                    <span className="ml-2 text-gray-900">{formatDate(user.last_login)}</span>
                  </div>
                </div>

                {/* Ações do Card */}
                <div className="flex flex-col gap-2 pt-3 border-t border-gray-200">
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleOpenPasswordModal(user)}
                      className="flex-1 flex items-center justify-center px-3 py-2 bg-purple-600 text-white text-sm rounded-md hover:bg-purple-700"
                    >
                      <Lock className="h-4 w-4 mr-1" />
                      Senha
                    </button>
                    {user.id !== currentUser?.id && (
                      <button
                        onClick={() => {
                          if (confirm(`Tem certeza que deseja ${user.is_active ? 'desativar' : 'ativar'} este usuário?`)) {
                            toggleActiveMutation.mutate(user.id)
                          }
                        }}
                        className={`flex-1 flex items-center justify-center px-3 py-2 text-sm rounded-md ${
                          user.is_active
                            ? 'border border-red-600 text-red-600 hover:bg-red-50'
                            : 'border border-green-600 text-green-600 hover:bg-green-50'
                        }`}
                      >
                        {user.is_active ? (
                          <>
                            <UserX className="h-4 w-4 mr-1" />
                            Desativar
                          </>
                        ) : (
                          <>
                            <UserCheck className="h-4 w-4 mr-1" />
                            Ativar
                          </>
                        )}
                      </button>
                    )}
                  </div>
                  {user.id !== currentUser?.id && (
                    <button
                      onClick={() => {
                        setSelectedUser(user)
                        setShowPermissionsModal(true)
                      }}
                      className="w-full flex items-center justify-center px-3 py-2 border border-purple-600 text-purple-600 text-sm rounded-md hover:bg-purple-50"
                    >
                      Editar Permissões
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Visualização em Tabela para Desktop */}
          <div className="hidden lg:block bg-white shadow rounded-lg overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Usuário
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Email
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Nome
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Permissões
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Último Login
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Ações
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredUsers.map((user) => (
                  <tr key={user.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">{user.username}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-500">{user.email}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">
                        {user.first_name} {user.last_name}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {user.is_active ? (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                          <UserCheck className="w-3 h-3 mr-1" />
                          Ativo
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                          <UserX className="w-3 h-3 mr-1" />
                          Inativo
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-500 flex items-center gap-1">
                        {user.is_superuser && (
                          <span className="inline-block mr-1 px-2 py-0.5 text-xs font-medium bg-purple-100 text-purple-800 rounded">
                            Admin
                          </span>
                        )}
                        {user.is_staff && (
                          <span className="inline-block px-2 py-0.5 text-xs font-medium bg-blue-100 text-blue-800 rounded">
                            Staff
                          </span>
                        )}
                        {!user.is_superuser && !user.is_staff && (
                          <span className="text-gray-400">-</span>
                        )}
                        {user.id !== currentUser?.id && (
                          <button
                            onClick={() => {
                              setSelectedUser(user)
                              setShowPermissionsModal(true)
                            }}
                            className="ml-2 text-purple-600 hover:text-purple-900 text-xs"
                            title="Editar permissões"
                          >
                            ✏️
                          </button>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-500">{formatDate(user.last_login)}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleOpenPasswordModal(user)}
                          className="text-purple-600 hover:text-purple-900 flex items-center gap-1"
                          title="Alterar senha"
                        >
                          <Lock className="w-4 h-4" />
                          Senha
                        </button>
                        {user.id !== currentUser?.id && (
                          <button
                            onClick={() => {
                              if (confirm(`Tem certeza que deseja ${user.is_active ? 'desativar' : 'ativar'} este usuário?`)) {
                                toggleActiveMutation.mutate(user.id)
                              }
                            }}
                            className={`${
                              user.is_active
                                ? 'text-red-600 hover:text-red-900'
                                : 'text-green-600 hover:text-green-900'
                            } flex items-center gap-1`}
                            title={user.is_active ? 'Desativar usuário' : 'Ativar usuário'}
                          >
                            {user.is_active ? <UserX className="w-4 h-4" /> : <UserCheck className="w-4 h-4" />}
                            {user.is_active ? 'Desativar' : 'Ativar'}
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
        </>
      )}

      {/* Modal de alteração de senha */}
      <Modal
        isOpen={showPasswordModal}
        onClose={() => {
          setShowPasswordModal(false)
          setNewPassword('')
          setConfirmPassword('')
          setPasswordError('')
          setSelectedUser(null)
        }}
        title={`Alterar Senha - ${selectedUser?.username}`}
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Nova Senha
            </label>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => {
                setNewPassword(e.target.value)
                setPasswordError('')
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              placeholder="Digite a nova senha"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Confirmar Senha
            </label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => {
                setConfirmPassword(e.target.value)
                setPasswordError('')
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              placeholder="Confirme a nova senha"
            />
          </div>

          {passwordError && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3">
              <p className="text-sm text-red-800">{passwordError}</p>
            </div>
          )}

          <div className="flex justify-end gap-2 pt-4">
            <Button
              variant="outline"
              onClick={() => {
                setShowPasswordModal(false)
                setNewPassword('')
                setConfirmPassword('')
                setPasswordError('')
                setSelectedUser(null)
              }}
            >
              Cancelar
            </Button>
            <Button
              onClick={handleUpdatePassword}
              disabled={updatePasswordMutation.isPending}
            >
              {updatePasswordMutation.isPending ? 'Salvando...' : 'Salvar Senha'}
            </Button>
          </div>
        </div>
      </Modal>

      {/* Modal de criação de usuário */}
      <Modal
        isOpen={showCreateModal}
        onClose={() => {
          setShowCreateModal(false)
          setNewUserData({
            username: '',
            email: '',
            password: '',
            confirmPassword: '',
            first_name: '',
            last_name: ''
          })
          setCreateUserError('')
        }}
        title="Criar Novo Usuário"
      >
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Usuário *
              </label>
              <input
                type="text"
                value={newUserData.username}
                onChange={(e) => {
                  setNewUserData({ ...newUserData, username: e.target.value })
                  setCreateUserError('')
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                placeholder="nomeusuario"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Email *
              </label>
              <input
                type="email"
                value={newUserData.email}
                onChange={(e) => {
                  setNewUserData({ ...newUserData, email: e.target.value })
                  setCreateUserError('')
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                placeholder="usuario@email.com"
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Nome
              </label>
              <input
                type="text"
                value={newUserData.first_name}
                onChange={(e) => {
                  setNewUserData({ ...newUserData, first_name: e.target.value })
                  setCreateUserError('')
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                placeholder="Primeiro nome"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Sobrenome
              </label>
              <input
                type="text"
                value={newUserData.last_name}
                onChange={(e) => {
                  setNewUserData({ ...newUserData, last_name: e.target.value })
                  setCreateUserError('')
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                placeholder="Sobrenome"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Senha *
            </label>
            <input
              type="password"
              value={newUserData.password}
              onChange={(e) => {
                setNewUserData({ ...newUserData, password: e.target.value })
                setCreateUserError('')
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              placeholder="Mínimo 6 caracteres"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Confirmar Senha *
            </label>
            <input
              type="password"
              value={newUserData.confirmPassword}
              onChange={(e) => {
                setNewUserData({ ...newUserData, confirmPassword: e.target.value })
                setCreateUserError('')
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              placeholder="Confirme a senha"
              required
            />
          </div>

          {createUserError && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3">
              <p className="text-sm text-red-800">{createUserError}</p>
            </div>
          )}

          <div className="flex justify-end gap-2 pt-4">
            <Button
              variant="outline"
              onClick={() => {
                setShowCreateModal(false)
                setNewUserData({
                  username: '',
                  email: '',
                  password: '',
                  confirmPassword: '',
                  first_name: '',
                  last_name: ''
                })
                setCreateUserError('')
              }}
            >
              Cancelar
            </Button>
            <Button
              onClick={() => {
                if (!newUserData.username || !newUserData.email || !newUserData.password) {
                  setCreateUserError('Preencha todos os campos obrigatórios')
                  return
                }

                if (newUserData.password.length < 6) {
                  setCreateUserError('A senha deve ter pelo menos 6 caracteres')
                  return
                }

                if (newUserData.password !== newUserData.confirmPassword) {
                  setCreateUserError('As senhas não coincidem')
                  return
                }

                createUserMutation.mutate({
                  username: newUserData.username,
                  email: newUserData.email,
                  password: newUserData.password,
                  first_name: newUserData.first_name,
                  last_name: newUserData.last_name
                })
              }}
              disabled={createUserMutation.isPending}
            >
              {createUserMutation.isPending ? 'Criando...' : 'Criar Usuário'}
            </Button>
          </div>
        </div>
      </Modal>

      {/* Modal de edição de permissões */}
      <Modal
        isOpen={showPermissionsModal}
        onClose={() => {
          setShowPermissionsModal(false)
          setSelectedUser(null)
        }}
        title={`Editar Permissões - ${selectedUser?.username}`}
      >
        <div className="space-y-4">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4">
            <p className="text-sm text-blue-800">
              <strong>Admin (Superuser):</strong> Acesso total ao sistema, incluindo administração de usuários.
            </p>
            <p className="text-sm text-blue-800 mt-2">
              <strong>Staff:</strong> Acesso a funcionalidades administrativas básicas.
            </p>
            <p className="text-sm text-blue-800 mt-2">
              <strong>Nota:</strong> Usuários Admin automaticamente têm permissão Staff.
            </p>
          </div>

          <div className="space-y-3">
            <label className="flex items-center space-x-3 cursor-pointer">
              <input
                type="checkbox"
                checked={selectedUser?.is_superuser || false}
                onChange={(e) => {
                  if (selectedUser) {
                    setSelectedUser({
                      ...selectedUser,
                      is_superuser: e.target.checked,
                      // Se marcar Admin, automaticamente marca Staff
                      is_staff: e.target.checked ? true : selectedUser.is_staff
                    })
                  }
                }}
                className="w-5 h-5 text-purple-600 border-gray-300 rounded focus:ring-purple-500"
              />
              <div>
                <span className="text-sm font-medium text-gray-700">Admin (Superuser)</span>
                <p className="text-xs text-gray-500">Acesso total ao sistema</p>
              </div>
            </label>

            <label className="flex items-center space-x-3 cursor-pointer">
              <input
                type="checkbox"
                checked={selectedUser?.is_staff || false}
                onChange={(e) => {
                  if (selectedUser) {
                    setSelectedUser({
                      ...selectedUser,
                      is_staff: e.target.checked
                    })
                  }
                }}
                disabled={selectedUser?.is_superuser || false}
                className="w-5 h-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              />
              <div>
                <span className="text-sm font-medium text-gray-700">Staff</span>
                <p className="text-xs text-gray-500">Acesso administrativo básico</p>
              </div>
            </label>
          </div>

          <div className="flex justify-end gap-2 pt-4">
            <Button
              variant="outline"
              onClick={() => {
                setShowPermissionsModal(false)
                setSelectedUser(null)
              }}
            >
              Cancelar
            </Button>
            <Button
              onClick={() => {
                if (!selectedUser) return
                updatePermissionsMutation.mutate({
                  userId: selectedUser.id,
                  isStaff: selectedUser.is_staff,
                  isSuperuser: selectedUser.is_superuser
                })
              }}
              disabled={updatePermissionsMutation.isPending}
            >
              {updatePermissionsMutation.isPending ? 'Salvando...' : 'Salvar Permissões'}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}

