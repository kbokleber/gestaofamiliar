import { useState, useEffect } from 'react'
import { TrendingUp, TrendingDown, Wallet, Calendar, PieChart, Plus, RefreshCw } from 'lucide-react'
import { financeService, FinanceSummary } from '../../services/financeService'
import Loading from '../../components/Loading'

export default function FinanceDashboard() {
  const [loading, setLoading] = useState(true)
  const [summary, setSummary] = useState<FinanceSummary | null>(null)
  const [month, setMonth] = useState(new Date().getMonth() + 1)
  const [year, setYear] = useState(new Date().getFullYear())

  useEffect(() => {
    loadSummary()
  }, [month, year])

  const loadSummary = async () => {
    setLoading(true)
    try {
      const data = await financeService.getSummary(month, year)
      setSummary(data)
    } catch (error) {
      console.error('Erro ao carregar resumo financeiro:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateRecurrences = async () => {
    try {
      await financeService.generateRecurrences()
      loadSummary()
    } catch (error) {
      console.error('Erro ao gerar recorrências:', error)
    }
  }

  if (loading && !summary) return <Loading />

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard Financeiro</h1>
          <p className="text-gray-500">Acompanhe a saúde financeira da sua família</p>
        </div>
        
        <div className="flex items-center gap-2">
          <select 
            value={month} 
            onChange={(e) => setMonth(parseInt(e.target.value))}
            className="rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm"
          >
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
          <button
            onClick={handleGenerateRecurrences}
            className="p-2 text-indigo-600 hover:bg-indigo-50 rounded-full transition-colors"
            title="Gerar recorrências do mês"
          >
            <RefreshCw className="h-5 w-5" />
          </button>
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
            <span className="text-xs font-medium text-gray-400 uppercase">Saldo Mensal</span>
          </div>
          <div className="text-2xl font-bold text-gray-900">
            {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(summary?.month_balance || 0)}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Despesas por Categoria */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
          <div className="flex items-center gap-2 mb-6">
            <PieChart className="h-5 w-5 text-gray-400" />
            <h2 className="text-lg font-semibold text-gray-900">Despesas por Categoria</h2>
          </div>
          
          <div className="space-y-4">
            {summary?.expenses_by_category.length === 0 ? (
              <p className="text-center text-gray-500 py-8">Nenhuma despesa registrada neste mês.</p>
            ) : (
              summary?.expenses_by_category.map((cat, i) => (
                <div key={i} className="group">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-gray-700">{cat.category_name}</span>
                    <span className="text-sm font-semibold text-gray-900">
                      {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(cat.amount)}
                    </span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-2">
                    <div 
                      className="h-2 rounded-full transition-all duration-500" 
                      style={{ 
                        width: `${(cat.amount / summary.month_expense) * 100}%`,
                        backgroundColor: cat.color || '#indigo-500'
                      }}
                    />
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Info/Ações Rápidas */}
        <div className="bg-indigo-600 p-6 rounded-xl shadow-lg text-white">
          <h2 className="text-xl font-bold mb-2">Controle Total</h2>
          <p className="text-indigo-100 mb-6">Cadastre suas receitas e despesas para ter uma visão clara de onde seu dinheiro está indo.</p>
          
          <div className="grid grid-cols-2 gap-4">
            <button 
              onClick={() => window.location.href = '/finance/entries'}
              className="flex flex-col items-center justify-center p-4 bg-white bg-opacity-10 hover:bg-opacity-20 rounded-lg transition-all"
            >
              <Plus className="h-6 w-6 mb-2" />
              <span className="text-sm font-medium">Novo Lançamento</span>
            </button>
            <button 
              onClick={() => window.location.href = '/finance/entries'}
              className="flex flex-col items-center justify-center p-4 bg-white bg-opacity-10 hover:bg-opacity-20 rounded-lg transition-all"
            >
              <Calendar className="h-6 w-6 mb-2" />
              <span className="text-sm font-medium">Ver Histórico</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
