import { useState, useEffect } from 'react'
import { Users, Plus, Edit2, Trash2, Calendar, User, ArrowLeft } from 'lucide-react'
import api from '../../lib/api'
import { useAuthStore } from '../../stores/authStore'
import Modal from '../../components/Modal'
import DateInput from '../../components/DateInput'
import { formatDateBR, calculateAge, toDateInputValue } from '../../utils/dateUtils'

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
  const [members, setMembers] = useState<FamilyMember[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [isEditingInline, setIsEditingInline] = useState(false)
  const [editingMember, setEditingMember] = useState<FamilyMember | null>(null)
  const [photoPreview, setPhotoPreview] = useState<string | null>(null)
  const [photoFile, setPhotoFile] = useState<File | null>(null)
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

  useEffect(() => {
    fetchMembers()
  }, [])

  const fetchMembers = async () => {
    try {
      setLoading(true)
      setError(null)
      
      // Verificar se há token antes de fazer a requisição
      const token = useAuthStore.getState().token
      if (!token) {
        setError('Você precisa fazer login para acessar esta página')
        // O interceptor vai redirecionar, mas vamos garantir
        setTimeout(() => {
          window.location.href = '/login'
        }, 2000)
        return
      }
      
      const response = await api.get('/healthcare/members')
      setMembers(response.data)
      setError(null)
    } catch (err: any) {
      console.error('Erro ao carregar membros:', err)
      
      // Se for erro 401, o interceptor já vai redirecionar
      if (err.response?.status === 401) {
        setError('Sessão expirada. Redirecionando para login...')
        // O interceptor já faz o logout e redireciona
      } else {
        setError(err.response?.data?.detail || 'Erro ao carregar membros. Verifique sua conexão.')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const dataToSend: any = { ...formData }

      // Se há uma nova foto, converter para base64
      if (photoFile) {
        const reader = new FileReader()
        const base64Promise = new Promise<string>((resolve, reject) => {
          reader.onloadend = () => {
            const base64String = (reader.result as string).split(',')[1]
            resolve(base64String)
          }
          reader.onerror = reject
        })
        reader.readAsDataURL(photoFile)
        dataToSend.photo = await base64Promise
      }

      console.log('Enviando dados:', dataToSend)
      console.log('Campo order:', dataToSend.order, 'Tipo:', typeof dataToSend.order)

      if (editingMember) {
        await api.put(`/healthcare/members/${editingMember.id}`, dataToSend)
      } else {
        await api.post('/healthcare/members', dataToSend)
      }
      fetchMembers()
      if (isEditingInline) {
        cancelEdit()
      } else {
        closeModal()
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

  const openModal = () => {
    setEditingMember(null)
    setPhotoPreview(null)
    setPhotoFile(null)
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
    setIsModalOpen(true)
  }

  const closeModal = () => {
    setIsModalOpen(false)
    setEditingMember(null)
    setPhotoPreview(null)
    setPhotoFile(null)
  }

  const handlePhotoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setPhotoFile(file)
      // Criar preview
      const reader = new FileReader()
      reader.onloadend = () => {
        setPhotoPreview(reader.result as string)
      }
      reader.readAsDataURL(file)
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


  if (loading) {
    return <div className="flex items-center justify-center h-64"><p className="text-gray-600">Carregando...</p></div>
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
      {!isEditingInline ? (
        <>
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-6 sm:mb-8 gap-4">
            <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">Membros da Família</h1>
            <button 
              onClick={() => openModal()} 
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
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {members.map((member) => (
            <div 
              key={member.id}
              className="bg-white rounded-xl shadow-md hover:shadow-lg transition-all overflow-hidden"
            >
              <div className="p-6">
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
          ))}
        </div>
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
                <label className="absolute bottom-0 right-0 bg-blue-600 text-white p-2 rounded-full cursor-pointer hover:bg-blue-700 shadow-lg">
                  <input 
                    type="file" 
                    accept="image/*" 
                    className="hidden" 
                    onChange={handlePhotoChange}
                  />
                  <Edit2 className="h-4 w-4" />
                </label>
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

      <Modal isOpen={isModalOpen} onClose={closeModal} title="Novo Membro da Família">
        <form onSubmit={handleSubmit} className="space-y-4 max-h-[70vh] overflow-y-auto pr-2">
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
              <label className="absolute bottom-0 right-0 bg-blue-600 text-white p-2 rounded-full cursor-pointer hover:bg-blue-700 shadow-lg">
                <input 
                  type="file" 
                  accept="image/*" 
                  className="hidden" 
                  onChange={handlePhotoChange}
                />
                <Edit2 className="h-4 w-4" />
              </label>
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

          <div className="flex flex-col sm:flex-row justify-end gap-2 sm:gap-3 pt-4 border-t border-gray-200 sticky bottom-0 bg-white">
            <button 
              type="button" 
              onClick={closeModal}
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
      </Modal>
    </div>
  )
}
