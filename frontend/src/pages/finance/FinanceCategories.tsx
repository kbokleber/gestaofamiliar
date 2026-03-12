import { useState, useEffect } from 'react'
import { Plus, Wallet, Trash2, Edit2 } from 'lucide-react'
import { financeService, Category } from '../../services/financeService'
import Loading from '../../components/Loading'
import Modal from '../../components/Modal'
import Button from '../../components/Button'

// Lista de cores pré-definidas
const PRESET_COLORS = [
  '#ef4444', '#f97316', '#f59e0b', '#10b981', '#06b6d4', 
  '#3b82f6', '#6366f1', '#8b5cf6', '#d946ef', '#ec4899', '#64748b'
]

export default function FinanceCategories() {
  const [loading, setLoading] = useState(true)
  const [categories, setCategories] = useState<Category[]>([])
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [selectedCategory, setSelectedCategory] = useState<Category | null>(null)
  
  const [formData, setFormData] = useState({
    name: '',
    type: 'EXPENSE',
    color: '#3b82f6',
    icon: 'Wallet',
    is_active: true
  })

  useEffect(() => {
    loadCategories()
  }, [])

  const loadCategories = async () => {
    setLoading(true)
    try {
      const data = await financeService.getCategories()
      setCategories(data)
    } catch (error) {
      console.error('Erro ao carregar categorias:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      if (selectedCategory) {
        await financeService.updateCategory(selectedCategory.id, formData as any)
      } else {
        await financeService.createCategory(formData as any)
      }
      setIsModalOpen(false)
      loadCategories()
    } catch (error) {
      console.error('Erro ao salvar categoria:', error)
    }
  }

  if (loading && categories.length === 0) return <Loading />

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Categorias Financeiras</h1>
          <p className="text-gray-500">Personalize suas categorias de receitas e despesas</p>
        </div>
        
        <button
          onClick={() => {
            setSelectedCategory(null)
            setFormData({
              name: '',
              type: 'EXPENSE',
              color: '#3b82f6',
              icon: 'Wallet',
              is_active: true
            })
            setIsModalOpen(true)
          }}
          className="inline-flex items-center px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors shadow-sm"
        >
          <Plus className="h-5 w-5 mr-2" />
          Nova Categoria
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* Despesas */}
        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <span className="w-2 h-6 bg-red-500 rounded-full"></span>
            Categorias de Despesas
          </h2>
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 divide-y">
            {categories.filter((c: Category) => c.type === 'EXPENSE').map((cat: Category) => (
              <div key={cat.id} className="flex items-center justify-between p-4 hover:bg-gray-50 transition-colors">
                <div className="flex items-center gap-3">
                  <div 
                    className="p-2 rounded-lg text-white"
                    style={{ backgroundColor: cat.color }}
                  >
                    <Wallet size={20} />
                  </div>
                  <span className="font-medium text-gray-700">{cat.name}</span>
                </div>
                <div className="flex items-center gap-2">
                   <button 
                     onClick={() => {
                       setSelectedCategory(cat)
                       setFormData({
                         name: cat.name,
                         type: cat.type,
                         color: cat.color,
                         icon: cat.icon || 'Wallet',
                         is_active: cat.is_active
                       })
                       setIsModalOpen(true)
                     }}
                     className="p-1 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 rounded"
                   >
                     <Edit2 size={16} />
                   </button>
                   <button 
                     onClick={async () => {
                       if (window.confirm('Excluir esta categoria?')) {
                         await financeService.deleteCategory(cat.id)
                         loadCategories()
                       }
                     }}
                     className="p-1 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded"
                   >
                     <Trash2 size={16} />
                   </button>
                </div>
              </div>
            ))}
            {categories.filter((c: Category) => c.type === 'EXPENSE').length === 0 && (
              <p className="p-8 text-center text-gray-400 italic">Nenhuma categoria de despesa.</p>
            )}
          </div>
        </div>

        {/* Receitas */}
        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <span className="w-2 h-6 bg-green-500 rounded-full"></span>
            Categorias de Receitas
          </h2>
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 divide-y">
            {categories.filter((c: Category) => c.type === 'INCOME').map((cat: Category) => (
              <div key={cat.id} className="flex items-center justify-between p-4 hover:bg-gray-50 transition-colors">
                <div className="flex items-center gap-3">
                  <div 
                    className="p-2 rounded-lg text-white"
                    style={{ backgroundColor: cat.color }}
                  >
                    <Wallet size={20} />
                  </div>
                  <span className="font-medium text-gray-700">{cat.name}</span>
                </div>
                <div className="flex items-center gap-2">
                   <button 
                     onClick={() => {
                       setSelectedCategory(cat)
                       setFormData({
                         name: cat.name,
                         type: cat.type,
                         color: cat.color,
                         icon: cat.icon || 'Wallet',
                         is_active: cat.is_active
                       })
                       setIsModalOpen(true)
                     }}
                     className="p-1 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 rounded"
                   >
                     <Edit2 size={16} />
                   </button>
                   <button 
                     onClick={async () => {
                       if (window.confirm('Excluir esta categoria?')) {
                         await financeService.deleteCategory(cat.id)
                         loadCategories()
                       }
                     }}
                     className="p-1 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded"
                   >
                     <Trash2 size={16} />
                   </button>
                </div>
              </div>
            ))}
            {categories.filter((c: Category) => c.type === 'INCOME').length === 0 && (
              <p className="p-8 text-center text-gray-400 italic">Nenhuma categoria de receita.</p>
            )}
          </div>
        </div>
      </div>

      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Configurar Categoria"
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nome*</label>
            <input
              type="text"
              required
              value={formData.name}
              onChange={(e) => setFormData({...formData, name: e.target.value})}
              className="w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
              placeholder="Ex: Alimentação, Lazer..."
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Tipo*</label>
            <div className="grid grid-cols-2 gap-4">
               <button
                  type="button"
                  onClick={() => setFormData({...formData, type: 'EXPENSE'})}
                  className={`py-2 px-4 rounded-lg border text-sm font-medium ${formData.type === 'EXPENSE' ? 'bg-red-50 border-red-200 text-red-700' : 'bg-white border-gray-200 text-gray-600'}`}
               >
                 Despesa
               </button>
               <button
                  type="button"
                  onClick={() => setFormData({...formData, type: 'INCOME'})}
                  className={`py-2 px-4 rounded-lg border text-sm font-medium ${formData.type === 'INCOME' ? 'bg-green-50 border-green-200 text-green-700' : 'bg-white border-gray-200 text-gray-600'}`}
               >
                 Receita
               </button>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Cor</label>
            <div className="flex flex-wrap gap-2">
              {PRESET_COLORS.map(color => (
                <button
                  key={color}
                  type="button"
                  onClick={() => setFormData({...formData, color})}
                  className={`w-8 h-8 rounded-full border-2 transition-transform hover:scale-110 ${formData.color === color ? 'border-gray-900' : 'border-transparent'}`}
                  style={{ backgroundColor: color }}
                />
              ))}
            </div>
          </div>

          <div className="flex justify-end gap-3 mt-6">
            <Button variant="outline" onClick={() => setIsModalOpen(false)}>Cancelar</Button>
            <Button type="submit">Salvar Categoria</Button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
