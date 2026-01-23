import { useState } from 'react'
import { Users, Plus, Edit2, Trash2, Calendar, User, ArrowLeft, GripVertical, Camera, Image } from 'lucide-react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import api from '../../lib/api'
import { useAuthStore } from '../../stores/authStore'
import DateInput from '../../components/DateInput'
import Loading from '../../components/Loading'
import { formatDateBR, calculateAge, toDateInputValue } from '../../utils/dateUtils'
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent
} from '@dnd-kit/core'
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  rectSortingStrategy
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'

interface FamilyMember {
  id: number
  name: string
  birth_date: string
  gender: string
  relationship_type?: string
  blood_type?: string
  notes?: string
  photo?: string
  order: number
  created_at: string
  updated_at: string
}

export default function FamilyMembers() {
  const queryClient = useQueryClient()
  const [viewMode, setViewMode] = useState<'list' | 'create'>('list')
  const [isEditingInline, setIsEditingInline] = useState(false)
  const [editingMember, setEditingMember] = useState<FamilyMember | null>(null)
  const [photoPreview, setPhotoPreview] = useState<string | null>(null)
  const [photoFile, setPhotoFile] = useState<File | null>(null)
  const [showPhotoMenu, setShowPhotoMenu] = useState(false)
  const [formData, setFormData] = useState({
    name: '',
    birth_date: '',
    gender: 'M',
    relationship_type: '',
    blood_type: '',
    allergies: '',
    chronic_conditions: '',
    emergency_contact: '',
    emergency_phone: '',
    notes: '',
    order: 0
  })

  // Usar React Query para cache automático
  const { data: membersData = [], isLoading: loading, error: queryError, refetch } = useQuery({
    queryKey: ['healthcare-members'],
    queryFn: async () => {
      const token = useAuthStore.getState().token
      if (!token) {
        throw new Error('Você precisa fazer login para acessar esta página')
      }
      const response = await api.get('/healthcare/members')
      // Ordenar membros por order (menor número primeiro)
      return [...response.data].sort((a: FamilyMember, b: FamilyMember) => (a.order || 0) - (b.order || 0))
    }
  })

  const members = membersData
  const error = queryError ? (queryError as Error).message : null

  // Função para invalidar o cache e refetch
  const fetchMembers = () => {
    queryClient.invalidateQueries({ queryKey: ['healthcare-members'] })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const dataToSend: any = { ...formData }

      // Se há uma nova foto, converter para base64 (igual ao DocumentUpload)
      if (photoFile) {
        const base64 = await fileToBase64(photoFile)
        dataToSend.photo = base64
      }

      // Remover order do dataToSend - a ordem será gerenciada pelo drag and drop
      delete dataToSend.order

      // Se for novo membro, definir order como o último + 1
      if (!editingMember) {
        const maxOrder = members.length > 0 ? Math.max(...members.map(m => m.order || 0)) : -1
        dataToSend.order = maxOrder + 1
      }

      if (editingMember) {
        await api.put(`/healthcare/members/${editingMember.id}`, dataToSend)
      } else {
        await api.post('/healthcare/members', dataToSend)
      }
      fetchMembers()
      if (isEditingInline) {
        cancelEdit()
      } else {
        closeCreateView()
      }
    } catch (err: any) {
      console.error('Erro ao salvar:', err)
      alert(err.response?.data?.detail || 'Erro ao salvar')
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Deseja realmente excluir este membro?')) return
    try {
      await api.delete(`/healthcare/members/${id}`)
      fetchMembers()
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Erro ao excluir')
    }
  }

  const startEdit = (member: FamilyMember) => {
    setEditingMember(member)
    setPhotoPreview(getPhotoUrl(member.photo))
    setPhotoFile(null)
    setFormData({
      name: member.name,
      birth_date: toDateInputValue(member.birth_date),
      gender: member.gender || 'M',
      relationship_type: member.relationship_type || '',
      blood_type: member.blood_type || '',
      allergies: (member as any).allergies || '',
      chronic_conditions: (member as any).chronic_conditions || '',
      emergency_contact: (member as any).emergency_contact || '',
      emergency_phone: (member as any).emergency_phone || '',
      notes: member.notes || '',
      order: member.order || 0
    })
    console.log('Editando membro - Parentesco:', member.relationship_type)
    setIsEditingInline(true)
  }

  const cancelEdit = () => {
    setIsEditingInline(false)
    setEditingMember(null)
    setPhotoPreview(null)
    setPhotoFile(null)
    setShowPhotoMenu(false)
    setFormData({
      name: '',
      birth_date: '',
      gender: 'M',
      relationship_type: '',
      blood_type: '',
      allergies: '',
      chronic_conditions: '',
      emergency_contact: '',
      emergency_phone: '',
      notes: '',
      order: 0
    })
  }

  const openCreateView = () => {
    setFormData({
      name: '',
      birth_date: '',
      gender: 'M',
      relationship_type: '',
      blood_type: '',
      allergies: '',
      chronic_conditions: '',
      emergency_contact: '',
      emergency_phone: '',
      notes: '',
      order: 0
    })
    setEditingMember(null)
    setPhotoPreview(null)
    setPhotoFile(null)
    setViewMode('create')
  }

  const closeCreateView = () => {
    setViewMode('list')
    setFormData({
      name: '',
      birth_date: '',
      gender: 'M',
      relationship_type: '',
      blood_type: '',
      allergies: '',
      chronic_conditions: '',
      emergency_contact: '',
      emergency_phone: '',
      notes: '',
      order: 0
    })
    setEditingMember(null)
    setPhotoPreview(null)
    setPhotoFile(null)
  }



  // Função para converter arquivo para base64 (igual ao DocumentUpload)
  const fileToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onloadend = () => {
        const base64String = (reader.result as string).split(',')[1]
        resolve(base64String)
      }
      reader.onerror = reject
      reader.readAsDataURL(file)
    })
  }

  const handlePhotoChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) {
      setShowPhotoMenu(false)
      return
    }

    // Validar tamanho (max 10MB)
    const maxSizeMB = 10
    if (file.size > maxSizeMB * 1024 * 1024) {
      alert(`A foto é maior que ${maxSizeMB}MB`)
      e.target.value = '' // Limpar input
      setShowPhotoMenu(false)
      return
    }

    // Validar tipo (apenas imagens)
    const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif']
    if (!validTypes.includes(file.type)) {
      alert('A foto deve ser JPG, PNG ou GIF')
      e.target.value = '' // Limpar input
      setShowPhotoMenu(false)
      return
    }

    try {
      setPhotoFile(file)
      setShowPhotoMenu(false)
      
      // Criar preview (com prefixo data: para exibição)
      const reader = new FileReader()
      reader.onloadend = () => {
        setPhotoPreview(reader.result as string)
      }
      reader.readAsDataURL(file)
    } catch (error) {
      console.error('Erro ao processar foto:', error)
      alert('Erro ao processar a foto')
      e.target.value = '' // Limpar input
      setShowPhotoMenu(false)
    }
  }

  const triggerCameraInput = (inputId: string) => {
    const input = document.getElementById(inputId) as HTMLInputElement
    if (input) {
      input.click()
    }
  }

  const getRelationshipLabel = (relationship?: string) => {
    if (!relationship) return null
    const relationships: Record<string, string> = {
      'pai': 'Pai',
      'mae': 'Mãe',
      'filho': 'Filho',
      'filha': 'Filha',
      'avo': 'Avô',
      'ava': 'Avó',
      'irmao': 'Irmão',
      'irma': 'Irmã',
      'outro': 'Outro'
    }
    return relationships[relationship.toLowerCase()] || relationship
  }

  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase()
      .substring(0, 2)
  }

  const getAvatarColor = (name: string) => {
    const colors = [
      'bg-blue-500',
      'bg-green-500',
      'bg-purple-500',
      'bg-pink-500',
      'bg-indigo-500',
      'bg-red-500',
      'bg-yellow-500',
      'bg-teal-500'
    ]
    const index = name.charCodeAt(0) % colors.length
    return colors[index]
  }

  const getPhotoUrl = (photo?: string | null) => {
    if (!photo) return null
    // Se já tem o prefixo data:, retornar como está
    if (photo.startsWith('data:')) return photo
    // Senão, adicionar o prefixo para base64
    return `data:image/jpeg;base64,${photo}`
  }

  // Configurar sensores para drag and drop
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  )

  // Função para lidar com o fim do arraste
  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event

    if (over && active.id !== over.id) {
      const oldIndex = members.findIndex((m) => m.id === active.id)
      const newIndex = members.findIndex((m) => m.id === over.id)

      // Reordenar localmente (atualiza o cache do React Query)
      const newMembers = arrayMove(members, oldIndex, newIndex)
      queryClient.setQueryData(['healthcare-members'], newMembers)

      // Atualizar ordem no backend
      try {
        const orderData = newMembers.map((member, index) => ({
          id: member.id,
          order: index
        }))
        await api.put('/healthcare/members/reorder', orderData)
      } catch (err: any) {
        console.error('Erro ao atualizar ordem:', err)
        alert('Erro ao salvar a nova ordem. Recarregando...')
        fetchMembers() // Recarregar em caso de erro
      }
    }
  }

  // Componente SortableItem para cada card
  interface SortableItemProps {
    member: FamilyMember
  }

  const SortableItem = ({ member }: SortableItemProps) => {
    const {
      attributes,
      listeners,
      setNodeRef,
      transform,
      transition,
      isDragging,
    } = useSortable({ id: member.id })

    const style = {
      transform: CSS.Transform.toString(transform),
      transition,
      opacity: isDragging ? 0.5 : 1,
    }

    return (
      <div
        ref={setNodeRef}
        style={style}
        className="bg-white rounded-xl shadow-md hover:shadow-lg transition-all overflow-hidden"
      >
        <div className="p-6">
          {/* Handle de arraste */}
          <div
            {...attributes}
            {...listeners}
            className="flex justify-center mb-2 cursor-grab active:cursor-grabbing"
            title="Arraste para reordenar"
          >
            <GripVertical className="h-5 w-5 text-gray-400 hover:text-gray-600" />
          </div>

          {/* Avatar */}
          <div className="flex justify-center mb-4">
            <div className={`w-32 h-32 rounded-full ${getAvatarColor(member.name)} flex items-center justify-center text-white text-3xl font-bold shadow-lg overflow-hidden`}>
              {getPhotoUrl(member.photo) ? (
                <img src={getPhotoUrl(member.photo)!} alt={member.name} className="w-full h-full object-cover" />
              ) : (
                getInitials(member.name)
              )}
            </div>
          </div>

          {/* Nome */}
          <h3 className="text-xl font-semibold text-gray-900 text-center mb-4">
            {member.name}
          </h3>

          {/* Informações */}
          <div className="space-y-3 mb-4">
            <div className="flex items-center text-gray-600">
              <Calendar className="h-4 w-4 mr-2 flex-shrink-0" />
              <span className="text-sm">{formatDateBR(member.birth_date)}</span>
            </div>
            <div className="flex items-center text-gray-600">
              <User className="h-4 w-4 mr-2 flex-shrink-0" />
              <span className="text-sm">{calculateAge(member.birth_date)} anos</span>
            </div>
            {getRelationshipLabel(member.relationship_type) && (
              <div className="flex items-center justify-center">
                <span className="px-3 py-1 bg-blue-100 text-blue-800 text-sm font-medium rounded-full">
                  {getRelationshipLabel(member.relationship_type)}
                </span>
              </div>
            )}
          </div>

          {/* Ações */}
          <div className="flex gap-2 pt-4 border-t border-gray-100">
            <button
              onClick={() => startEdit(member)}
              className="flex-1 flex items-center justify-center px-4 py-2 border border-blue-600 text-blue-600 rounded-lg hover:bg-blue-50 transition-colors"
            >
              <Edit2 className="h-4 w-4 mr-1" />
              Editar
            </button>
            <button
              onClick={() => handleDelete(member.id)}
              className="flex-1 flex items-center justify-center px-4 py-2 border border-red-600 text-red-600 rounded-lg hover:bg-red-50 transition-colors"
            >
              <Trash2 className="h-4 w-4 mr-1" />
              Excluir
            </button>
          </div>
        </div>
      </div>
    )
  }


  if (loading) {
    return <Loading message="Carregando membros da família..." />
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-600">Erro: {error}</p>
        <button onClick={fetchMembers} className="mt-2 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700">
          Tentar novamente
        </button>
      </div>
    )
  }

  return (
    <div>
      {viewMode === 'create' ? (
        // Tela completa de cadastro
        <div className="min-h-screen bg-gray-50">
          <div className="bg-white shadow-sm border-b border-gray-200 sticky top-0 z-10">
            <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
              <div className="flex items-center gap-4">
                <button
                  onClick={closeCreateView}
                  className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                  title="Voltar"
                >
                  <ArrowLeft className="h-5 w-5 text-gray-600" />
                </button>
                <h1 className="text-2xl font-bold text-gray-900">Novo Membro da Família</h1>
              </div>
            </div>
          </div>
          
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow-sm p-6 space-y-6">
              {/* Foto */}
              <div className="flex justify-center mb-4">
                <div className="relative">
                  <div className={`w-32 h-32 rounded-full bg-gray-300 flex items-center justify-center text-white text-3xl font-bold shadow-lg overflow-hidden`}>
                    {photoPreview ? (
                      <img src={photoPreview} alt="Foto" className="w-full h-full object-cover" />
                    ) : (
                      <Users className="h-16 w-16" />
                    )}
                  </div>
                  <div className="absolute bottom-0 right-0">
                    <button
                      type="button"
                      onClick={() => setShowPhotoMenu(!showPhotoMenu)}
                      className="bg-blue-600 text-white p-2 rounded-full cursor-pointer hover:bg-blue-700 shadow-lg z-10"
                      title="Adicionar foto"
                    >
                      <Edit2 className="h-4 w-4" />
                    </button>
                    
                    {showPhotoMenu && (
                      <div className="absolute bottom-12 right-0 bg-white rounded-lg shadow-xl border border-gray-200 py-2 min-w-[180px] z-20">
                        <button
                          type="button"
                          onClick={() => {
                            setShowPhotoMenu(false)
                            triggerCameraInput('photo-camera-create')
                          }}
                          className="w-full px-4 py-3 text-left hover:bg-gray-100 flex items-center space-x-3"
                        >
                          <Camera className="h-5 w-5 text-blue-600" />
                          <span className="text-gray-700">Câmera</span>
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setShowPhotoMenu(false)
                            triggerCameraInput('photo-gallery-create')
                          }}
                          className="w-full px-4 py-3 text-left hover:bg-gray-100 flex items-center space-x-3 border-t border-gray-200"
                        >
                          <Image className="h-5 w-5 text-green-600" />
                          <span className="text-gray-700">Galeria</span>
                        </button>
                      </div>
                    )}
                    
                    <input 
                      id="photo-camera-create"
                      type="file" 
                      accept="image/jpeg,image/jpg,image/png,image/gif" 
                      capture="environment"
                      className="hidden" 
                      onChange={handlePhotoChange}
                    />
                    <input 
                      id="photo-gallery-create"
                      type="file" 
                      accept="image/jpeg,image/jpg,image/png,image/gif" 
                      className="hidden" 
                      onChange={handlePhotoChange}
                    />
                  </div>
                </div>
              </div>

              {/* Grid de 2 colunas */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Nome *</label>
                  <input 
                    type="text" 
                    required 
                    value={formData.name} 
                    onChange={(e) => setFormData({...formData, name: e.target.value})} 
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Data de Nascimento *</label>
                  <DateInput
                    value={formData.birth_date}
                    onChange={(value) => setFormData({...formData, birth_date: value})}
                    required
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Gênero *</label>
                  <select 
                    value={formData.gender} 
                    onChange={(e) => setFormData({...formData, gender: e.target.value})} 
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="M">Masculino</option>
                    <option value="F">Feminino</option>
                    <option value="O">Outro</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Parentesco</label>
                  <select 
                    value={formData.relationship_type || ''} 
                    onChange={(e) => setFormData({...formData, relationship_type: e.target.value})} 
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">Selecione...</option>
                    <option value="Pai">Pai</option>
                    <option value="Mãe">Mãe</option>
                    <option value="Filho">Filho</option>
                    <option value="Filha">Filha</option>
                    <option value="Avô">Avô</option>
                    <option value="Avó">Avó</option>
                    <option value="Irmão">Irmão</option>
                    <option value="Irmã">Irmã</option>
                    <option value="Outro">Outro</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Tipo Sanguíneo</label>
                  <input 
                    type="text" 
                    value={formData.blood_type} 
                    onChange={(e) => setFormData({...formData, blood_type: e.target.value})} 
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500" 
                    placeholder="Ex: A+, O-, AB+"
                  />
                </div>
              </div>

              {/* Campos de texto grandes */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Alergias</label>
                <textarea 
                  value={formData.allergies} 
                  onChange={(e) => setFormData({...formData, allergies: e.target.value})} 
                  rows={2} 
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Descreva as alergias conhecidas..."
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Condições Crônicas</label>
                <textarea 
                  value={formData.chronic_conditions} 
                  onChange={(e) => setFormData({...formData, chronic_conditions: e.target.value})} 
                  rows={2} 
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Descreva condições crônicas..."
                />
              </div>

              {/* Contatos de emergência */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Contato de Emergência</label>
                  <input 
                    type="text" 
                    value={formData.emergency_contact} 
                    onChange={(e) => setFormData({...formData, emergency_contact: e.target.value})} 
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Nome do contato"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Telefone de Emergência</label>
                  <input 
                    type="tel" 
                    value={formData.emergency_phone} 
                    onChange={(e) => setFormData({...formData, emergency_phone: e.target.value})} 
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="(00) 00000-0000"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Observações</label>
                <textarea 
                  value={formData.notes} 
                  onChange={(e) => setFormData({...formData, notes: e.target.value})} 
                  rows={3} 
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Informações adicionais..."
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Ordem de Exibição</label>
                <input 
                  type="number" 
                  value={formData.order} 
                  onChange={(e) => {
                    const value = e.target.value === '' ? 0 : parseInt(e.target.value, 10)
                    setFormData(prev => ({...prev, order: isNaN(value) ? 0 : value}))
                  }} 
                  min="0"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="0"
                />
                <p className="mt-1 text-xs text-gray-500">
                  Define a ordem em que este membro aparece nos cards (menor número aparece primeiro)
                </p>
              </div>

              <div className="flex flex-col sm:flex-row justify-end gap-2 sm:gap-3 pt-4 border-t border-gray-200">
                <button 
                  type="button" 
                  onClick={closeCreateView}
                  className="w-full sm:w-auto px-6 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                >
                  Cancelar
                </button>
                <button 
                  type="submit" 
                  className="w-full sm:w-auto px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 flex items-center justify-center"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Criar Membro
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : !isEditingInline ? (
        // Tela de lista
        <>
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-6 sm:mb-8 gap-4">
            <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">Membros da Família</h1>
            <button 
              onClick={() => openCreateView()} 
              className="w-full sm:w-auto px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center justify-center shadow-sm"
            >
              <Plus className="mr-2 h-5 w-5" />
              Novo Membro
            </button>
          </div>

          {members.length === 0 ? (
            <div className="bg-white shadow rounded-lg p-12 text-center">
              <Users className="mx-auto h-16 w-16 text-gray-400 mb-4" />
              <p className="text-gray-600 text-lg mb-2">Nenhum membro cadastrado</p>
              <p className="text-gray-500 text-sm">Clique em "Novo Membro" para começar.</p>
            </div>
          ) : (
            <DndContext
              sensors={sensors}
              collisionDetection={closestCenter}
              onDragEnd={handleDragEnd}
            >
              <SortableContext
                items={members.map(m => m.id)}
                strategy={rectSortingStrategy}
              >
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                  {members.map((member) => (
                    <SortableItem key={member.id} member={member} />
                  ))}
                </div>
              </SortableContext>
            </DndContext>
          )}
        </>
      ) : (
        /* Formulário de Edição na Tela */
        <div className="bg-white shadow rounded-lg p-4 md:p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl md:text-2xl font-bold text-gray-900 flex items-center">
              <ArrowLeft 
                onClick={cancelEdit}
                className="mr-3 h-6 w-6 cursor-pointer text-gray-600 hover:text-gray-900"
              />
              Editar Membro da Família
            </h2>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Foto */}
            <div className="flex justify-center mb-4">
              <div className="relative">
                <div className={`w-32 h-32 rounded-full ${editingMember ? getAvatarColor(editingMember.name) : 'bg-gray-300'} flex items-center justify-center text-white text-3xl font-bold shadow-lg overflow-hidden`}>
                  {photoPreview ? (
                    <img src={photoPreview} alt="Foto" className="w-full h-full object-cover" />
                  ) : editingMember ? (
                    getInitials(editingMember.name)
                  ) : (
                    <Users className="h-16 w-16" />
                  )}
                </div>
                <div className="absolute bottom-0 right-0">
                  <button
                    type="button"
                    onClick={() => setShowPhotoMenu(!showPhotoMenu)}
                    className="bg-blue-600 text-white p-2 rounded-full cursor-pointer hover:bg-blue-700 shadow-lg z-10"
                    title="Adicionar foto"
                  >
                    <Edit2 className="h-4 w-4" />
                  </button>
                  
                  {showPhotoMenu && (
                    <div className="absolute bottom-12 right-0 bg-white rounded-lg shadow-xl border border-gray-200 py-2 min-w-[180px] z-20">
                      <button
                        type="button"
                        onClick={() => {
                          setShowPhotoMenu(false)
                          triggerCameraInput('photo-camera-edit')
                        }}
                        className="w-full px-4 py-3 text-left hover:bg-gray-100 flex items-center space-x-3"
                      >
                        <Camera className="h-5 w-5 text-blue-600" />
                        <span className="text-gray-700">Câmera</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setShowPhotoMenu(false)
                          triggerCameraInput('photo-gallery-edit')
                        }}
                        className="w-full px-4 py-3 text-left hover:bg-gray-100 flex items-center space-x-3 border-t border-gray-200"
                      >
                        <Image className="h-5 w-5 text-green-600" />
                        <span className="text-gray-700">Galeria</span>
                      </button>
                    </div>
                  )}
                  
                  <input 
                    id="photo-camera-edit"
                    type="file" 
                    accept="image/jpeg,image/jpg,image/png,image/gif" 
                    capture="environment"
                    className="hidden" 
                    onChange={handlePhotoChange}
                  />
                  <input 
                    id="photo-gallery-edit"
                    type="file" 
                    accept="image/jpeg,image/jpg,image/png,image/gif" 
                    className="hidden" 
                    onChange={handlePhotoChange}
                  />
                </div>
              </div>
            </div>

            {/* Grid de 2 colunas */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">Nome *</label>
                <input 
                  type="text" 
                  required 
                  value={formData.name} 
                  onChange={(e) => setFormData({...formData, name: e.target.value})} 
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Data de Nascimento *</label>
                <DateInput
                  value={formData.birth_date}
                  onChange={(value) => setFormData({...formData, birth_date: value})}
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Gênero *</label>
                <select 
                  value={formData.gender} 
                  onChange={(e) => setFormData({...formData, gender: e.target.value})} 
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="M">Masculino</option>
                  <option value="F">Feminino</option>
                  <option value="O">Outro</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Parentesco</label>
                <select 
                  value={formData.relationship_type || ''} 
                  onChange={(e) => setFormData({...formData, relationship_type: e.target.value})} 
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Selecione...</option>
                  <option value="Pai">Pai</option>
                  <option value="Mãe">Mãe</option>
                  <option value="Filho">Filho</option>
                  <option value="Filha">Filha</option>
                  <option value="Avô">Avô</option>
                  <option value="Avó">Avó</option>
                  <option value="Irmão">Irmão</option>
                  <option value="Irmã">Irmã</option>
                  <option value="Outro">Outro</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Tipo Sanguíneo</label>
                <input 
                  type="text" 
                  value={formData.blood_type} 
                  onChange={(e) => setFormData({...formData, blood_type: e.target.value})} 
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500" 
                  placeholder="Ex: A+, O-, AB+"
                />
              </div>
            </div>

            {/* Campos de texto grandes */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Alergias</label>
              <textarea 
                value={formData.allergies} 
                onChange={(e) => setFormData({...formData, allergies: e.target.value})} 
                rows={2} 
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Descreva as alergias conhecidas..."
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Condições Crônicas</label>
              <textarea 
                value={formData.chronic_conditions} 
                onChange={(e) => setFormData({...formData, chronic_conditions: e.target.value})} 
                rows={2} 
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Descreva condições crônicas..."
              />
            </div>

            {/* Contatos de emergência */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Contato de Emergência</label>
                <input 
                  type="text" 
                  value={formData.emergency_contact} 
                  onChange={(e) => setFormData({...formData, emergency_contact: e.target.value})} 
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Nome do contato"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Telefone de Emergência</label>
                <input 
                  type="tel" 
                  value={formData.emergency_phone} 
                  onChange={(e) => setFormData({...formData, emergency_phone: e.target.value})} 
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="(00) 00000-0000"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Observações</label>
              <textarea 
                value={formData.notes} 
                onChange={(e) => setFormData({...formData, notes: e.target.value})} 
                rows={3} 
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Informações adicionais..."
              />
            </div>

            <div className="flex flex-col sm:flex-row justify-end gap-2 sm:gap-3 pt-4 border-t border-gray-200">
              <button 
                type="button" 
                onClick={cancelEdit}
                className="w-full sm:w-auto px-6 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button 
                type="submit" 
                className="w-full sm:w-auto px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 flex items-center justify-center"
              >
                <Plus className="h-4 w-4 mr-2" />
                Salvar Alterações
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}
