import api from '../lib/api'

export interface Category {
  id: number
  name: string
  icon: string
  color: string
  type: 'INCOME' | 'EXPENSE'
  is_active: boolean
}

export interface Entry {
  id: number
  description: string
  amount: number
  date: string
  type: 'INCOME' | 'EXPENSE'
  category_id?: number
  category?: Category
  payment_method?: string
  is_paid: boolean
  notes?: string
  documents?: string
}

export interface Recurrence {
  id: number
  description: string
  amount: number
  type: 'INCOME' | 'EXPENSE'
  category_id?: number
  category?: Category
  day_of_month: number
  start_date?: string
  end_date?: string
  is_active: boolean
}

export interface FinanceSummary {
  month_income: number
  month_expense: number
  month_balance: number
  previous_month_balance: number
  expenses_by_category: {
    category_name: string
    amount: number
    color: string
  }[]
  incomes_by_category: {
    category_name: string
    amount: number
    color: string
  }[]
  monthly_data?: {
    month: number
    income: number
    expense: number
  }[]
}

export interface ImportCategoryRule {
  id: number
  family_id: number
  category_id: number
  pattern: string
  entry_type: 'EXPENSE' | 'INCOME' | 'BOTH'
  priority: number
  is_active: boolean
  created_at: string
  updated_at: string
  category?: Category
}

export const financeService = {
  // Categorias
  async getCategories() {
    const response = await api.get<Category[]>('/finance/categories')
    return response.data
  },
  async createCategory(data: Partial<Category>) {
    const response = await api.post<Category>('/finance/categories', data)
    return response.data
  },
  async updateCategory(id: number, data: Partial<Category>) {
    const response = await api.put<Category>(`/finance/categories/${id}`, data)
    return response.data
  },
  async deleteCategory(id: number) {
    await api.delete(`/finance/categories/${id}`)
  },

  async getImportCategoryRules() {
    const response = await api.get<ImportCategoryRule[]>('/finance/import-category-rules')
    return response.data
  },
  async createImportCategoryRule(data: {
    pattern: string
    category_id: number
    entry_type: string
    priority?: number
    is_active?: boolean
  }) {
    const response = await api.post<ImportCategoryRule>('/finance/import-category-rules', data)
    return response.data
  },
  async updateImportCategoryRule(
    id: number,
    data: Partial<{
      pattern: string
      category_id: number
      entry_type: string
      priority: number
      is_active: boolean
    }>
  ) {
    const response = await api.put<ImportCategoryRule>(`/finance/import-category-rules/${id}`, data)
    return response.data
  },
  async deleteImportCategoryRule(id: number) {
    await api.delete(`/finance/import-category-rules/${id}`)
  },

  // Lançamentos
  async getEntries(params?: {
    start_date?: string
    end_date?: string
    category_id?: number
    /** Apenas lançamentos sem categoria (no servidor ignora category_id). */
    uncategorized_only?: boolean
    type?: string
    is_paid?: boolean
    /** Texto parcial na descrição (case-insensitive no servidor). */
    description_contains?: string
  }) {
    const response = await api.get<Entry[]>('/finance/entries', { params })
    return response.data
  },
  async createEntry(data: Partial<Entry>) {
    const response = await api.post<Entry>('/finance/entries', data)
    return response.data
  },
  async updateEntry(id: number, data: Partial<Entry>) {
    const response = await api.put<Entry>(`/finance/entries/${id}`, data)
    return response.data
  },
  async deleteEntry(id: number) {
    await api.delete(`/finance/entries/${id}`)
  },
  async uploadReceipt(file: File) {
    const formData = new FormData()
    formData.append('file', file)
    const response = await api.post<Entry>('/finance/upload-receipt', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    return response.data
  },

  // Recorrências
  async getRecurrences() {
    const response = await api.get<Recurrence[]>('/finance/recurrences')
    return response.data
  },
  async createRecurrence(data: Partial<Recurrence>) {
    const response = await api.post<Recurrence>('/finance/recurrences', data)
    return response.data
  },
  async updateRecurrence(id: number, data: Partial<Recurrence>) {
    const response = await api.put<Recurrence>(`/finance/recurrences/${id}`, data)
    return response.data
  },
  async deleteRecurrence(id: number) {
    await api.delete(`/finance/recurrences/${id}`)
  },
  async generateRecurrences(month?: number, year?: number) {
    const response = await api.post<{message: string}>('/finance/generate-recurrences', null, { params: { month, year } })
    return response.data
  },

  // Resumo
  async getSummary(month?: number, year?: number) {
    const response = await api.get<FinanceSummary>('/finance/summary', { params: { month, year } })
    return response.data
  },

  async suggestImportCategories(items: { description: string; type: string }[]) {
    const response = await api.post<{
      suggestions: { category_id: number | null; confidence: string | null }[]
    }>('/finance/suggest-import-categories', { items })
    return response.data.suggestions
  },

  async bulkCreateEntries(
    entries: {
      description: string
      amount: number
      date: string
      type: string
      category_id?: number
      payment_method?: string
      is_paid?: boolean
    }[]
  ) {
    const response = await api.post<{ created: number; errors: { index: number; detail: string }[] }>(
      '/finance/entries/bulk',
      { entries }
    )
    return response.data
  },

  async bulkDeleteEntries(entryIds: number[]) {
    const response = await api.post<{ deleted: number }>('/finance/entries/bulk-delete', {
      entry_ids: entryIds,
    })
    return response.data
  },

  async bulkUpdateEntryCategory(entryIds: number[], categoryId: number | null) {
    const response = await api.patch<{ updated: number; skipped: number }>('/finance/entries/bulk-category', {
      entry_ids: entryIds,
      category_id: categoryId,
    })
    return response.data
  },
}
