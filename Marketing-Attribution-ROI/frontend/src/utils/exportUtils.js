/**
 * Escapes a single cell value for safe RFC-4180 CSV export.
 */
function escapeCsvCell(value) {
  if (value === null || value === undefined) return ''
  const str = String(value)
  if (/[",\n\r]/.test(str)) {
    return `"${str.replace(/"/g, '""')}"`
  }
  return str
}

/**
 * Triggers a browser download of an array of objects as a CSV file.
 * @param {string} filename
 * @param {Array<Object>} rows
 * @param {Array<{ key: string, label: string }>} [columns]
 */
export function exportToCsv(filename, rows = [], columns) {
  if (!rows.length) return

  const resolvedColumns =
    columns ||
    Object.keys(rows[0]).map((key) => ({
      key,
      label: key,
    }))

  const headerLine = resolvedColumns.map((col) => escapeCsvCell(col.label)).join(',')
  const dataLines = rows.map((row) =>
    resolvedColumns
      .map((col) => {
        const val = typeof col.accessor === 'function' ? col.accessor(row) : row[col.key]
        return escapeCsvCell(val)
      })
      .join(',')
  )

  const csvContent = [headerLine, ...dataLines].join('\r\n')
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  downloadBlob(blob, filename.endsWith('.csv') ? filename : `${filename}.csv`)
}

/**
 * Triggers a browser download of data serialized as formatted JSON.
 * @param {string} filename
 * @param {*} data
 */
export function exportToJson(filename, data) {
  const jsonContent = JSON.stringify(data, null, 2)
  const blob = new Blob([jsonContent], { type: 'application/json;charset=utf-8;' })
  downloadBlob(blob, filename.endsWith('.json') ? filename : `${filename}.json`)
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', filename)
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

/**
 * Opens the browser print dialog for print-friendly reports.
 */
export function triggerPrint() {
  window.print()
}

