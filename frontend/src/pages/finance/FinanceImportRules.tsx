import { useEffect, useState } from 'react'
import { Plus, Edit2, ListFilter } from 'lucide-react'
import { financeService, Category, ImportCategoryRule } from '../../services/financeService'
import Loading from '../../components/Loading'
import Modal from '../../components/Modal'
import Button from '../../components/Button'

const entryTypeLabel = (t: string) => {
  if (t === 'EXPENSE') return 'Despesa'
  if (t === 'INCOME') return 'Receita'
  return 'Ambos'
}

export default function FinanceImportRules() {
  const [loading, setLoading] = useState(true)
  const [categories, setCategories] = useState<Category[]>([])
  const [rules, setRules] = useState<ImportCategoryRule[]>([])
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<ImportCategoryRule | null>(null)
  const [form, setForm] = useState({
    pattern: '',
    category_id: 0,
    entry_type: 'EXPENSE' as 'EXPENSE' | 'INCOME' | 'BOTH',
    priority: 100,
    is_active: true,
  })

  const load = async () => {
    setLoading(true)
    try {
      const [cats, r] = await Promise.all([
        financeService.getCategories(),
        financeService.getImportCategoryRules(),
      ])
      setCategories(cats.filter((c) => c.is_active))
      setRules(r)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const categoriesForSelect = () => {
    if (form.entry_type === 'BOTH') return categories
    return categories.filter((c) => c.type === form.entry_type)
  }

  const openCreate = () => {
    setEditing(null)
    const first = categories.find((c) => c.type === 'EXPENSE')
    setForm({
      pattern: '',
      category_id: first?.id ?? 0,
      entry_type: 'EXPENSE',
      priority: 100,
      is_active: true,
    })
    setModalOpen(true)
  }

  const openEdit = (rule: ImportCategoryRule) => {
    setEditing(rule)
    setForm({
      pattern: rule.pattern,
      category_id: rule.category_id,
      entry_type: rule.entry_type,
      priority: rule.priority,
      is_active: rule.is_active,
    })
    setModalOpen(true)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.pattern.trim() || !form.category_id) return
    try {
      if (editing) {
        await financeService.updateImportCategoryRule(editing.id, {
          pattern: form.pattern.trim(),
          category_id: form.category_id,
          entry_type: form.entry_type,
          priority: form.priority,
          is_active: form.is_active,
        })
      } else {
        await financeService.createImportCategoryRule({
          pattern: form.pattern.trim(),
          category_id: form.category_id,
          entry_type: form.entry_type,
          priority: form.priority,
          is_active: form.is_active,
        })
      }
      setModalOpen(false)
      load()
    } catch (err) {
      console.error(err)
      alert('Não foi possível salvar a regra. Verifique tipo da categoria e da regra.')
    }
  }

  const handleDeactivate = async (rule: ImportCategoryRule) => {
    if (!window.confirm('Desativar esta regra?')) return
    try {
      await financeService.deleteImportCategoryRule(rule.id)
      load()
    } catch (e) {
      console.error(e)
    }
  }

  if (loading && rules.length === 0) return <Loading />

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold text-gray-900">
            <ListFilter className="h-7 w-7 text-indigo-600" />
            Regras de importação
          </h1>
          <p className="text-gray-500">
            Mapeie trechos do campo <strong>Detalhes</strong> do extrato para categorias. As regras têm prioridade
            sobre a sugestão automática.
          </p>
        </div>
        <button
          type="button"
          onClick={openCreate}
          className="inline-flex items-center justify-center rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700"
        >
          <Plus className="mr-2 h-5 w-5" />
          Nova regra
        </button>
      </div>

      <div className="overflow-hidden rounded-xl border border-gray-100 bg-white shadow-sm">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Prioridade</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Padrão (contém)</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Categoria</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Tipo</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Status</th>
              <th className="px-4 py-3 text-right font-medium text-gray-600">Ações</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {rules.map((r) => (
              <tr key={r.id} className={!r.is_active ? 'bg-gray-50 text-gray-400' : ''}>
                <td className="whitespace-nowrap px-4 py-3 font-mono">{r.priority}</td>
                <td className="max-w-xs px-4 py-3 font-medium text-gray-800">{r.pattern}</td>
                <td className="px-4 py-3">{r.category?.name ?? `#${r.category_id}`}</td>
                <td className="px-4 py-3">{entryTypeLabel(r.entry_type)}</td>
                <td className="px-4 py-3">{r.is_active ? 'Ativa' : 'Inativa'}</td>
                <td className="whitespace-nowrap px-4 py-3 text-right">
                  <button
                    type="button"
                    onClick={() => openEdit(r)}
                    className="rounded p-1 text-gray-400 hover:bg-indigo-50 hover:text-indigo-600"
                    aria-label="Editar"
                  >
                    <Edit2 size={16} />
                  </button>
                  {r.is_active && (
                    <button
                      type="button"
                      onClick={() => handleDeactivate(r)}
                      className="ml-1 rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-600"
                      aria-label="Desativar"
                    >
                      Desativar
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {rules.length === 0 && (
          <p className="p-8 text-center text-gray-400">Nenhuma regra cadastrada ainda.</p>
        )}
      </div>

      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title={editing ? 'Editar regra' : 'Nova regra'}>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Texto no detalhe contém</label>
            <input
              type="text"
              value={form.pattern}
              onChange={(e) => setForm((f) => ({ ...f, pattern: e.target.value }))}
              className="w-full rounded-lg border border-gray-300 px-3 py-2"
              placeholder="ex.: mc don, drogaria, pix salário"
              required
              maxLength={200}
            />
            <p className="mt-1 text-xs text-gray-500">Comparação sem acento, ignora maiúsculas.</p>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Aplicar a lançamentos</label>
            <select
              value={form.entry_type}
              onChange={(e) => {
                const t = e.target.value as 'EXPENSE' | 'INCOME' | 'BOTH'
                const pool = t === 'BOTH' ? categories : categories.filter((c) => c.type === t)
                const first = pool[0]
                setForm((f) => ({
                  ...f,
                  entry_type: t,
                  category_id: first?.id ?? f.category_id,
                }))
              }}
              className="w-full rounded-lg border border-gray-300 px-3 py-2"
            >
              <option value="EXPENSE">Despesa</option>
              <option value="INCOME">Receita</option>
              <option value="BOTH">Ambos (filtra pela categoria na hora do match)</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Categoria</label>
            <select
              value={form.category_id || ''}
              onChange={(e) => setForm((f) => ({ ...f, category_id: Number(e.target.value) }))}
              className="w-full rounded-lg border border-gray-300 px-3 py-2"
              required
            >
              {categoriesForSelect().map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.type === 'EXPENSE' ? 'Despesa' : 'Receita'})
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Prioridade (menor = primeiro)</label>
            <input
              type="number"
              value={form.priority}
              onChange={(e) => setForm((f) => ({ ...f, priority: parseInt(e.target.value, 10) || 0 }))}
              className="w-full rounded-lg border border-gray-300 px-3 py-2"
            />
          </div>
          {editing && (
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))}
              />
              Regra ativa
            </label>
          )}
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={() => setModalOpen(false)}>
              Cancelar
            </Button>
            <Button type="submit">Salvar</Button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
