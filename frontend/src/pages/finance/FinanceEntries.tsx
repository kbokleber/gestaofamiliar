import { useState, useEffect } from 'react'
import { Plus, Trash2, Edit2, CheckCircle, XCircle } from 'lucide-react'
import { financeService, Entry, Category } from '../../services/financeService'
import Loading from '../../components/Loading'
import Modal from '../../components/Modal'
import Button from '../../components/Button'
import ConfirmDeleteModal from '../../components/ConfirmDeleteModal'

export default function FinanceEntries() {
  const [loading, setLoading] = useState(true)
  const [entries, setEntries] = useState<Entry[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false)
  const [selectedEntry, setSelectedEntry] = useState<Entry | null>(null)
  
  const [formData, setFormData] = useState({
    description: '',
    amount: '',
    date: new Date().toISOString().split('T')[0],
    type: 'EXPENSE',
    category_id: '',
    payment_method: '',
    is_paid: true,
    notes: ''
  })

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const [entriesData, categoriesData] = await Promise.all([
        financeService.getEntries(),
        financeService.getCategories()
      ])
      setEntries(entriesData)
      setCategories(categoriesData)
    } catch (error) {
      console.error('Erro ao carregar dados:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const payload = {
        ...formData,
        amount: parseFloat(formData.amount),
        category_id: formData.category_id ? parseInt(formData.category_id) : undefined
      }
      
      if (selectedEntry) {
        await financeService.updateEntry(selectedEntry.id, payload as any)
      } else {
        await financeService.createEntry(payload as any)
      }
      
      setIsModalOpen(false)
      loadData()
    } catch (error) {
      console.error('Erro ao salvar lançamento:', error)
    }
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

  if (loading && entries.length === 0) return <Loading />

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Lançamentos Financeiros</h1>
          <p className="text-gray-500">Gerencie suas receitas e despesas</p>
        </div>
        
        <button
          onClick={() => {
            setSelectedEntry(null)
            setFormData({
              description: '',
              amount: '',
              date: new Date().toISOString().split('T')[0],
              type: 'EXPENSE',
              category_id: '',
              payment_method: '',
              is_paid: true,
              notes: ''
            })
            setIsModalOpen(true)
          }}
          className="inline-flex items-center px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors shadow-sm"
        >
          <Plus className="h-5 w-5 mr-2" />
          Novo Lançamento
        </button>
      </div>

      {/* Tabela de Lançamentos */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
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
              {entries.map((entry) => (
                <tr key={entry.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                    {new Intl.DateTimeFormat('pt-BR').format(new Date(entry.date + 'T00:00:00'))}
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm font-medium text-gray-900">{entry.description}</div>
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
                    {entry.is_paid ? (
                      <span className="inline-flex items-center text-green-600 text-xs font-medium">
                        <CheckCircle className="h-4 w-4 mr-1" /> Pago
                      </span>
                    ) : (
                      <span className="inline-flex items-center text-orange-500 text-xs font-medium">
                        <XCircle className="h-4 w-4 mr-1" /> Pendente
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <button 
                      onClick={() => {
                        setSelectedEntry(entry)
                        setFormData({
                          description: entry.description,
                          amount: entry.amount.toString(),
                          date: entry.date,
                          type: entry.type,
                          category_id: entry.category_id?.toString() || '',
                          payment_method: entry.payment_method || '',
                          is_paid: entry.is_paid,
                          notes: entry.notes || ''
                        })
                        setIsModalOpen(true)
                      }}
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

          <div className="flex justify-end gap-3 mt-6">
            <Button variant="outline" onClick={() => setIsModalOpen(false)}>Cancelar</Button>
            <Button type="submit">Salvar</Button>
          </div>
        </form>
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
