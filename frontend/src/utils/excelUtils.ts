import * as XLSX from 'xlsx'

export interface ExcelColumn {
  header: string
  key: string
  width?: number
}

export function exportToExcel(
  data: any[],
  columns: ExcelColumn[],
  filename: string
) {
  if (!data || data.length === 0) {
    alert('Não há dados para exportar')
    return
  }

  // Preparar dados para o Excel
  const excelData = data.map(item => {
    const row: any = {}
    columns.forEach(col => {
      row[col.header] = item[col.key] ?? ''
    })
    return row
  })

  // Criar workbook
  const worksheet = XLSX.utils.json_to_sheet(excelData)
  const workbook = XLSX.utils.book_new()

  // Ajustar largura das colunas
  const colWidths = columns.map(col => ({
    wch: col.width || 15
  }))
  worksheet['!cols'] = colWidths

  // Adicionar worksheet ao workbook
  XLSX.utils.book_append_sheet(workbook, worksheet, 'Dados')

  // Gerar arquivo Excel
  XLSX.writeFile(workbook, `${filename}.xlsx`)
}

