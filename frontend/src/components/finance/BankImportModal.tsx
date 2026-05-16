import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { X, Upload, Loader2, Trash2 } from 'lucide-react'
import type { Category } from '../../services/financeService'
import { financeService } from '../../services/financeService'
import { readExcelFirstSheetAsMatrix } from '../../utils/excelUtils'
import { parseBancoDoBrasilExtrato } from '../../utils/bankImport/bancoDoBrasilParser'

function newRowId() {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) return crypto.randomUUID()
  return `r-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
}

export interface BankImportRow {
  id: string
  date: string
  description: string
  amount: number
  type: 'INCOME' | 'EXPENSE'
  category_id: string
  confidence: 'high' | 'low' | null
}

interface BankImportModalProps {
  isOpen: boolean
  onClose: () => void
  categories: Category[]
  onImported: () => void
}

export default function BankImportModal({
  isOpen,
  onClose,
  categories,
  onImported,
}: BankImportModalProps) {
  const navigate = useNavigate()
  const fileRef = useRef<HTMLInputElement>(null)
  const [rows, setRows] = useState<BankImportRow[]>([])
  const [loadingFile, setLoadingFile] = useState(false)
  const [suggesting, setSuggesting] = useState(false)
  const [saving, setSaving] = useState(false)
  const [parseError, setParseError] = useState<string | null>(null)

  const reset = () => {
    setRows([])
    setParseError(null)
    setLoadingFile(false)
    setSuggesting(false)
    setSaving(false)
  }

  const handleClose = () => {
    reset()
    onClose()
  }

  if (!isOpen) return null

  const categoryOptionsFor = (type: 'INCOME' | 'EXPENSE') =>
    categories.filter((c) => c.type === type && c.is_active)

  const handleFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return

    setLoadingFile(true)
    setParseError(null)
    setRows([])
    try {
      const matrix = await readExcelFirstSheetAsMatrix(file)
      const parsed = parseBancoDoBrasilExtrato(matrix)
      if (!parsed.length) {
        setParseError(
          'Não foi possível ler o extrato. Use o arquivo Excel exportado pelo BB (colunas Data, Detalhes e Valor ou Crédito/Débito).'
        )
        return
      }
      const initial: BankImportRow[] = parsed.map((p) => ({
        id: newRowId(),
        date: p.date,
        description: p.description,
        amount: p.amount,
        type: p.type,
        category_id: '',
        confidence: null,
      }))
      setRows(initial)
      setSuggesting(true)
      try {
        const suggestions = await financeService.suggestImportCategories(
          initial.map((r) => ({ description: r.description, type: r.type }))
        )
        setRows((prev) =>
          prev.map((r, i) => {
            const s = suggestions[i]
            if (!s?.category_id) return { ...r, category_id: '', confidence: null }
            return {
              ...r,
              category_id: String(s.category_id),
              confidence: (s.confidence as 'high' | 'low') || null,
            }
          })
        )
      } catch (err) {
        console.error(err)
        setParseError(
          'Linhas carregadas, mas a sugestão de categorias falhou. Você pode escolher manualmente.'
        )
      } finally {
        setSuggesting(false)
      }
    } catch (err) {
      console.error(err)
      setParseError('Erro ao abrir o arquivo. Tente .xlsx ou .xls exportado pelo BB.')
    } finally {
      setLoadingFile(false)
    }
  }

  const removeRow = (id: string) => {
    setRows((prev) => prev.filter((r) => r.id !== id))
  }

  const handleSave = async () => {
    if (!rows.length) return
    setSaving(true)
    try {
      const entries = rows.map((r) => ({
        description: r.description,
        amount: r.amount,
        date: r.date,
        type: r.type,
        category_id: r.category_id ? parseInt(r.category_id, 10) : undefined,
        payment_method: 'Extrato BB',
        is_paid: true,
      }))
      const result = await financeService.bulkCreateEntries(entries)
      if (result.errors.length) {
        const msg = result.errors
          .slice(0, 5)
          .map((e) => `Linha ${e.index + 1}: ${e.detail}`)
          .join('\n')
        alert(
          `Importados ${result.created} lançamento(s). ${result.errors.length} erro(s).\n${msg}${
            result.errors.length > 5 ? '\n...' : ''
          }`
        )
      } else {
        alert(`${result.created} lançamento(s) importados com sucesso.`)
      }
      onImported()
      handleClose()
    } catch (err) {
      console.error(err)
      alert('Erro ao salvar lançamentos. Verifique os dados e tente novamente.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 overflow-y-auto"
      role="dialog"
      aria-modal="true"
      aria-labelledby="bank-import-title"
    >
      <div className="flex min-h-screen items-center justify-center px-4 py-8 sm:p-6">
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75" onClick={handleClose} aria-hidden="true" />
        <div className="relative z-10 flex max-h-[90vh] w-full max-w-5xl flex-col overflow-hidden rounded-lg bg-white shadow-xl">
          <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3 sm:px-6">
            <h2 id="bank-import-title" className="text-lg font-semibold text-gray-900">
              Importar extrato Banco do Brasil
            </h2>
            <button
              type="button"
              onClick={handleClose}
              className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
              aria-label="Fechar"
            >
              <X className="h-6 w-6" />
            </button>
          </div>

          <div className="space-y-3 border-b border-gray-100 px-4 py-3 sm:px-6">
            <input ref={fileRef} type="file" accept=".xlsx,.xls" className="hidden" onChange={handleFile} />
            <button
              type="button"
              onClick={() => fileRef.current?.click()}
              disabled={loadingFile || saving}
              className="inline-flex items-center rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 disabled:opacity-50"
            >
              {loadingFile ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Upload className="mr-2 h-4 w-4" />
              )}
              {loadingFile ? 'Lendo...' : 'Selecionar arquivo Excel'}
            </button>
            {suggesting && (
              <p className="flex items-center text-sm text-indigo-600">
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Sugerindo categorias...
              </p>
            )}
            {parseError && <p className="text-sm text-amber-800">{parseError}</p>}
            <button
              type="button"
              onClick={() => {
                onClose()
                navigate('/finance/import-category-rules')
              }}
              className="text-sm text-indigo-600 underline hover:text-indigo-800"
            >
              Gerenciar regras de importação (Detalhes → categoria)
            </button>
          </div>

          {rows.length > 0 && (
            <div className="flex min-h-0 flex-1 flex-col">
              <div className="overflow-auto px-2 pb-2 sm:px-4">
                <table className="min-w-full divide-y divide-gray-200 text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="w-10 px-1 py-2 text-center font-medium text-gray-600" aria-label="Ações" />
                      <th className="px-2 py-2 text-left font-medium text-gray-600">Data</th>
                      <th className="px-2 py-2 text-left font-medium text-gray-600">Detalhes</th>
                      <th className="px-2 py-2 text-right font-medium text-gray-600">Valor</th>
                      <th className="px-2 py-2 text-left font-medium text-gray-600">Tipo</th>
                      <th className="px-2 py-2 text-left font-medium text-gray-600">Categoria</th>
                      <th className="px-2 py-2 text-left font-medium text-gray-600">Conf.</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 bg-white">
                    {rows.map((row, idx) => (
                      <tr key={row.id}>
                        <td className="px-1 py-1 text-center align-middle">
                          <button
                            type="button"
                            onClick={() => removeRow(row.id)}
                            disabled={suggesting || saving}
                            className="rounded p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-600 disabled:opacity-40"
                            title="Não importar esta linha"
                            aria-label="Remover linha da importação"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </td>
                        <td className="whitespace-nowrap px-2 py-1">
                          <input
                            type="date"
                            value={row.date}
                            onChange={(e) => {
                              const v = e.target.value
                              setRows((prev) => prev.map((r, i) => (i === idx ? { ...r, date: v } : r)))
                            }}
                            className="w-[9.5rem] rounded border-gray-300 text-xs"
                          />
                        </td>
                        <td className="max-w-[220px] px-2 py-1">
                          <input
                            type="text"
                            value={row.description}
                            onChange={(e) => {
                              const v = e.target.value
                              setRows((prev) => prev.map((r, i) => (i === idx ? { ...r, description: v } : r)))
                            }}
                            className="w-full rounded border-gray-300 text-xs"
                          />
                        </td>
                        <td className="whitespace-nowrap px-2 py-1 text-right">
                          <input
                            type="number"
                            step="0.01"
                            min="0"
                            value={row.amount}
                            onChange={(e) => {
                              const v = parseFloat(e.target.value)
                              setRows((prev) =>
                                prev.map((r, i) => (i === idx ? { ...r, amount: Number.isNaN(v) ? 0 : v } : r))
                              )
                            }}
                            className="w-24 rounded border-gray-300 text-right text-xs"
                          />
                        </td>
                        <td className="whitespace-nowrap px-2 py-1">
                          <select
                            value={row.type}
                            onChange={(e) => {
                              const v = e.target.value as 'INCOME' | 'EXPENSE'
                              setRows((prev) =>
                                prev.map((r, i) =>
                                  i === idx ? { ...r, type: v, category_id: '', confidence: null } : r
                                )
                              )
                            }}
                            className="rounded border-gray-300 text-xs"
                          >
                            <option value="EXPENSE">Despesa</option>
                            <option value="INCOME">Receita</option>
                          </select>
                        </td>
                        <td className="min-w-[140px] px-2 py-1">
                          <select
                            value={row.category_id}
                            onChange={(e) => {
                              const v = e.target.value
                              setRows((prev) =>
                                prev.map((r, i) => (i === idx ? { ...r, category_id: v, confidence: null } : r))
                              )
                            }}
                            className="w-full max-w-[200px] rounded border-gray-300 text-xs"
                          >
                            <option value="">—</option>
                            {categoryOptionsFor(row.type).map((c) => (
                              <option key={c.id} value={c.id}>
                                {c.name}
                              </option>
                            ))}
                          </select>
                        </td>
                        <td className="whitespace-nowrap px-2 py-1 text-xs text-gray-500">
                          {row.confidence === 'high' && 'Alta'}
                          {row.confidence === 'low' && 'Baixa'}
                          {!row.confidence && '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="flex justify-end gap-2 border-t border-gray-200 px-4 py-3 sm:px-6">
                <button
                  type="button"
                  onClick={handleClose}
                  className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  onClick={handleSave}
                  disabled={saving || suggesting || rows.length === 0}
                  className="inline-flex items-center rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
                >
                  {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Salvar {rows.length} lançamento(s)
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
