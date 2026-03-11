import { useState, useEffect } from 'react'
import { Plus, Trash2, CheckCircle2, XCircle, Info } from 'lucide-react'
import { financeService, Recurrence, Category } from '../../services/financeService'
import Loading from '../../components/Loading'
import Modal from '../../components/Modal'
import Button from '../../components/Button'

export default function FinanceRecurrences() {
  const [loading, setLoading] = useState(true)
  const [recurrences, setRecurrences] = useState<Recurrence[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [isModalOpen, setIsModalOpen] = useState(false)
  
  const [formData, setFormData] = useState({
    description: '',
    amount: '',
    type: 'EXPENSE',
    category_id: '',
    day_of_month: '1',
    is_active: true
  })

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const [recData, catData] = await Promise.all([
        financeService.getRecurrences(),
        financeService.getCategories()
      ])
      setRecurrences(recData)
      setCategories(catData)
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
        category_id: formData.category_id ? parseInt(formData.category_id) : undefined,
        day_of_month: parseInt(formData.day_of_month)
      }
      
      await financeService.createRecurrence(payload as any)
      setIsModalOpen(false)
      loadData()
    } catch (error) {
      console.error('Erro ao salvar recorrência:', error)
    }
  }

  if (loading && recurrences.length === 0) return <Loading />

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Recorrências Mensais</h1>
          <p className="text-gray-500">Automatize os lançamentos fixos do seu mês</p>
        </div>
        
        <button
          onClick={() => {
            setFormData({
              description: '',
              amount: '',
              type: 'EXPENSE',
              category_id: '',
              day_of_month: '1',
              is_active: true
            })
            setIsModalOpen(true)
          }}
          className="inline-flex items-center px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors shadow-sm"
        >
          <Plus className="h-5 w-5 mr-2" />
          Nova Recorrência
        </button>
      </div>

      <div className="bg-blue-50 border border-blue-200 p-4 rounded-xl flex gap-3 text-blue-800">
        <Info className="h-5 w-5 flex-shrink-0" />
        <div className="text-sm">
          <p className="font-semibold">Como funcionam as recorrências?</p>
          <p>Os itens cadastrados aqui servem de modelo. Todo início de mês, você pode clicar no botão de "Sincronizar" no Dashboard para gerar os lançamentos reais automaticamente baseados nestas regras.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {recurrences.map((rec) => (
          <div key={rec.id} className="bg-white p-5 rounded-xl shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
            <div className="flex justify-between items-start mb-3">
              <div>
                <h3 className="font-bold text-gray-900">{rec.description}</h3>
                <p className="text-xs text-gray-500">Dia {rec.day_of_month} de cada mês</p>
              </div>
              {rec.is_active ? (
                <CheckCircle2 className="h-5 w-5 text-green-500" />
              ) : (
                <XCircle className="h-5 w-5 text-gray-300" />
              )}
            </div>

            <div className={`text-xl font-bold mb-4 ${rec.type === 'INCOME' ? 'text-green-600' : 'text-red-600'}`}>
              {rec.type === 'INCOME' ? '+' : '-'} {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(rec.amount)}
            </div>

            <div className="flex justify-between items-center pt-4 border-t border-gray-50">
              <span className="text-xs font-medium px-2 py-1 bg-gray-100 text-gray-600 rounded">
                {rec.category?.name || 'Sem categoria'}
              </span>
              <button 
                className="text-gray-400 hover:text-red-600 transition-colors"
                title="Excluir (em breve)"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          </div>
        ))}

        {recurrences.length === 0 && (
          <div className="col-span-full py-12 text-center text-gray-500 border-2 border-dashed border-gray-200 rounded-xl">
            Nenhuma recorrência cadastrada ainda.
          </div>
        )}
      </div>

      {/* Modal de Recorrência */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Nova Recorrência"
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
              placeholder="Ex: Aluguel, Internet, Academia"
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
              <label className="block text-sm font-medium text-gray-700 mb-1">Dia do Vencimento (1-28)*</label>
              <input
                type="number"
                min="1"
                max="28"
                required
                value={formData.day_of_month}
                onChange={(e) => setFormData({...formData, day_of_month: e.target.value})}
                className="w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
              />
            </div>
          </div>

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

          <div className="flex justify-end gap-3 mt-6">
            <Button variant="outline" onClick={() => setIsModalOpen(false)}>Cancelar</Button>
            <Button type="submit">Cadastrar</Button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
