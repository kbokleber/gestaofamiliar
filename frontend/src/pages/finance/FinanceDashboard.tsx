import { useState, useEffect } from 'react'
import { TrendingUp, TrendingDown, Wallet, Calendar, PieChart } from 'lucide-react'
import { financeService, FinanceSummary } from '../../services/financeService'
import Loading from '../../components/Loading'

type CategorySlice = FinanceSummary['expenses_by_category'][number]

const currencyFormatter = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })

function PieCategoryCard({
  title,
  items,
  emptyMessage,
}: {
  title: string
  items: CategorySlice[]
  emptyMessage: string
}) {
  const total = items.reduce((sum, item) => sum + Number(item.amount), 0)

  const gradient = items.length
    ? `conic-gradient(${items
        .reduce(
          (acc, item, index) => {
            const value = Number(item.amount)
            const percentage = total > 0 ? (value / total) * 100 : 0
            const start = acc.current
            const end = start + percentage

            acc.current = end
            acc.parts.push(`${item.color || ['#22c55e', '#ef4444', '#6366f1', '#f59e0b'][index % 4]} ${start}% ${end}%`)

            return acc
          },
          { current: 0, parts: [] as string[] }
        )
        .parts.join(', ')})`
    : 'conic-gradient(#e5e7eb 0% 100%)'

  return (
    <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
      <div className="flex items-center gap-2 mb-6">
        <PieChart className="h-5 w-5 text-gray-400" />
        <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
      </div>

      {items.length === 0 ? (
        <p className="text-center text-gray-500 py-8">{emptyMessage}</p>
      ) : (
        <div className="flex flex-col xl:flex-row gap-6 items-center">
          <div className="relative flex items-center justify-center">
            <div
              className="h-52 w-52 rounded-full shadow-inner"
              style={{ background: gradient }}
              aria-hidden="true"
            />
            <div className="absolute flex h-28 w-28 flex-col items-center justify-center rounded-full bg-white shadow-sm">
              <span className="text-xs font-medium uppercase tracking-wide text-gray-400">Total</span>
              <span className="text-sm font-bold text-gray-900 text-center px-2">
                {currencyFormatter.format(total)}
              </span>
            </div>
          </div>

          <div className="w-full space-y-3">
            {items.map((item, index) => {
              const value = Number(item.amount)
              const percentage = total > 0 ? (value / total) * 100 : 0
              const color = item.color || ['#22c55e', '#ef4444', '#6366f1', '#f59e0b'][index % 4]

              return (
                <div key={`${item.category_name}-${index}`} className="flex items-start justify-between gap-4">
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="mt-1 h-3 w-3 rounded-full shrink-0" style={{ backgroundColor: color }} />
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-gray-800 truncate">{item.category_name}</p>
                      <p className="text-xs text-gray-500">{percentage.toFixed(1)}%</p>
                    </div>
                  </div>
                  <span className="text-sm font-semibold text-gray-900 whitespace-nowrap">
                    {currencyFormatter.format(value)}
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

export default function FinanceDashboard() {
  const [loading, setLoading] = useState(true)
  const [summary, setSummary] = useState<FinanceSummary | null>(null)
  const [month, setMonth] = useState<number | null>(new Date().getMonth() + 1)
  const [year, setYear] = useState(new Date().getFullYear())
  const [expenseThreshold, setExpenseThreshold] = useState<number>(() => {
    const saved = localStorage.getItem('finance-expense-threshold')
    return saved ? Number(saved) || 0 : 0
  })

  useEffect(() => {
    loadSummary()
  }, [month, year])

  useEffect(() => {
    localStorage.setItem('finance-expense-threshold', String(expenseThreshold))
  }, [expenseThreshold])

  const loadSummary = async () => {
    setLoading(true)
    try {
      const data = await financeService.getSummary(month === null ? undefined : month, year)
      setSummary(data)
    } catch (error) {
      console.error('Erro ao carregar resumo financeiro:', error)
    } finally {
      setLoading(false)
    }
  }


  if (loading && !summary) return <Loading />

  const monthlyData = summary?.monthly_data || []
  const chartMax = monthlyData.length
    ? Math.max(
        ...monthlyData.map((d) => Math.max(Number(d.income), Number(d.expense))),
        expenseThreshold,
        1
      )
    : 1
  const thresholdHeight = expenseThreshold > 0 ? (expenseThreshold / chartMax) * 100 : null

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard Financeiro</h1>
          <p className="text-gray-500">Acompanhe a saúde financeira da sua família</p>
        </div>
        
        <div className="flex items-center gap-2">
          <select 
            value={month === null ? 'all' : month} 
            onChange={(e) => setMonth(e.target.value === 'all' ? null : parseInt(e.target.value))}
            className="rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm"
          >
            <option value="all">O ano todo</option>
            {[...Array(12)].map((_, i) => (
              <option key={i+1} value={i+1}>
                {new Intl.DateTimeFormat('pt-BR', { month: 'long' }).format(new Date(2000, i))}
              </option>
            ))}
          </select>
          <select 
            value={year} 
            onChange={(e) => setYear(parseInt(e.target.value))}
            className="rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm"
          >
            {[year - 1, year, year + 1].map(y => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
          <div className="flex items-center justify-between mb-4">
            <div className="p-2 bg-green-100 text-green-600 rounded-lg">
              <TrendingUp className="h-6 w-6" />
            </div>
            <span className="text-xs font-medium text-gray-400 uppercase">Receitas</span>
          </div>
          <div className="text-2xl font-bold text-gray-900">
            {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(summary?.month_income || 0)}
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
          <div className="flex items-center justify-between mb-4">
            <div className="p-2 bg-red-100 text-red-600 rounded-lg">
              <TrendingDown className="h-6 w-6" />
            </div>
            <span className="text-xs font-medium text-gray-400 uppercase">Despesas</span>
          </div>
          <div className="text-2xl font-bold text-gray-900">
            {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(summary?.month_expense || 0)}
          </div>
        </div>

        <div className={`bg-white p-6 rounded-xl shadow-sm border border-gray-100 ${ (summary?.month_balance || 0) >= 0 ? 'border-l-4 border-l-green-500' : 'border-l-4 border-l-red-500'}`}>
          <div className="flex items-center justify-between mb-4">
            <div className={`p-2 rounded-lg ${(summary?.month_balance || 0) >= 0 ? 'bg-indigo-100 text-indigo-600' : 'bg-orange-100 text-orange-600'}`}>
              <Wallet className="h-6 w-6" />
            </div>
            <span className="text-xs font-medium text-gray-400 uppercase">{month === null ? 'Saldo Anual' : 'Saldo Mensal'}</span>
          </div>
          <div className="text-2xl font-bold text-gray-900">
            {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(summary?.month_balance || 0)}
          </div>
          <div className={`text-xs mt-2 ${ (summary?.month_balance || 0) >= (summary?.previous_month_balance || 0) ? 'text-green-500' : 'text-red-500'}`}>
            {(summary?.month_balance || 0) >= (summary?.previous_month_balance || 0) ? '↑' : '↓'} 
            {Math.abs(((summary?.month_balance || 0) - (summary?.previous_month_balance || 0)) / (Math.abs(summary?.previous_month_balance || 1) || 1) * 100).toFixed(1)}% vs {month === null ? 'ano anterior' : 'mês ant.'}
          </div>
        </div>
      </div>

      {summary?.monthly_data && (
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
          <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex items-center gap-2">
              <Calendar className="h-5 w-5 text-gray-400" />
              <h2 className="text-lg font-semibold text-gray-900">Evolução Mensal ({year})</h2>
            </div>

            <div className="flex flex-col sm:flex-row sm:items-center gap-3">
              <label className="text-sm font-medium text-gray-600">Limiar de despesas</label>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={expenseThreshold}
                  onChange={(e) => setExpenseThreshold(Math.max(0, Number(e.target.value) || 0))}
                  className="w-40 rounded-lg border-gray-300 shadow-sm focus:border-amber-500 focus:ring-amber-500 text-sm"
                  placeholder="0,00"
                />
                <span className="text-xs text-gray-500 whitespace-nowrap">
                  {currencyFormatter.format(expenseThreshold)}
                </span>
              </div>
            </div>
          </div>
          
          <div className="relative h-64 w-full px-2">
            <div className="pointer-events-none absolute bottom-6 left-2 right-2 h-48">
              {thresholdHeight !== null && (
                <div
                  className="absolute left-0 right-0 z-10 border-t-2 border-dashed border-amber-400"
                  style={{ bottom: `${thresholdHeight}%` }}
                >
                  <span className="absolute -top-5 right-0 rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-700">
                    Limiar: {currencyFormatter.format(expenseThreshold)}
                  </span>
                </div>
              )}
            </div>

            <div className="h-full w-full flex items-end gap-1 sm:gap-4 pb-6">
              {monthlyData.map((m, i) => {
                const incomeHeight = (Number(m.income) / chartMax) * 100
                const expenseHeight = (Number(m.expense) / chartMax) * 100
              
                return (
                  <div key={i} className="flex-1 flex flex-col items-center gap-2 group relative">
                    <div className="w-full flex items-end justify-center gap-0.5 sm:gap-1 h-48 relative pt-6">
                      <div className="flex flex-col items-center flex-1 h-full justify-end">
                        {Number(m.income) > 0 && (
                          <span className="text-[8px] sm:text-[10px] text-green-600 font-bold mb-0.5 whitespace-nowrap">
                            {Number(m.income) >= 1000 ? `${(Number(m.income)/1000).toFixed(1)}k` : Math.round(Number(m.income))}
                          </span>
                        )}
                        <div 
                          className="w-2 sm:w-4 bg-green-400 rounded-t-sm transition-all duration-500 group-hover:bg-green-500"
                          style={{ height: `${incomeHeight}%` }}
                          title={`Receita: ${new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(m.income))}`}
                        />
                      </div>
                      <div className="flex flex-col items-center flex-1 h-full justify-end">
                        {Number(m.expense) > 0 && (
                          <span className="text-[8px] sm:text-[10px] text-red-600 font-bold mb-0.5 whitespace-nowrap">
                            {Number(m.expense) >= 1000 ? `${(Number(m.expense)/1000).toFixed(1)}k` : Math.round(Number(m.expense))}
                          </span>
                        )}
                        <div 
                          className="w-2 sm:w-4 bg-red-400 rounded-t-sm transition-all duration-500 group-hover:bg-red-500"
                          style={{ height: `${expenseHeight}%` }}
                          title={`Despesa: ${new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(m.expense))}`}
                        />
                      </div>
                    </div>
                    <span className="text-[10px] sm:text-xs text-gray-400 font-medium">
                      {new Intl.DateTimeFormat('pt-BR', { month: 'short' }).format(new Date(2000, m.month - 1)).replace('.', '')}
                    </span>
                    
                    {/* Tooltip */}
                    <div className="absolute bottom-full mb-2 bg-gray-900 text-white text-[10px] p-2 rounded opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-10 whitespace-nowrap shadow-xl">
                      <div className="text-green-400">R: {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(m.income))}</div>
                      <div className="text-red-400">D: {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(m.expense))}</div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
          <div className="flex justify-center gap-6 mt-6 border-t pt-4">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-green-400 rounded-sm" />
              <span className="text-xs text-gray-500 font-medium">Receitas</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-red-400 rounded-sm" />
              <span className="text-xs text-gray-500 font-medium">Despesas</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-0 border-t-2 border-dashed border-amber-400" />
              <span className="text-xs text-gray-500 font-medium">Limiar</span>
            </div>
          </div>
        </div>
      )}

      {month === null ? (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <PieCategoryCard
            title="Despesas por Categoria"
            items={summary?.expenses_by_category || []}
            emptyMessage="Nenhuma despesa paga registrada neste ano."
          />
          <PieCategoryCard
            title="Receitas por Categoria"
            items={summary?.incomes_by_category || []}
            emptyMessage="Nenhuma receita paga registrada neste ano."
          />
        </div>
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
            <div className="flex items-center gap-2 mb-6">
              <PieChart className="h-5 w-5 text-gray-400" />
              <h2 className="text-lg font-semibold text-gray-900">Despesas por Categoria</h2>
            </div>
            
            <div className="space-y-4">
              {summary?.expenses_by_category.length === 0 ? (
                <p className="text-center text-gray-500 py-8">Nenhuma despesa paga registrada neste mês.</p>
              ) : (
                summary?.expenses_by_category.map((cat, i) => (
                  <div key={i} className="group">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-gray-700">{cat.category_name}</span>
                      <span className="text-sm font-semibold text-gray-900">
                        {currencyFormatter.format(Number(cat.amount))}
                      </span>
                    </div>
                    <div className="w-full bg-gray-100 rounded-full h-2">
                      <div 
                        className="h-2 rounded-full transition-all duration-500" 
                        style={{ 
                          width: `${summary?.month_expense ? (Number(cat.amount) / Number(summary.month_expense)) * 100 : 0}%`,
                          backgroundColor: cat.color || '#ef4444'
                        }}
                      />
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
            <div className="flex items-center gap-2 mb-6">
              <PieChart className="h-5 w-5 text-gray-400" />
              <h2 className="text-lg font-semibold text-gray-900">Receitas por Categoria</h2>
            </div>
            
            <div className="space-y-4">
              {summary?.incomes_by_category.length === 0 ? (
                <p className="text-center text-gray-500 py-8">Nenhuma receita paga registrada neste mês.</p>
              ) : (
                summary?.incomes_by_category.map((cat, i) => (
                  <div key={i} className="group">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-gray-700">{cat.category_name}</span>
                      <span className="text-sm font-semibold text-gray-900">
                        {currencyFormatter.format(Number(cat.amount))}
                      </span>
                    </div>
                    <div className="w-full bg-gray-100 rounded-full h-2">
                      <div 
                        className="h-2 rounded-full transition-all duration-500" 
                        style={{ 
                          width: `${summary?.month_income ? (Number(cat.amount) / Number(summary.month_income)) * 100 : 0}%`,
                          backgroundColor: cat.color || '#22c55e'
                        }}
                      />
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
