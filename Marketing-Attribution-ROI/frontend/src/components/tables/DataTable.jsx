import { useMemo, useState } from 'react'
import {
  ArrowDown,
  ArrowUp,
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'
import { cn } from '../../utils/formatters'
import { EmptyState } from '../common/EmptyState'
import { LoadingState } from '../common/LoadingState'

/**
 * Reusable enterprise data table with client-side sorting, pagination,
 * row click support, and loading/empty states.
 */
export function DataTable({
  columns = [],
  data = [],
  rowKey = 'id',
  pageSize: initialPageSize = 10,
  loading = false,
  emptyTitle = 'No matching records',
  emptyDescription = 'Try adjusting your search or filter criteria.',
  onResetFilters,
  onRowClick,
  rowClassName,
  className = '',
}) {
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' })
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(initialPageSize)

  const handleSort = (column) => {
    if (!column.sortable) return
    setPage(1)
    setSortConfig((prev) => {
      if (prev.key !== column.key) {
        return { key: column.key, direction: 'asc' }
      }
      if (prev.direction === 'asc') {
        return { key: column.key, direction: 'desc' }
      }
      return { key: null, direction: 'asc' }
    })
  }

  const sortedData = useMemo(() => {
    if (!sortConfig.key) return data
    const column = columns.find((col) => col.key === sortConfig.key)
    const dir = sortConfig.direction === 'asc' ? 1 : -1

    return [...data].sort((a, b) => {
      const valA = column?.sortValue ? column.sortValue(a) : a[sortConfig.key]
      const valB = column?.sortValue ? column.sortValue(b) : b[sortConfig.key]

      if (valA === valB) return 0
      if (valA === null || valA === undefined) return 1
      if (valB === null || valB === undefined) return -1

      if (typeof valA === 'number' && typeof valB === 'number') {
        return (valA - valB) * dir
      }
      return String(valA).localeCompare(String(valB)) * dir
    })
  }, [data, columns, sortConfig])

  const totalPages = Math.max(1, Math.ceil(sortedData.length / pageSize))
  const safePage = Math.min(page, totalPages)
  const startIndex = (safePage - 1) * pageSize
  const paginatedRows = sortedData.slice(startIndex, startIndex + pageSize)

  if (loading) {
    return <LoadingState />
  }

  if (data.length === 0) {
    return (
      <EmptyState
        title={emptyTitle}
        description={emptyDescription}
        actionLabel={onResetFilters ? 'Clear Filters' : undefined}
        onAction={onResetFilters}
      />
    )
  }

  return (
    <div
      className={cn(
        'overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xs',
        className
      )}
    >
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
          <thead className="bg-slate-50/90">
            <tr>
              {columns.map((column) => {
                const isSorted = sortConfig.key === column.key
                return (
                  <th
                    key={column.key}
                    scope="col"
                    className={cn(
                      'px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500 whitespace-nowrap',
                      column.align === 'right' && 'text-right',
                      column.align === 'center' && 'text-center',
                      column.headerClassName
                    )}
                  >
                    {column.sortable ? (
                      <button
                        type="button"
                        onClick={() => handleSort(column)}
                        className={cn(
                          'inline-flex items-center gap-1.5 hover:text-slate-900 cursor-pointer',
                          column.align === 'right' && 'flex-row-reverse'
                        )}
                      >
                        <span>{column.label}</span>
                        {isSorted ? (
                          sortConfig.direction === 'asc' ? (
                            <ArrowUp className="h-3.5 w-3.5 text-blue-600" />
                          ) : (
                            <ArrowDown className="h-3.5 w-3.5 text-blue-600" />
                          )
                        ) : (
                          <ArrowUpDown className="h-3.5 w-3.5 text-slate-400" />
                        )}
                      </button>
                    ) : (
                      column.label
                    )}
                  </th>
                )
              })}
            </tr>
          </thead>

          <tbody className="divide-y divide-slate-100 bg-white">
            {paginatedRows.map((row, rowIndex) => {
              const keyValue =
                typeof rowKey === 'function'
                  ? rowKey(row)
                  : row[rowKey] ?? `${safePage}-${rowIndex}`
              const customRowClass =
                typeof rowClassName === 'function' ? rowClassName(row) : ''

              return (
                <tr
                  key={keyValue}
                  onClick={onRowClick ? () => onRowClick(row) : undefined}
                  className={cn(
                    'transition-colors hover:bg-slate-50/80',
                    onRowClick && 'cursor-pointer',
                    customRowClass
                  )}
                >
                  {columns.map((column) => (
                    <td
                      key={column.key}
                      className={cn(
                        'px-4 py-3 text-slate-700 align-middle',
                        column.align === 'right' && 'text-right tabular-nums',
                        column.align === 'center' && 'text-center',
                        column.cellClassName
                      )}
                    >
                      {column.render
                        ? column.render(row)
                        : row[column.key] ?? '—'}
                    </td>
                  ))}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <div className="flex flex-col gap-3 border-t border-slate-200 bg-slate-50/60 px-4 py-3 sm:flex-row sm:items-center sm:justify-between no-print">
        <div className="flex items-center gap-2 text-xs text-slate-600">
          <span>
            Showing{' '}
            <strong className="font-semibold text-slate-900">
              {startIndex + 1}
            </strong>
            –
            <strong className="font-semibold text-slate-900">
              {Math.min(startIndex + pageSize, sortedData.length)}
            </strong>{' '}
            of{' '}
            <strong className="font-semibold text-slate-900">
              {sortedData.length}
            </strong>{' '}
            records
          </span>
        </div>

        <div className="flex items-center gap-3">
          <label className="flex items-center gap-1.5 text-xs text-slate-600">
            <span>Rows</span>
            <select
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value))
                setPage(1)
              }}
              className="h-7 rounded-md border border-slate-200 bg-white px-2 text-xs text-slate-700 focus:border-blue-500 focus:outline-none cursor-pointer"
            >
              {[5, 10, 20, 50].map((size) => (
                <option key={size} value={size}>
                  {size}
                </option>
              ))}
            </select>
          </label>

          <div className="flex items-center gap-1">
            <button
              type="button"
              disabled={safePage <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              aria-label="Previous page"
              className="inline-flex h-7 w-7 items-center justify-center rounded-md border border-slate-200 bg-white text-slate-600 hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <span className="px-2 text-xs font-medium text-slate-700 tabular-nums">
              Page {safePage} of {totalPages}
            </span>
            <button
              type="button"
              disabled={safePage >= totalPages}
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              aria-label="Next page"
              className="inline-flex h-7 w-7 items-center justify-center rounded-md border border-slate-200 bg-white text-slate-600 hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

