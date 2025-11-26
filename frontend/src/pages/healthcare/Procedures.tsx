import { useState, useEffect } from 'react'
import { Activity, Plus, Edit2, Trash2, X, Save, User, Paperclip, ArrowLeft, Filter, FileSpreadsheet } from 'lucide-react'
import api from '../../lib/api'
import DateTimeInput from '../../components/DateTimeInput'
import DateInput from '../../components/DateInput'
import DocumentUpload, { Document } from '../../components/DocumentUpload'
import { formatDateTimeBR, toDateTimeInputValue } from '../../utils/dateUtils'
import { exportToExcel } from '../../utils/excelUtils'

interface FamilyMember {
  id: number
  name: string
}

interface Procedure {
  id: number
  family_member_id: number
  procedure_name: string
  procedure_date: string
  doctor_name: string
  location: string
  description: string
  results: string
  follow_up_notes: string
  next_procedure_date: string | null
  documents: string | null
  created_at: string
  updated_at: string
  family_member?: FamilyMember
}

export default function Procedures() {
  const [procedures, setProcedures] = useState<Procedure[]>([])
  const [filteredProcedures, setFilteredProcedures] = useState<Procedure[]>([])
  const [members, setMembers] = useState<FamilyMember[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<'list' | 'create'>('list')
  const [isEditingInline, setIsEditingInline] = useState(false)
  const [editingProcedure, setEditingProcedure] = useState<Procedure | null>(null)
  const [filters, setFilters] = useState({
    member_id: 0,
    start_date: '',
    end_date: ''
  })
  const [formData, setFormData] = useState({
    family_member_id: 0,
    procedure_name: '',
    procedure_date: '',
    doctor_name: '',
    location: '',
    description: '',
    results: '',
    follow_up_notes: '',
    next_procedure_date: ''
  })
  const [documents, setDocuments] = useState<Document[]>([])

  useEffect(() => {
    fetchProcedures()
    fetchMembers()
  }, [])

  useEffect(() => {
    applyFilters()
  }, [procedures, filters])

  const applyFilters = () => {
    let filtered = [...procedures]

    // Filtro por membro
    if (filters.member_id > 0) {
      filtered = filtered.filter(procedure => procedure.family_member_id === filters.member_id)
    }

    // Filtro por data inicial (considera data/hora completa)
    if (filters.start_date) {
      const startDate = new Date(filters.start_date)
      startDate.setHours(0, 0, 0, 0)
      filtered = filtered.filter(procedure => {
        const procedureDate = new Date(procedure.procedure_date)
        // Compara mantendo a hora original do procedure_date
        return procedureDate >= startDate
      })
    }

    // Filtro por data final (considera data/hora completa)
    if (filters.end_date) {
      const endDate = new Date(filters.end_date)
      endDate.setHours(23, 59, 59, 999)
      filtered = filtered.filter(procedure => {
        const procedureDate = new Date(procedure.procedure_date)
        // Compara mantendo a hora original do procedure_date
        return procedureDate <= endDate
      })
    }

    setFilteredProcedures(filtered)
  }

  const handleFilter = () => {
    applyFilters()
  }

  const handleExportExcel = () => {
    const dataToExport = filteredProcedures.map(procedure => ({
      paciente: getMemberName(procedure.family_member_id),
      procedimento: procedure.procedure_name || '-',
      dataHora: formatDateTimeBR(procedure.procedure_date),
      medico: procedure.doctor_name || '-',
      local: procedure.location || '-',
      descricao: procedure.description || '-',
      resultados: procedure.results || '-',
      observacoes: procedure.follow_up_notes || '-',
      proximoProcedimento: procedure.next_procedure_date ? formatDateTimeBR(procedure.next_procedure_date) : '-'
    }))

    exportToExcel(
      dataToExport,
      [
        { header: 'Paciente', key: 'paciente', width: 20 },
        { header: 'Procedimento', key: 'procedimento', width: 30 },
        { header: 'Data/Hora', key: 'dataHora', width: 20 },
        { header: 'Médico', key: 'medico', width: 20 },
        { header: 'Local', key: 'local', width: 20 },
        { header: 'Descrição', key: 'descricao', width: 30 },
        { header: 'Resultados', key: 'resultados', width: 30 },
        { header: 'Observações', key: 'observacoes', width: 30 },
        { header: 'Próximo Procedimento', key: 'proximoProcedimento', width: 20 }
      ],
      `Procedimentos_Medicos_${new Date().toISOString().split('T')[0]}`
    )
  }

  const fetchProcedures = async () => {
    try {
      setLoading(true)
      const response = await api.get('/healthcare/procedures')
      setProcedures(response.data)
      setError(null)
    } catch (err: any) {
      console.error('Erro ao buscar procedimentos:', err)
      setError(err.response?.data?.detail || 'Erro ao carregar procedimentos')
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
    
    // Validar campos obrigatórios
    if (!formData.family_member_id || formData.family_member_id === 0) {
      alert('Por favor, selecione um paciente')
      return
    }
    
    if (!formData.procedure_date) {
      alert('Por favor, preencha a data e hora do procedimento')
      return
    }
    
    if (!formData.procedure_name) {
      alert('Por favor, preencha o nome do procedimento')
      return
    }
    
    try {
      // Preparar dados para envio
      const dataToSend = {
        ...formData,
        next_procedure_date: formData.next_procedure_date || null,
        // Serializar documentos como JSON
        documents: documents.length > 0 ? JSON.stringify(documents) : null
      }
      
      if (editingProcedure) {
        await api.put(`/healthcare/procedures/${editingProcedure.id}`, dataToSend)
      } else {
        await api.post('/healthcare/procedures', dataToSend)
      }
      fetchProcedures()
      if (isEditingInline) {
        cancelEdit()
      } else {
        closeCreateView()
      }
    } catch (err: any) {
      console.error('Erro ao salvar:', err)
      console.error('Detalhes do erro:', err.response?.data)
      
      // Extrair mensagem de erro mais específica
      let errorMessage = 'Erro ao salvar procedimento'
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
    if (!confirm('Deseja realmente excluir este procedimento?')) return
    try {
      await api.delete(`/healthcare/procedures/${id}`)
      fetchProcedures()
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Erro ao excluir')
    }
  }

  const startEdit = (procedure: Procedure) => {
    setEditingProcedure(procedure)
    setFormData({
      family_member_id: procedure.family_member_id,
      procedure_name: procedure.procedure_name,
      procedure_date: toDateTimeInputValue(procedure.procedure_date),
      doctor_name: procedure.doctor_name,
      location: procedure.location,
      description: procedure.description,
      results: procedure.results || '',
      follow_up_notes: procedure.follow_up_notes || '',
      next_procedure_date: toDateTimeInputValue(procedure.next_procedure_date)
    })
    // Carregar documentos
    if (procedure.documents) {
      try {
        setDocuments(JSON.parse(procedure.documents))
      } catch (e) {
        setDocuments([])
      }
    } else {
      setDocuments([])
    }
    setIsEditingInline(true)
  }

  const cancelEdit = () => {
    setIsEditingInline(false)
    setEditingProcedure(null)
    setFormData({
      family_member_id: members.length > 0 ? members[0].id : 0,
      procedure_name: '',
      procedure_date: '',
      doctor_name: '',
      location: '',
      description: '',
      results: '',
      follow_up_notes: '',
      next_procedure_date: ''
    })
    setDocuments([])
  }

  const openCreateView = () => {
    setEditingProcedure(null)
    setFormData({
      family_member_id: members.length > 0 ? members[0].id : 0,
      procedure_name: '',
      procedure_date: '',
      doctor_name: '',
      location: '',
      description: '',
      results: '',
      follow_up_notes: '',
      next_procedure_date: ''
    })
    setDocuments([])
    setViewMode('create')
  }

  const closeCreateView = () => {
    setViewMode('list')
    setEditingProcedure(null)
    setDocuments([])
  }

  const getMemberName = (memberId: number) => {
    const member = members.find(m => m.id === memberId)
    return member ? member.name : 'Desconhecido'
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
          onClick={fetchProcedures}
          className="mt-2 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700"
        >
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
                <h1 className="text-2xl font-bold text-gray-900">Novo Procedimento</h1>
              </div>
            </div>
          </div>
          
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow-sm p-6 space-y-6">
              {/* Paciente */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Paciente *</label>
                <select
                  value={formData.family_member_id}
                  onChange={(e) => setFormData({...formData, family_member_id: parseInt(e.target.value)})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                >
                  <option value={0}>Selecione o paciente...</option>
                  {members.map(member => (
                    <option key={member.id} value={member.id}>{member.name}</option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Nome do Procedimento */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Nome do Procedimento *</label>
                  <input
                    type="text"
                    value={formData.procedure_name}
                    onChange={(e) => setFormData({...formData, procedure_name: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Ex: CID: N10 - Nefrite Túbulo-Intersticial aguda"
                    required
                  />
                </div>

                {/* Data/Hora do Procedimento */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Data e Hora *</label>
                  <DateTimeInput
                    value={formData.procedure_date}
                    onChange={(value) => setFormData({...formData, procedure_date: value})}
                    required
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Médico */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Nome do Médico *</label>
                  <input
                    type="text"
                    value={formData.doctor_name}
                    onChange={(e) => setFormData({...formData, doctor_name: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>

                {/* Local */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Local *</label>
                  <input
                    type="text"
                    value={formData.location}
                    onChange={(e) => setFormData({...formData, location: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Hospital, Clínica, etc."
                    required
                  />
                </div>
              </div>

              {/* Descrição */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Descrição *</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({...formData, description: e.target.value})}
                  rows={5}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Descreva o procedimento realizado..."
                  required
                />
              </div>

              {/* Resultados */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Resultados</label>
                <textarea
                  value={formData.results}
                  onChange={(e) => setFormData({...formData, results: e.target.value})}
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Resultados do procedimento..."
                />
              </div>

              {/* Observações de Acompanhamento */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Observações de Acompanhamento</label>
                <textarea
                  value={formData.follow_up_notes}
                  onChange={(e) => setFormData({...formData, follow_up_notes: e.target.value})}
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Observações sobre o acompanhamento..."
                />
              </div>

              {/* Próximo Procedimento */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Próximo Procedimento</label>
                <DateTimeInput
                  value={formData.next_procedure_date}
                  onChange={(value) => setFormData({...formData, next_procedure_date: value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
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
                  onClick={closeCreateView}
                  className="w-full sm:w-auto px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="w-full sm:w-auto px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 flex items-center justify-center"
                >
                  <Save className="mr-2 h-5 w-5" />
                  Criar Procedimento
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : !isEditingInline ? (
        // Tela de lista
        <>
          {/* Cabeçalho */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-6 gap-4">
            <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 flex items-center">
              <Activity className="mr-2 sm:mr-3 h-6 w-6 sm:h-8 sm:w-8 text-blue-600" />
              Procedimentos Médicos
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
                onClick={() => openCreateView()}
                className="flex-1 sm:flex-none px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors flex items-center justify-center"
              >
                <Plus className="mr-2 h-5 w-5" />
                Novo Procedimento
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
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
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
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Data Final</label>
                <DateInput
                  value={filters.end_date}
                  onChange={(value) => setFilters({...filters, end_date: value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div className="flex items-end">
                <button
                  onClick={handleFilter}
                  className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors flex items-center justify-center"
                >
                  <Filter className="mr-2 h-5 w-5" />
                  Filtrar
                </button>
              </div>
            </div>
          </div>

          {filteredProcedures.length === 0 ? (
        <div className="bg-white shadow rounded-lg p-6">
          <p className="text-gray-600 text-center py-8">
            Nenhum procedimento encontrado com os filtros aplicados.
          </p>
        </div>
      ) : (
        <>
          {/* Visualização em Cards para Mobile/Tablet */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:hidden gap-4 mb-6">
            {filteredProcedures.map((procedure) => (
              <div key={procedure.id} className="bg-white shadow rounded-lg p-4 space-y-3">
                {/* Cabeçalho do Card */}
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="text-lg font-semibold text-gray-900">{procedure.procedure_name}</h3>
                      {procedure.documents && (
                        <Paperclip className="h-4 w-4 text-blue-500" aria-label="Possui documentos anexados" />
                      )}
                    </div>
                    <div className="flex items-center text-sm text-gray-500 mt-1">
                      <User className="h-4 w-4 mr-1" />
                      {getMemberName(procedure.family_member_id)}
                    </div>
                  </div>
                </div>

                {/* Informações do Card */}
                <div className="space-y-2 text-sm">
                  <div>
                    <span className="font-medium text-gray-700">Data:</span>
                    <span className="ml-2 text-gray-900">{formatDateTimeBR(procedure.procedure_date)}</span>
                  </div>
                  <div>
                    <span className="font-medium text-gray-700">Médico:</span>
                    <span className="ml-2 text-gray-900">{procedure.doctor_name}</span>
                  </div>
                  <div>
                    <span className="font-medium text-gray-700">Local:</span>
                    <span className="ml-2 text-gray-900">{procedure.location}</span>
                  </div>
                  {procedure.description && (
                    <div>
                      <span className="font-medium text-gray-700">Descrição:</span>
                      <p className="mt-1 text-gray-900 text-xs line-clamp-3">{procedure.description}</p>
                    </div>
                  )}
                </div>

                {/* Ações do Card */}
                <div className="flex gap-2 pt-3 border-t border-gray-200">
                  <button 
                    onClick={() => startEdit(procedure)}
                    className="flex-1 flex items-center justify-center px-3 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700"
                  >
                    <Edit2 className="h-4 w-4 mr-1" />
                    Editar
                  </button>
                  <button 
                    onClick={() => handleDelete(procedure.id)}
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
                    Data
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Membro
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Procedimento
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Médico
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Local
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Descrição
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Ações
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredProcedures.map((procedure) => (
                  <tr key={procedure.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">
                        {formatDateTimeBR(procedure.procedure_date)}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <User className="h-5 w-5 text-gray-400 mr-2" />
                        <div className="text-sm font-medium text-gray-900">
                          {getMemberName(procedure.family_member_id)}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center">
                        <div className="text-sm font-medium text-gray-900">{procedure.procedure_name}</div>
                        {procedure.documents && (
                          <Paperclip className="h-4 w-4 text-blue-500 ml-2" aria-label="Possui documentos anexados" />
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">{procedure.doctor_name}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-600">{procedure.location}</div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-600 max-w-xs truncate" title={procedure.description}>
                        {procedure.description}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <button 
                        onClick={() => startEdit(procedure)}
                        className="text-blue-600 hover:text-blue-900 mr-3"
                        title="Editar"
                      >
                        <Edit2 className="h-5 w-5" />
                      </button>
                      <button 
                        onClick={() => handleDelete(procedure.id)}
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
              Editar Procedimento
            </h2>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4 md:space-y-6">
            {/* Paciente */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Paciente *</label>
              <select
                value={formData.family_member_id}
                onChange={(e) => setFormData({...formData, family_member_id: parseInt(e.target.value)})}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              >
                <option value={0}>Selecione o paciente...</option>
                {members.map(member => (
                  <option key={member.id} value={member.id}>{member.name}</option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Nome do Procedimento */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nome do Procedimento *</label>
                <input
                  type="text"
                  value={formData.procedure_name}
                  onChange={(e) => setFormData({...formData, procedure_name: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Ex: CID: N10 - Nefrite Túbulo-Intersticial aguda"
                  required
                />
              </div>

              {/* Data/Hora do Procedimento */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Data e Hora *</label>
                <DateTimeInput
                  value={formData.procedure_date}
                  onChange={(value) => setFormData({...formData, procedure_date: value})}
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Médico */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nome do Médico *</label>
                <input
                  type="text"
                  value={formData.doctor_name}
                  onChange={(e) => setFormData({...formData, doctor_name: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>

              {/* Local */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Local *</label>
                <input
                  type="text"
                  value={formData.location}
                  onChange={(e) => setFormData({...formData, location: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Hospital, Clínica, etc."
                  required
                />
              </div>
            </div>

            {/* Descrição */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Descrição *</label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({...formData, description: e.target.value})}
                rows={5}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Descreva o procedimento realizado..."
                required
              />
            </div>

            {/* Resultados */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Resultados</label>
              <textarea
                value={formData.results}
                onChange={(e) => setFormData({...formData, results: e.target.value})}
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Resultados do procedimento..."
              />
            </div>

            {/* Observações de Acompanhamento */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Observações de Acompanhamento</label>
              <textarea
                value={formData.follow_up_notes}
                onChange={(e) => setFormData({...formData, follow_up_notes: e.target.value})}
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Observações sobre o acompanhamento..."
              />
            </div>

            {/* Próximo Procedimento */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Próximo Procedimento</label>
              <DateTimeInput
                value={formData.next_procedure_date}
                onChange={(value) => setFormData({...formData, next_procedure_date: value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
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
                className="w-full sm:w-auto px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 flex items-center justify-center"
              >
                <Save className="mr-2 h-5 w-5" />
                Salvar Alterações
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}

