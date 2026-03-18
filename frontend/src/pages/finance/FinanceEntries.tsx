import { useState, useEffect, useRef } from 'react'
import { Plus, Trash2, Edit2, CheckCircle, XCircle, Camera, Loader2, Paperclip, Image, HelpCircle, ChevronDown } from 'lucide-react'
import { financeService, Entry, Category } from '../../services/financeService'
import Loading from '../../components/Loading'
import Modal from '../../components/Modal'
import Button from '../../components/Button'
import ConfirmDeleteModal from '../../components/ConfirmDeleteModal'
import api from '../../lib/api'
import { useAuthStore } from '../../stores/authStore'

const formatDateForInput = (date: Date) => {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')

  return `${year}-${month}-${day}`
}

const getCurrentMonthFilter = () => {
  const now = new Date()

  return {
    start_date: formatDateForInput(new Date(now.getFullYear(), now.getMonth(), 1)),
    end_date: formatDateForInput(new Date(now.getFullYear(), now.getMonth() + 1, 0)),
  }
}

interface FamilyAIConfig {
  enabled: boolean
  provider: string
  openai_model: string | null
  has_openai_key: boolean
  has_azure_config: boolean
}

interface CustomSelectProps {
  value: string;
  onChange: (val: string) => void;
  options: { value: string; label: string }[];
  placeholder?: string;
}

function CustomSelect({ value, onChange, options, placeholder = 'Selecione...' }: CustomSelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const selectedOption = options.find((opt) => opt.value === value);

  return (
    <div className="relative w-full" ref={containerRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full items-center justify-between rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 h-[38px] transition-colors"
      >
        <span className={selectedOption && value !== '' ? 'text-gray-900' : 'text-gray-500'}>
          {selectedOption ? selectedOption.label : placeholder}
        </span>
        <ChevronDown className={`h-4 w-4 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute z-50 mt-1 max-h-60 w-full overflow-auto rounded-md bg-white py-1 text-base shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none sm:text-sm">
          {options.map((option) => (
            <div
              key={option.value}
              className={`relative cursor-pointer select-none py-2 px-3 ${
                option.value === value ? 'bg-indigo-50 text-indigo-900' : 'text-gray-900 hover:bg-gray-100'
              }`}
              onClick={() => {
                onChange(option.value);
                setIsOpen(false);
              }}
            >
              <span className={`block truncate ${option.value === value ? 'font-medium' : 'font-normal'}`}>
                {option.label}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function FinanceEntries() {
  const { user: currentUser } = useAuthStore()
  const [loading, setLoading] = useState(true)
  const [entries, setEntries] = useState<Entry[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false)
  const [selectedEntry, setSelectedEntry] = useState<Entry | null>(null)
  const [filters, setFilters] = useState(() => ({
    ...getCurrentMonthFilter(),
    category_id: '',
    status: 'ALL'
  }))
  
  const [visibleCount, setVisibleCount] = useState(20)

  const [formData, setFormData] = useState({
    description: '',
    amount: '',
    date: new Date().toISOString().substring(0, 10),
    type: 'EXPENSE',
    category_id: '',
    payment_method: '',
    is_paid: true,
    notes: '',
    documents: undefined as string | null | undefined
  })
  const [isUploading, setIsUploading] = useState(false)
  const [statusUpdatingId, setStatusUpdatingId] = useState<number | null>(null)
  const [familyAiConfig, setFamilyAiConfig] = useState<FamilyAIConfig | null>(null)
  const [showScanMenu, setShowScanMenu] = useState(false)
  const [isScanHelpOpen, setIsScanHelpOpen] = useState(false)

  useEffect(() => {
    setVisibleCount(20)
    loadData()
  }, [filters])

  const loadData = async () => {
    setLoading(true)
    try {
      const params = {
        start_date: filters.start_date || undefined,
        end_date: filters.end_date || undefined,
        category_id: filters.category_id ? parseInt(filters.category_id) : undefined,
        is_paid: filters.status === 'PAID' ? true : filters.status === 'PENDING' ? false : undefined
      }

      const [entriesData, categoriesData] = await Promise.all([
        financeService.getEntries(params),
        financeService.getCategories()
      ])
      setEntries(entriesData)
      setCategories(categoriesData)

      try {
        const familyIdParam =
          currentUser?.family_id ??
          currentUser?.family_ids?.[0] ??
          undefined

        const { data } = await api.get<FamilyAIConfig>('/telegram/family/ai', {
          params: familyIdParam ? { family_id: familyIdParam } : undefined
        })
        setFamilyAiConfig(data)
      } catch (error) {
        console.error('Erro ao carregar configuração de IA da família:', error)
        setFamilyAiConfig(null)
      }
    } catch (error) {
      console.error('Erro ao carregar dados:', error)
    } finally {
      setLoading(false)
    }
  }

  const isFamilyAiConfigured =
    !!familyAiConfig &&
    familyAiConfig.enabled &&
    familyAiConfig.provider !== 'none' &&
    (
      ((familyAiConfig.provider === 'openai' || familyAiConfig.provider === 'nvidia-nim') && familyAiConfig.has_openai_key) ||
      (familyAiConfig.provider === 'azure' && familyAiConfig.has_azure_config)
    )

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const payload: any = {
        description: formData.description,
        amount: parseFloat(formData.amount),
        date: formData.date,
        type: formData.type,
        category_id: formData.category_id ? parseInt(formData.category_id) : undefined,
        payment_method: formData.payment_method || undefined,
        is_paid: formData.is_paid,
        notes: formData.notes || undefined,
      }
      
      if (!selectedEntry || formData.documents !== selectedEntry.documents) {
        payload.documents = formData.documents === undefined ? undefined : formData.documents
      }
      
      console.log('Salvando lançamento:', payload)
      if (selectedEntry) {
        await financeService.updateEntry(selectedEntry.id, payload as any)
      } else {
        const result = await financeService.createEntry(payload as any)
        console.log('Lançamento criado:', result)
      }
      
      setIsModalOpen(false)
      loadData()
    } catch (error) {
      console.error('Erro ao salvar lançamento:', error)
    }
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setIsUploading(true)
    try {
      await financeService.uploadReceipt(file)
      alert('Comprovante processado e cadastrado com sucesso!')
      loadData()
    } catch (error: any) {
      console.error('Erro ao processar comprovante:', error)
      const message = error.response?.data?.detail || 'Erro ao processar comprovante. Verifique se a IA está configurada ou tente novamente.'
      alert(message)
    } finally {
      setIsUploading(false)
      // Limpar o input
      e.target.value = ''
    }
  }

  const triggerFileInput = (inputId: string) => {
    const input = document.getElementById(inputId) as HTMLInputElement | null
    input?.click()
  }

  const handleDelete = async () => {
    if (!selectedEntry) return
    try {
      await financeService.deleteEntry(selectedEntry.id)
      setIsDeleteModalOpen(false)
      loadData()
    } catch (error) {
      console.error('Erro ao excluir:', error)
    }
  }

  const openEntryModal = (entry?: Entry) => {
    if (entry) {
      setSelectedEntry(entry)
      setFormData({
        description: entry.description,
        amount: entry.amount.toString(),
        date: entry.date,
        type: entry.type,
        category_id: entry.category_id?.toString() || '',
        payment_method: entry.payment_method || '',
        is_paid: entry.is_paid,
        notes: entry.notes || '',
        documents: entry.documents ?? undefined
      })
    } else {
      setSelectedEntry(null)
      setFormData({
        description: '',
        amount: '',
        date: new Date().toISOString().substring(0, 10),
        type: 'EXPENSE',
        category_id: '',
        payment_method: '',
        is_paid: true,
        notes: '',
        documents: undefined
      })
    }

    setIsModalOpen(true)
  }

  const handleTogglePaidStatus = async (entry: Entry) => {
    setStatusUpdatingId(entry.id)
    try {
      await financeService.updateEntry(entry.id, { is_paid: !entry.is_paid })
      await loadData()
    } catch (error) {
      console.error('Erro ao atualizar status do lançamento:', error)
      alert('Não foi possível atualizar o status do lançamento.')
    } finally {
      setStatusUpdatingId(null)
    }
  }

  const renderStatusBadge = (entry: Entry, compact = false) => {
    const isUpdating = statusUpdatingId === entry.id

    return (
      <button
        type="button"
        onClick={() => handleTogglePaidStatus(entry)}
        disabled={isUpdating}
        className={`inline-flex items-center justify-center rounded-full transition-colors ${
          compact ? 'px-2.5 py-1 text-xs' : 'px-3 py-1.5 text-sm'
        } ${
          entry.is_paid
            ? 'bg-green-50 text-green-700 hover:bg-green-100'
            : 'bg-orange-50 text-orange-600 hover:bg-orange-100'
        } disabled:opacity-60 disabled:cursor-not-allowed`}
        title={entry.is_paid ? 'Marcar como pendente' : 'Marcar como pago'}
      >
        {isUpdating ? (
          <Loader2 className={`animate-spin ${compact ? 'h-3.5 w-3.5' : 'h-4 w-4'}`} />
        ) : entry.is_paid ? (
          <>
            <CheckCircle className={`${compact ? 'h-3.5 w-3.5 mr-1' : 'h-4 w-4 mr-1.5'}`} />
            Pago
          </>
        ) : (
          <>
            <XCircle className={`${compact ? 'h-3.5 w-3.5 mr-1' : 'h-4 w-4 mr-1.5'}`} />
            Pendente
          </>
        )}
      </button>
    )
  }

  const handleViewReceipt = async (documentsJson: string) => {
    try {
      if (selectedEntry && formData.documents === selectedEntry.documents) {
        const tokenStr = localStorage.getItem('auth-storage');
        const token = tokenStr ? JSON.parse(tokenStr).state?.token : '';
        if (token) {
          const response = await api.get(`/finance/entries/${selectedEntry.id}/receipt`, { responseType: 'blob' });
          const url = URL.createObjectURL(response.data);
          window.open(url, '_blank');
          return;
        }
      }

      const docs = JSON.parse(documentsJson)
      if (docs && docs.length > 0) {
        const doc = docs[0]
        if (!doc.content) {
          alert('Este comprovante está vazio ou corrompido.');
          return;
        }
        const byteString = atob(doc.content)
        const ab = new ArrayBuffer(byteString.length)
        const ia = new Uint8Array(ab)
        for (let i = 0; i < byteString.length; i++) {
          ia[i] = byteString.charCodeAt(i)
        }
        const blob = new Blob([ab], { type: doc.type || 'image/jpeg' })
        const url = URL.createObjectURL(blob)
        window.open(url, '_blank')
      }
    } catch (error) {
      console.error('Erro ao visualizar comprovante:', error)
      alert('Erro ao abrir o comprovante. Pode estar indisponível.')
    }
  }

  const handleManualFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    // Limitar tamanho (ex: 5MB)
    if (file.size > 5 * 1024 * 1024) {
      alert('Arquivo muito grande. O limite é 5MB.')
      return
    }

    const reader = new FileReader()
    reader.onload = () => {
      const b64 = (reader.result as string).split(',')[1]
      const docObj = [{
        name: file.name,
        type: file.type,
        content: b64
      }]
      setFormData({ ...formData, documents: JSON.stringify(docObj) })
    }
    reader.onerror = () => {
      alert('Erro ao ler arquivo.')
    }
    reader.readAsDataURL(file)
  }

  if (loading && entries.length === 0) return <Loading />

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Lançamentos Financeiros</h1>
          <p className="text-gray-500">Gerencie suas receitas e despesas</p>
        </div>
        
        <div className="flex flex-col sm:flex-row gap-2 sm:items-start">
          <div className="flex items-center gap-2">
            <div className="relative">
              <button
                type="button"
                onClick={() => {
                  if (isUploading || !isFamilyAiConfigured) return
                  setShowScanMenu((prev) => !prev)
                }}
                className={`inline-flex items-center px-4 py-2 rounded-lg transition-colors shadow-sm ${
                  isUploading || !isFamilyAiConfigured
                    ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                    : 'bg-indigo-50 text-indigo-700 hover:bg-indigo-100 cursor-pointer'
                }`}
                title={!isFamilyAiConfigured ? 'Configure a IA da família para habilitar o escaneamento de recibos.' : undefined}
                disabled={isUploading || !isFamilyAiConfigured}
              >
                {isUploading ? (
                  <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                ) : (
                  <Camera className="h-5 w-5 mr-2" />
                )}
                {isUploading ? 'Processando...' : 'Escanear Recibo'}
              </button>

              {showScanMenu && isFamilyAiConfigured && !isUploading && (
                <div className="absolute right-0 top-full z-20 mt-2 min-w-[190px] overflow-hidden rounded-lg border border-gray-200 bg-white shadow-xl">
                  <button
                    type="button"
                    onClick={() => {
                      setShowScanMenu(false)
                      triggerFileInput('receipt-camera-input')
                    }}
                    className="flex w-full items-center gap-3 px-4 py-3 text-left text-gray-700 hover:bg-gray-100"
                  >
                    <Camera className="h-5 w-5 text-indigo-600" />
                    <span>Câmera</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setShowScanMenu(false)
                      triggerFileInput('receipt-gallery-input')
                    }}
                    className="flex w-full items-center gap-3 border-t border-gray-200 px-4 py-3 text-left text-gray-700 hover:bg-gray-100"
                  >
                    <Image className="h-5 w-5 text-green-600" />
                    <span>Galeria</span>
                  </button>
                </div>
              )}

              <input
                id="receipt-camera-input"
                type="file"
                className="hidden"
                accept="image/*,application/pdf"
                capture="environment"
                onChange={handleFileUpload}
                disabled={isUploading || !isFamilyAiConfigured}
              />
              <input
                id="receipt-gallery-input"
                type="file"
                className="hidden"
                accept="image/*,application/pdf"
                onChange={handleFileUpload}
                disabled={isUploading || !isFamilyAiConfigured}
              />
            </div>

            <button
              type="button"
              onClick={() => setIsScanHelpOpen(true)}
              className="inline-flex items-center justify-center rounded-lg border border-gray-200 bg-white p-2.5 text-gray-500 shadow-sm transition-colors hover:bg-gray-50 hover:text-indigo-600"
              title="Como funciona a captura do recibo"
              aria-label="Como funciona a captura do recibo"
            >
              <HelpCircle className="h-5 w-5" />
            </button>
          </div>

          <button
            onClick={() => openEntryModal()}
            className="inline-flex items-center px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors shadow-sm"
          >
            <Plus className="h-5 w-5 mr-2" />
            Novo Lançamento
          </button>
        </div>
      </div>

      {!isFamilyAiConfigured && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          O escaneamento de recibos fica disponível somente quando a IA da família estiver configurada.
        </div>
      )}

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <div className="flex flex-col lg:flex-row gap-4 lg:items-end">
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 flex-1">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Data inicial</label>
              <input
                type="date"
                value={filters.start_date}
                onChange={(e) => setFilters((prev) => ({ ...prev, start_date: e.target.value }))}
                className="w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Data final</label>
              <input
                type="date"
                value={filters.end_date}
                onChange={(e) => setFilters((prev) => ({ ...prev, end_date: e.target.value }))}
                className="w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Categoria</label>
              <CustomSelect
                value={filters.category_id}
                onChange={(val) => setFilters((prev) => ({ ...prev, category_id: val }))}
                options={[
                  { value: '', label: 'Todas' },
                  ...categories.map(c => ({ value: c.id.toString(), label: c.name }))
                ]}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
              <CustomSelect
                value={filters.status}
                onChange={(val) => setFilters((prev) => ({ ...prev, status: val }))}
                options={[
                  { value: 'ALL', label: 'Todos' },
                  { value: 'PAID', label: 'Pago' },
                  { value: 'PENDING', label: 'Pendente' }
                ]}
              />
            </div>
          </div>

          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => setFilters({
                ...getCurrentMonthFilter(),
                category_id: '',
                status: 'ALL'
              })}
            >
              Mês atual
            </Button>
            <Button
              variant="outline"
              onClick={() => setFilters({
                start_date: '',
                end_date: '',
                category_id: '',
                status: 'ALL'
              })}
            >
              Limpar
            </Button>
          </div>
        </div>
      </div>

      {/* Lista mobile */}
      <div className="space-y-3 md:hidden">
        {entries.length === 0 ? (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 text-center text-gray-500">
            Nenhum lançamento encontrado.
          </div>
        ) : (
          entries.slice(0, visibleCount).map((entry) => (
            <div key={entry.id} className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 space-y-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-semibold text-gray-900 break-words">{entry.description}</p>
                    {entry.documents && <Paperclip className="h-3.5 w-3.5 text-gray-400 shrink-0" />}
                  </div>
                  <p className="mt-1 text-xs text-gray-500">
                    {new Intl.DateTimeFormat('pt-BR').format(new Date(entry.date + 'T00:00:00'))}
                    {entry.payment_method ? ` • ${entry.payment_method}` : ''}
                  </p>
                </div>
                <div className={`text-sm font-bold whitespace-nowrap ${entry.type === 'INCOME' ? 'text-green-600' : 'text-red-600'}`}>
                  {entry.type === 'INCOME' ? '+' : '-'} {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(entry.amount)}
                </div>
              </div>

              <div className="flex items-center justify-between gap-3">
                <div>
                  {entry.category ? (
                    <span
                      className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
                      style={{ backgroundColor: `${entry.category.color}15`, color: entry.category.color }}
                    >
                      {entry.category.name}
                    </span>
                  ) : (
                    <span className="text-xs text-gray-400">Sem categoria</span>
                  )}
                </div>
                {renderStatusBadge(entry, true)}
              </div>

              <div className="grid grid-cols-2 gap-2">
                <Button
                  variant={entry.is_paid ? 'outline' : 'primary'}
                  onClick={() => handleTogglePaidStatus(entry)}
                  disabled={statusUpdatingId === entry.id}
                  className={entry.is_paid ? 'text-orange-600 border-orange-200 hover:bg-orange-50' : 'bg-green-600 hover:bg-green-700'}
                >
                  {statusUpdatingId === entry.id ? (
                    <span className="inline-flex items-center justify-center gap-2">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Salvando...
                    </span>
                  ) : entry.is_paid ? (
                    'Marcar pendente'
                  ) : (
                    'Marcar pago'
                  )}
                </Button>
                <div className="flex gap-2">
                  <Button variant="outline" onClick={() => openEntryModal(entry)} className="flex-1 px-3">
                    <Edit2 className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="danger"
                    onClick={() => {
                      setSelectedEntry(entry)
                      setIsDeleteModalOpen(true)
                    }}
                    className="flex-1 px-3"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </div>
          ))
        )}
        
        {entries.length > visibleCount && (
          <div className="pt-2 pb-4 flex justify-center">
            <Button
              variant="outline"
              onClick={() => setVisibleCount((prev) => prev + 20)}
              className="w-full bg-white text-indigo-600 border-indigo-200 shadow-sm"
            >
              Carregar mais lançamentos
            </Button>
          </div>
        )}
      </div>

      {/* Tabela desktop */}
      <div className="hidden md:block bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Data</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Descrição</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Categoria</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Valor</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Ações</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {entries.slice(0, visibleCount).map((entry) => (
                <tr key={entry.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                    {new Intl.DateTimeFormat('pt-BR').format(new Date(entry.date + 'T00:00:00'))}
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                       <div className="text-sm font-medium text-gray-900">{entry.description}</div>
                       {entry.documents && (
                         <Paperclip className="h-3.5 w-3.5 text-gray-400" />
                       )}
                    </div>
                    {entry.payment_method && <div className="text-xs text-gray-400">{entry.payment_method}</div>}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {entry.category ? (
                      <span 
                        className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
                        style={{ backgroundColor: `${entry.category.color}15`, color: entry.category.color }}
                      >
                        {entry.category.name}
                      </span>
                    ) : (
                      <span className="text-xs text-gray-400">Sem categoria</span>
                    )}
                  </td>
                  <td className={`px-6 py-4 whitespace-nowrap text-sm font-bold ${entry.type === 'INCOME' ? 'text-green-600' : 'text-red-600'}`}>
                    {entry.type === 'INCOME' ? '+' : '-'} {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(entry.amount)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {renderStatusBadge(entry)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <button 
                      onClick={() => openEntryModal(entry)}
                      className="text-indigo-600 hover:text-indigo-900 mx-1 p-1 hover:bg-indigo-50 rounded"
                    >
                      <Edit2 className="h-4 w-4" />
                    </button>
                    <button 
                      onClick={() => {
                        setSelectedEntry(entry)
                        setIsDeleteModalOpen(true)
                      }}
                      className="text-red-600 hover:text-red-900 mx-1 p-1 hover:bg-red-50 rounded"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))}
              {entries.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-gray-500">
                    Nenhum lançamento encontrado. Clique em "Novo Lançamento" para começar.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        
        {entries.length > visibleCount && (
          <div className="p-4 border-t border-gray-200 flex justify-center bg-gray-50">
            <Button
              variant="outline"
              onClick={() => setVisibleCount((prev) => prev + 20)}
              className="bg-white text-indigo-600 border-indigo-200 shadow-sm"
            >
              Carregar mais lançamentos
            </Button>
          </div>
        )}
      </div>

      {/* Modal de Lançamento */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={selectedEntry ? 'Editar Lançamento' : 'Novo Lançamento'}
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <button
              type="button"
              onClick={() => setFormData({...formData, type: 'EXPENSE'})}
              className={`py-2 px-4 rounded-lg border text-sm font-medium transition-all ${formData.type === 'EXPENSE' ? 'bg-red-50 border-red-200 text-red-700 ring-2 ring-red-500' : 'bg-gray-50 border-gray-200 text-gray-600'}`}
            >
              Despesa
            </button>
            <button
              type="button"
              onClick={() => setFormData({...formData, type: 'INCOME'})}
              className={`py-2 px-4 rounded-lg border text-sm font-medium transition-all ${formData.type === 'INCOME' ? 'bg-green-50 border-green-200 text-green-700 ring-2 ring-green-500' : 'bg-gray-50 border-gray-200 text-gray-600'}`}
            >
              Receita
            </button>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Descrição*</label>
            <input
              type="text"
              required
              value={formData.description}
              onChange={(e) => setFormData({...formData, description: e.target.value})}
              className="w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
              placeholder="Ex: Aluguel, Supermercado, Salário"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Valor*</label>
              <input
                type="number"
                step="0.01"
                required
                value={formData.amount}
                onChange={(e) => setFormData({...formData, amount: e.target.value})}
                className="w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                placeholder="0,00"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Data*</label>
              <input
                type="date"
                required
                value={formData.date}
                onChange={(e) => setFormData({...formData, date: e.target.value})}
                className="w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Categoria</label>
              <select
                value={formData.category_id}
                onChange={(e) => setFormData({...formData, category_id: e.target.value})}
                className="w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
              >
                <option value="">Selecione...</option>
                {categories.filter(c => c.type === formData.type).map(cat => (
                  <option key={cat.id} value={cat.id}>{cat.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Meio de Pagamento</label>
              <input
                type="text"
                value={formData.payment_method}
                onChange={(e) => setFormData({...formData, payment_method: e.target.value})}
                className="w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                placeholder="Cartão, Pix, etc"
              />
            </div>
          </div>

          <div className="flex items-center">
            <input
              type="checkbox"
              id="is_paid"
              checked={formData.is_paid}
              onChange={(e) => setFormData({...formData, is_paid: e.target.checked})}
              className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
            />
            <label htmlFor="is_paid" className="ml-2 block text-sm text-gray-900">
              {formData.type === 'INCOME' ? 'Recebido' : 'Pago'}
            </label>
          </div>

          {formData.documents ? (
            <div className="pt-4 border-t border-gray-100 bg-gray-50 p-3 rounded-lg">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm text-gray-600">
                  <Paperclip className="h-4 w-4 text-indigo-500" />
                  <span className="font-medium">Comprovante anexado</span>
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => handleViewReceipt(formData.documents!)}
                    className="text-xs font-semibold text-indigo-600 hover:text-indigo-800"
                  >
                    Visualizar
                  </button>
                  <button
                    type="button"
                    onClick={() => setFormData({ ...formData, documents: null })}
                    className="text-xs font-semibold text-red-600 hover:text-red-800 border-l pl-2 border-gray-300"
                  >
                    Remover
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="pt-4 border-t border-gray-100 border-dashed">
               <input
                type="file"
                id="manual-receipt-upload"
                className="hidden"
                accept="image/*,application/pdf"
                onChange={handleManualFileUpload}
              />
              <label 
                htmlFor="manual-receipt-upload"
                className="flex items-center justify-center gap-2 p-3 border-2 border-dashed border-gray-200 rounded-lg cursor-pointer hover:border-indigo-300 hover:bg-indigo-50 transition-all group"
              >
                <Camera className="h-5 w-5 text-gray-400 group-hover:text-indigo-500" />
                <span className="text-sm font-medium text-gray-500 group-hover:text-indigo-600">Anexar Comprovante (sem IA)</span>
              </label>
            </div>
          )}

          <div className="flex justify-end gap-3 mt-6">
            <Button variant="outline" onClick={() => setIsModalOpen(false)}>Cancelar</Button>
            <Button type="submit">Salvar</Button>
          </div>
        </form>
      </Modal>

      <Modal
        isOpen={isScanHelpOpen}
        onClose={() => setIsScanHelpOpen(false)}
        title="Como funciona a captura do recibo"
      >
        <div className="space-y-4 text-sm text-gray-600">
          <p>
            Quando você envia uma imagem ou PDF, o sistema tenta interpretar o documento e criar a despesa automaticamente.
          </p>

          <div className="space-y-3 rounded-lg bg-gray-50 p-4">
            <div>
              <p className="font-medium text-gray-900">Data do lançamento</p>
              <p>
                A IA prioriza a data da compra, transação ou emissão do comprovante. Se não existir uma data válida no documento, o sistema usa a data do upload.
              </p>
            </div>

            <div>
              <p className="font-medium text-gray-900">Categoria</p>
              <p>
                O sistema tenta encontrar uma categoria já existente que seja igual ou relacionada ao recibo. Só cria uma categoria nova quando não encontra nada suficientemente próximo.
              </p>
            </div>

            <div>
              <p className="font-medium text-gray-900">Compras parceladas</p>
              <p>
                Se o documento indicar parcelamento, a parcela atual é criada como paga e as próximas são lançadas nos meses seguintes como pendentes.
              </p>
            </div>

            <div>
              <p className="font-medium text-gray-900">Valor das parcelas</p>
              <p>
                O valor total do comprovante é dividido entre as parcelas mensais, mantendo a soma exata mesmo quando os centavos não dividem igualmente.
              </p>
            </div>

            <div>
              <p className="font-medium text-gray-900">Datas futuras das parcelas</p>
              <p>
                As parcelas futuras mantêm o mesmo dia sempre que possível. Quando o mês não tem esse dia, o sistema usa o último dia disponível.
              </p>
            </div>

            <div>
              <p className="font-medium text-gray-900">Evitar duplicidade</p>
              <p>
                Se já existir um lançamento com a mesma data e o mesmo valor para a família, o comprovante é tratado como duplicado e não é lançado novamente.
              </p>
            </div>
          </div>
        </div>
      </Modal>

      <ConfirmDeleteModal
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        onConfirm={handleDelete}
        title="Excluir Lançamento"
        message="Tem certeza que deseja excluir este lançamento? Esta ação não pode ser desfeita."
      />
    </div>
  )
}
