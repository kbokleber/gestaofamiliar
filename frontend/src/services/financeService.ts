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

  // Lançamentos
  async getEntries(params?: {
    start_date?: string
    end_date?: string
    category_id?: number
    type?: string
    is_paid?: boolean
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
  }
}
