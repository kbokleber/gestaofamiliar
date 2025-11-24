import { useState, useEffect } from 'react'
import { Pill, Plus, Edit2, Trash2, X, Save, User, Paperclip, ArrowLeft, Filter, FileSpreadsheet } from 'lucide-react'
import api from '../../lib/api'
import Modal from '../../components/Modal'
import DateInput from '../../components/DateInput'
import DocumentUpload, { Document } from '../../components/DocumentUpload'
import { formatDateBR, toDateInputValue } from '../../utils/dateUtils'
import { exportToExcel } from '../../utils/excelUtils'

interface FamilyMember {
  id: number
  name: string
}

interface Medication {
  id: number
  family_member_id: number
  name: string
  dosage: string
  frequency: string
  start_date: string
  end_date: string | null
  prescribed_by: string
  prescription_number: string
  instructions: string
  side_effects: string
  notes: string
  documents: string | null
  created_at: string
  updated_at: string
}

const FREQUENCY_OPTIONS = [
  { value: 'once', label: '1x ao dia' },
  { value: 'twice', label: '2x ao dia' },
  { value: 'three_times', label: '3x ao dia' },
  { value: 'four_times', label: '4x ao dia' },
  { value: 'every_4h', label: 'A cada 4 horas' },
  { value: 'every_6h', label: 'A cada 6 horas' },
  { value: 'every_8h', label: 'A cada 8 horas' },
  { value: 'every_12h', label: 'A cada 12 horas' },
  { value: 'weekly', label: 'Semanal' },
  { value: 'biweekly', label: 'Quinzenal' },
  { value: 'monthly', label: 'Mensal' },
  { value: 'as_needed', label: 'Conforme necessário' },
]

export default function Medications() {
  const [medications, setMedications] = useState<Medication[]>([])
  const [filteredMedications, setFilteredMedications] = useState<Medication[]>([])
  const [members, setMembers] = useState<FamilyMember[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showActiveOnly, setShowActiveOnly] = useState(true)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [isEditingInline, setIsEditingInline] = useState(false)
  const [editingMedication, setEditingMedication] = useState<Medication | null>(null)
  const [filters, setFilters] = useState({
    member_id: 0,
    start_date: '',
    end_date: ''
  })
  const [formData, setFormData] = useState({
    family_member_id: 0,
    name: '',
    dosage: '',
    frequency: 'once',
    start_date: '',
    end_date: '',
    prescribed_by: '',
    prescription_number: '',
    instructions: '',
    side_effects: '',
    notes: ''
  })
  const [documents, setDocuments] = useState<Document[]>([])

  useEffect(() => {
    fetchMedications()
    fetchMembers()
  }, [showActiveOnly])

  useEffect(() => {
    applyFilters()
  }, [medications, filters])

  const fetchMedications = async () => {
    try {
      setLoading(true)
      const response = await api.get('/healthcare/medications', {
        params: { active_only: showActiveOnly }
      })
      console.log('Medicamentos recebidos:', response.data)
      // Log para verificar se documents está presente
      response.data.forEach((med: Medication) => {
        console.log(`Medicamento ${med.id} (${med.name}): documents = ${med.documents ? 'SIM (' + med.documents.length + ' chars)' : 'NÃO'}`)
      })
      setMedications(response.data)
      setError(null)
    } catch (err: any) {
      console.error('Erro ao buscar medicamentos:', err)
      setError(err.response?.data?.detail || 'Erro ao carregar medicamentos')
    } finally {
      setLoading(false)
    }
  }

  const fetchMembers = async () => {
    try {
      const response = await api.get('/healthcare/members')
      setMembers(response.data)
    } catch (err: any) {
      console.error('Erro ao buscar membros:', err)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!formData.family_member_id || formData.family_member_id === 0) {
      alert('Por favor, selecione um paciente')
      return
    }
    
    if (!formData.start_date) {
      alert('Por favor, preencha a data de início')
      return
    }
    
    try {
      // Preparar dados para envio - usar o mesmo padrão de Appointments
      const dataToSend = {
        ...formData,
        end_date: formData.end_date || null,
        // Serializar documentos como JSON - mesmo padrão de Appointments
        documents: documents.length > 0 ? JSON.stringify(documents) : null
      }
      
      console.log('Salvando medicamento com', documents.length, 'documentos')
      console.log('Array de documentos:', documents)
      console.log('JSON stringificado:', documents.length > 0 ? JSON.stringify(documents).substring(0, 100) + '...' : 'null')
      console.log('Dados a enviar:', { ...dataToSend, documents: dataToSend.documents ? `<${dataToSend.documents.length} caracteres>` : null })
      
      let savedMedication
      if (editingMedication) {
        const response = await api.put(`/healthcare/medications/${editingMedication.id}`, dataToSend)
        savedMedication = response.data
        console.log('Medicamento atualizado - resposta:', savedMedication)
        console.log('Documents na resposta:', savedMedication.documents ? `SIM (${savedMedication.documents.length} chars)` : 'NÃO')
      } else {
        const response = await api.post('/healthcare/medications', dataToSend)
        savedMedication = response.data
        console.log('Medicamento criado - resposta:', savedMedication)
        console.log('Documents na resposta:', savedMedication.documents ? `SIM (${savedMedication.documents.length} chars)` : 'NÃO')
      }
      
      // Atualizar a lista de medicamentos para garantir dados atualizados
      await fetchMedications()
      
      if (isEditingInline) {
        cancelEdit()
      } else {
        closeModal()
      }
    } catch (err: any) {
      console.error('Erro ao salvar:', err)
      console.error('Detalhes do erro:', err.response?.data)
      
      let errorMessage = 'Erro ao salvar medicamento'
      if (err.response?.data?.detail) {
        if (Array.isArray(err.response.data.detail)) {
          errorMessage = err.response.data.detail.map((e: any) => `${e.loc.join('.')}: ${e.msg}`).join('\n')
        } else {
          errorMessage = err.response.data.detail
        }
      }
      
      alert(errorMessage)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Deseja realmente excluir este medicamento?')) return
    try {
      await api.delete(`/healthcare/medications/${id}`)
      fetchMedications()
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Erro ao excluir')
    }
  }

  const startEdit = (medication: Medication) => {
    setEditingMedication(medication)
    setFormData({
      family_member_id: medication.family_member_id,
      name: medication.name,
      dosage: medication.dosage,
      frequency: medication.frequency,
      start_date: toDateInputValue(medication.start_date),
      end_date: toDateInputValue(medication.end_date),
      prescribed_by: medication.prescribed_by || '',
      prescription_number: medication.prescription_number || '',
      instructions: medication.instructions || '',
      side_effects: medication.side_effects || '',
      notes: medication.notes || ''
    })
    // Carregar documentos
    console.log('Editando medicamento - documents:', medication.documents)
    if (medication.documents) {
      try {
        const parsedDocs = JSON.parse(medication.documents)
        console.log('Documentos parseados:', parsedDocs)
        console.log('Quantidade de documentos:', parsedDocs.length)
        setDocuments(Array.isArray(parsedDocs) ? parsedDocs : [])
      } catch (e) {
        console.error('Erro ao parsear documentos:', e)
        console.error('Conteúdo do documents:', medication.documents)
        setDocuments([])
      }
    } else {
      console.log('Medicamento sem documentos')
      setDocuments([])
    }
    setIsEditingInline(true)
  }

  const cancelEdit = () => {
    setIsEditingInline(false)
    setEditingMedication(null)
    setFormData({
      family_member_id: members.length > 0 ? members[0].id : 0,
      name: '',
      dosage: '',
      frequency: 'once',
      start_date: '',
      end_date: '',
      prescribed_by: '',
      prescription_number: '',
      instructions: '',
      side_effects: '',
      notes: ''
    })
    setDocuments([])
  }

  const openModal = () => {
    setEditingMedication(null)
    setFormData({
      family_member_id: members.length > 0 ? members[0].id : 0,
      name: '',
      dosage: '',
      frequency: 'once',
      start_date: '',
      end_date: '',
      prescribed_by: '',
      prescription_number: '',
      instructions: '',
      side_effects: '',
      notes: ''
    })
    setDocuments([])
    setIsModalOpen(true)
  }

  const closeModal = () => {
    setIsModalOpen(false)
    setEditingMedication(null)
    setDocuments([])
  }

  const isActive = (medication: Medication) => {
    const today = new Date()
    const startDate = new Date(medication.start_date)
    const endDate = medication.end_date ? new Date(medication.end_date) : null
    
    return startDate <= today && (!endDate || endDate >= today)
  }

  const getMemberName = (memberId: number) => {
    const member = members.find(m => m.id === memberId)
    return member ? member.name : 'Desconhecido'
  }

  const applyFilters = () => {
    let filtered = [...medications]

    // Filtro por membro
    if (filters.member_id > 0) {
      filtered = filtered.filter(medication => medication.family_member_id === filters.member_id)
    }

    // Filtro por data inicial
    if (filters.start_date) {
      const startDate = new Date(filters.start_date)
      startDate.setHours(0, 0, 0, 0)
      filtered = filtered.filter(medication => {
        const medicationDate = new Date(medication.start_date)
        medicationDate.setHours(0, 0, 0, 0)
        return medicationDate >= startDate
      })
    }

    // Filtro por data final
    if (filters.end_date) {
      const endDate = new Date(filters.end_date)
      endDate.setHours(23, 59, 59, 999)
      filtered = filtered.filter(medication => {
        const medicationDate = new Date(medication.start_date)
        return medicationDate <= endDate
      })
    }

    setFilteredMedications(filtered)
  }

  const handleFilter = () => {
    applyFilters()
  }

  const handleExportExcel = () => {
    const dataToExport = filteredMedications.map(medication => ({
      paciente: getMemberName(medication.family_member_id),
      medicamento: medication.name || '-',
      dosagem: medication.dosage || '-',
      frequencia: getFrequencyLabel(medication.frequency),
      periodo: `${formatDateBR(medication.start_date)}${medication.end_date ? ` até ${formatDateBR(medication.end_date)}` : ' (Contínuo)'}`,
      prescritoPor: medication.prescribed_by || '-',
      numeroReceita: medication.prescription_number || '-',
      instrucoes: medication.instructions || '-',
      efeitosColaterais: medication.side_effects || '-',
      observacoes: medication.notes || '-',
      status: isActive(medication) ? 'Ativo' : 'Inativo'
    }))

    exportToExcel(
      dataToExport,
      [
        { header: 'Paciente', key: 'paciente', width: 20 },
        { header: 'Medicamento', key: 'medicamento', width: 25 },
        { header: 'Dosagem', key: 'dosagem', width: 15 },
        { header: 'Frequência', key: 'frequencia', width: 15 },
        { header: 'Período', key: 'periodo', width: 25 },
        { header: 'Prescrito por', key: 'prescritoPor', width: 20 },
        { header: 'Número da Receita', key: 'numeroReceita', width: 15 },
        { header: 'Instruções', key: 'instrucoes', width: 30 },
        { header: 'Efeitos Colaterais', key: 'efeitosColaterais', width: 30 },
        { header: 'Observações', key: 'observacoes', width: 30 },
        { header: 'Status', key: 'status', width: 10 }
      ],
      `Medicamentos_${new Date().toISOString().split('T')[0]}`
    )
  }

  const getFrequencyLabel = (frequency: string) => {
    const option = FREQUENCY_OPTIONS.find(opt => opt.value === frequency)
    return option ? option.label : frequency
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-600">Carregando...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-600">Erro: {error}</p>
        <button 
          onClick={fetchMedications}
          className="mt-2 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700"
        >
          Tentar novamente
        </button>
      </div>
    )
  }

  return (
    <div>
      {!isEditingInline ? (
        <>
          {/* Cabeçalho */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-6 gap-4">
            <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 flex items-center">
              <Pill className="mr-2 sm:mr-3 h-6 w-6 sm:h-8 sm:w-8 text-red-600" />
              Medicamentos
            </h1>
            <div className="flex gap-2 w-full sm:w-auto">
              <button 
                onClick={handleExportExcel}
                className="flex-1 sm:flex-none px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors flex items-center justify-center"
              >
                <FileSpreadsheet className="mr-2 h-5 w-5" />
                Exportar Excel
              </button>
              <button 
                onClick={() => openModal()}
                className="flex-1 sm:flex-none px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors flex items-center justify-center"
              >
                <Plus className="mr-2 h-5 w-5" />
                Novo Medicamento
              </button>
            </div>
          </div>

          {/* Filtros */}
          <div className="bg-white shadow rounded-lg p-4 mb-6">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Paciente</label>
                <select
                  value={filters.member_id}
                  onChange={(e) => setFilters({...filters, member_id: parseInt(e.target.value)})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500"
                >
                  <option value={0}>Todos os Pacientes</option>
                  {members.map(member => (
                    <option key={member.id} value={member.id}>{member.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Data Inicial</label>
                <DateInput
                  value={filters.start_date}
                  onChange={(value) => setFilters({...filters, start_date: value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Data Final</label>
                <DateInput
                  value={filters.end_date}
                  onChange={(value) => setFilters({...filters, end_date: value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500"
                />
              </div>
              <div className="flex items-end gap-2">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={showActiveOnly}
                    onChange={(e) => setShowActiveOnly(e.target.checked)}
                    className="mr-2 rounded"
                  />
                  <span className="text-sm text-gray-700">Apenas ativos</span>
                </label>
                <button
                  onClick={handleFilter}
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors flex items-center justify-center"
                >
                  <Filter className="mr-2 h-5 w-5" />
                  Filtrar
                </button>
              </div>
            </div>
          </div>

          {filteredMedications.length === 0 ? (
        <div className="bg-white shadow rounded-lg p-6">
          <p className="text-gray-600 text-center py-8">
            Nenhum medicamento encontrado com os filtros aplicados.
          </p>
        </div>
      ) : (
        <>
          {/* Visualização em Cards para Mobile/Tablet */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:hidden gap-4">
            {filteredMedications.map((medication) => (
              <div key={medication.id} className="bg-white shadow rounded-lg p-4 space-y-3">
                {/* Cabeçalho do Card */}
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="text-lg font-semibold text-gray-900">{medication.name}</h3>
                      {medication.documents && (
                        <Paperclip className="h-4 w-4 text-blue-500" aria-label="Possui documentos anexados" />
                      )}
                    </div>
                    <div className="flex items-center text-sm text-gray-500 mt-1">
                      <User className="h-4 w-4 mr-1" />
                      {getMemberName(medication.family_member_id)}
                    </div>
                  </div>
                  <div>
                    {isActive(medication) ? (
                      <span className="px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">
                        Ativo
                      </span>
                    ) : (
                      <span className="px-2 py-1 text-xs font-semibold rounded-full bg-gray-100 text-gray-800">
                        Inativo
                      </span>
                    )}
                  </div>
                </div>

                {/* Informações do Card */}
                <div className="space-y-2 text-sm">
                  <div>
                    <span className="font-medium text-gray-700">Dosagem:</span>
                    <span className="ml-2 text-gray-900">{medication.dosage}</span>
                  </div>
                  <div>
                    <span className="font-medium text-gray-700">Frequência:</span>
                    <span className="ml-2 text-gray-900">{getFrequencyLabel(medication.frequency)}</span>
                  </div>
                  <div>
                    <span className="font-medium text-gray-700">Período:</span>
                    <span className="ml-2 text-gray-900">
                      {formatDateBR(medication.start_date)}
                      {medication.end_date && (
                        <> até {formatDateBR(medication.end_date)}</>
                      )}
                      {!medication.end_date && (
                        <span className="text-green-600"> (Contínuo)</span>
                      )}
                    </span>
                  </div>
                  {medication.prescribed_by && (
                    <div>
                      <span className="font-medium text-gray-700">Prescrito por:</span>
                      <span className="ml-2 text-gray-900">{medication.prescribed_by}</span>
                    </div>
                  )}
                </div>

                {/* Ações do Card */}
                <div className="flex gap-2 pt-3 border-t border-gray-200">
                  <button 
                    onClick={() => startEdit(medication)}
                    className="flex-1 flex items-center justify-center px-3 py-2 bg-red-600 text-white text-sm rounded-md hover:bg-red-700"
                  >
                    <Edit2 className="h-4 w-4 mr-1" />
                    Editar
                  </button>
                  <button 
                    onClick={() => handleDelete(medication.id)}
                    className="flex items-center justify-center px-3 py-2 border border-red-600 text-red-600 text-sm rounded-md hover:bg-red-50"
                  >
                    <Trash2 className="h-4 w-4 mr-1" />
                    Excluir
                  </button>
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
                  Paciente
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Medicamento
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Dosagem
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Frequência
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Período
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Ações
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredMedications.map((medication) => (
                <tr key={medication.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <User className="h-5 w-5 text-gray-400 mr-2" />
                      <div className="text-sm font-medium text-gray-900">
                        {getMemberName(medication.family_member_id)}
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <div className="text-sm font-medium text-gray-900">{medication.name}</div>
                      {medication.documents && (
                        <Paperclip className="h-4 w-4 text-blue-500" aria-label="Possui documentos anexados" />
                      )}
                    </div>
                    {medication.prescribed_by && (
                      <div className="text-xs text-gray-500">Por: {medication.prescribed_by}</div>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">{medication.dosage}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-600">{getFrequencyLabel(medication.frequency)}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-600">
                      {formatDateBR(medication.start_date)}
                      {medication.end_date && (
                        <> até {formatDateBR(medication.end_date)}</>
                      )}
                      {!medication.end_date && (
                        <span className="text-green-600"> (Contínuo)</span>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {isActive(medication) ? (
                      <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                        Ativo
                      </span>
                    ) : (
                      <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-gray-100 text-gray-800">
                        Inativo
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <button 
                      onClick={() => startEdit(medication)}
                      className="text-red-600 hover:text-red-900 mr-3"
                      title="Editar"
                    >
                      <Edit2 className="h-5 w-5" />
                    </button>
                    <button 
                      onClick={() => handleDelete(medication.id)}
                      className="text-red-600 hover:text-red-900"
                      title="Excluir"
                    >
                      <Trash2 className="h-5 w-5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        </>
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
              Editar Medicamento
            </h2>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4 md:space-y-6">
            {/* Paciente */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Paciente *</label>
              <select
                value={formData.family_member_id}
                onChange={(e) => setFormData({...formData, family_member_id: parseInt(e.target.value)})}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500"
                required
              >
                <option value={0}>Selecione o paciente...</option>
                {members.map(member => (
                  <option key={member.id} value={member.id}>{member.name}</option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Nome do Medicamento */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nome do Medicamento *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({...formData, name: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500"
                  placeholder="Ex: Dipirona, Paracetamol"
                  required
                />
              </div>

              {/* Dosagem */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Dosagem *</label>
                <input
                  type="text"
                  value={formData.dosage}
                  onChange={(e) => setFormData({...formData, dosage: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500"
                  placeholder="Ex: 500mg, 10ml, 1 comprimido"
                  required
                />
              </div>
            </div>

            {/* Frequência */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Frequência *</label>
              <select
                value={formData.frequency}
                onChange={(e) => setFormData({...formData, frequency: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500"
                required
              >
                {FREQUENCY_OPTIONS.map(option => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Data de Início */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Data de Início *</label>
                <DateInput
                  value={formData.start_date}
                  onChange={(value) => setFormData({...formData, start_date: value})}
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500"
                />
              </div>

              {/* Data de Término */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Data de Término</label>
                <DateInput
                  value={formData.end_date}
                  onChange={(value) => setFormData({...formData, end_date: value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500"
                  placeholder="Deixe vazio para contínuo"
                />
                <p className="mt-1 text-xs text-gray-500">Deixe vazio se o uso for contínuo</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Prescrito Por */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Prescrito Por</label>
                <input
                  type="text"
                  value={formData.prescribed_by}
                  onChange={(e) => setFormData({...formData, prescribed_by: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500"
                  placeholder="Nome do médico"
                />
              </div>

              {/* Número da Receita */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Número da Receita</label>
                <input
                  type="text"
                  value={formData.prescription_number}
                  onChange={(e) => setFormData({...formData, prescription_number: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500"
                  placeholder="Número da receita médica"
                />
              </div>
            </div>

            {/* Instruções */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Instruções de Uso</label>
              <textarea
                value={formData.instructions}
                onChange={(e) => setFormData({...formData, instructions: e.target.value})}
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500"
                placeholder="Ex: Tomar após as refeições, com água..."
              />
            </div>

            {/* Efeitos Colaterais */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Efeitos Colaterais</label>
              <textarea
                value={formData.side_effects}
                onChange={(e) => setFormData({...formData, side_effects: e.target.value})}
                rows={2}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500"
                placeholder="Possíveis efeitos colaterais..."
              />
            </div>

            {/* Observações */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Observações</label>
              <textarea
                value={formData.notes}
                onChange={(e) => setFormData({...formData, notes: e.target.value})}
                rows={2}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500"
                placeholder="Informações adicionais..."
              />
            </div>

            {/* Upload de Documentos */}
            <div>
              <DocumentUpload
                documents={documents}
                onChange={setDocuments}
                maxFiles={10}
                maxSizeMB={10}
              />
            </div>

            <div className="flex flex-col sm:flex-row justify-end gap-2 sm:gap-3 pt-4 border-t border-gray-200">
              <button
                type="button"
                onClick={cancelEdit}
                className="w-full sm:w-auto px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                type="submit"
                className="w-full sm:w-auto px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 flex items-center justify-center"
              >
                <Save className="mr-2 h-5 w-5" />
                Salvar Alterações
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Modal de Criar */}
      <Modal isOpen={isModalOpen} onClose={closeModal} title="Novo Medicamento">
        <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] flex flex-col">
          <div className="sticky top-0 bg-white border-b border-gray-200 px-4 md:px-6 py-4 flex items-center justify-between z-10">
            <h3 className="text-lg md:text-xl font-semibold text-gray-900">
              Novo Medicamento
            </h3>
            <button onClick={closeModal} className="text-gray-400 hover:text-gray-600">
              <X className="h-5 w-5 md:h-6 md:w-6" />
            </button>
          </div>

          <form onSubmit={handleSubmit} className="p-4 md:p-6 space-y-4 md:space-y-6 overflow-y-auto flex-1">
            {/* Paciente */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Paciente *</label>
              <select
                value={formData.family_member_id}
                onChange={(e) => setFormData({...formData, family_member_id: parseInt(e.target.value)})}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500"
                required
              >
                <option value={0}>Selecione o paciente...</option>
                {members.map(member => (
                  <option key={member.id} value={member.id}>{member.name}</option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Nome do Medicamento */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nome do Medicamento *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({...formData, name: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500"
                  placeholder="Ex: Dipirona, Paracetamol"
                  required
                />
              </div>

              {/* Dosagem */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Dosagem *</label>
                <input
                  type="text"
                  value={formData.dosage}
                  onChange={(e) => setFormData({...formData, dosage: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500"
                  placeholder="Ex: 500mg, 10ml, 1 comprimido"
                  required
                />
              </div>
            </div>

            {/* Frequência */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Frequência *</label>
              <select
                value={formData.frequency}
                onChange={(e) => setFormData({...formData, frequency: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500"
                required
              >
                {FREQUENCY_OPTIONS.map(option => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Data de Início */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Data de Início *</label>
                <DateInput
                  value={formData.start_date}
                  onChange={(value) => setFormData({...formData, start_date: value})}
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500"
                />
              </div>

              {/* Data de Término */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Data de Término</label>
                <DateInput
                  value={formData.end_date}
                  onChange={(value) => setFormData({...formData, end_date: value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500"
                  placeholder="Deixe vazio para contínuo"
                />
                <p className="mt-1 text-xs text-gray-500">Deixe vazio se o uso for contínuo</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Prescrito Por */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Prescrito Por</label>
                <input
                  type="text"
                  value={formData.prescribed_by}
                  onChange={(e) => setFormData({...formData, prescribed_by: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500"
                  placeholder="Nome do médico"
                />
              </div>

              {/* Número da Receita */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Número da Receita</label>
                <input
                  type="text"
                  value={formData.prescription_number}
                  onChange={(e) => setFormData({...formData, prescription_number: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500"
                  placeholder="Número da receita médica"
                />
              </div>
            </div>

            {/* Instruções */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Instruções de Uso</label>
              <textarea
                value={formData.instructions}
                onChange={(e) => setFormData({...formData, instructions: e.target.value})}
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500"
                placeholder="Ex: Tomar após as refeições, com água..."
              />
            </div>

            {/* Efeitos Colaterais */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Efeitos Colaterais</label>
              <textarea
                value={formData.side_effects}
                onChange={(e) => setFormData({...formData, side_effects: e.target.value})}
                rows={2}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500"
                placeholder="Possíveis efeitos colaterais..."
              />
            </div>

            {/* Observações */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Observações</label>
              <textarea
                value={formData.notes}
                onChange={(e) => setFormData({...formData, notes: e.target.value})}
                rows={2}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500"
                placeholder="Informações adicionais..."
              />
            </div>

            {/* Upload de Documentos */}
            <div>
              <DocumentUpload
                documents={documents}
                onChange={setDocuments}
                maxFiles={10}
                maxSizeMB={10}
              />
            </div>

            <div className="sticky bottom-0 bg-white border-t border-gray-200 pt-4 pb-2 flex flex-col sm:flex-row justify-end gap-2 sm:gap-3 mt-6">
              <button
                type="button"
                onClick={closeModal}
                className="w-full sm:w-auto px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                type="submit"
                className="w-full sm:w-auto px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 flex items-center justify-center"
              >
                <Save className="mr-2 h-5 w-5" />
                Criar Medicamento
              </button>
            </div>
          </form>
        </div>
      </Modal>
    </div>
  )
}
