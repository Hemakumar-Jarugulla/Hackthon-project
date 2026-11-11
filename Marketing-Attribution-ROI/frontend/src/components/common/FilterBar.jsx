import { RotateCcw, Search } from 'lucide-react'
import { cn } from '../../utils/formatters'
import { Button } from './Button'

/**
 * Reusable search & filter toolbar for tables and analytics views.
 */
export function FilterBar({
  searchValue = '',
  onSearchChange,
  searchPlaceholder = 'Search...',
  filters = [],
  onReset,
  actions,
  className = '',
}) {
  const hasActiveFilter =
    Boolean(searchValue) ||
    filters.some((f) => f.value && f.value !== 'all')

  return (
    <div
      className={cn(
        'flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-3.5 shadow-xs lg:flex-row lg:items-center lg:justify-between no-print',
        className
      )}
    >
      <div className="flex flex-1 flex-wrap items-center gap-2.5">
        {onSearchChange && (
          <div className="relative min-w-[220px] flex-1 sm:max-w-xs">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              type="search"
              value={searchValue}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder={searchPlaceholder}
              className="h-9 w-full rounded-lg border border-slate-200 bg-slate-50/70 pl-9 pr-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            />
          </div>
        )}

        {filters.map((filter) => (
          <div key={filter.id} className="flex items-center gap-1.5">
            {filter.label && (
              <label
                htmlFor={`filter-${filter.id}`}
                className="text-xs font-medium text-slate-500 whitespace-nowrap"
              >
                {filter.label}
              </label>
            )}
            <select
              id={`filter-${filter.id}`}
              value={filter.value}
              onChange={(e) => filter.onChange(e.target.value)}
              className="h-9 rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-700 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 cursor-pointer"
            >
              {filter.options.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        ))}

        {onReset && hasActiveFilter && (
          <Button
            variant="ghost"
            size="sm"
            icon={RotateCcw}
            onClick={onReset}
          >
            Reset
          </Button>
        )}
      </div>

      {actions && (
        <div className="flex flex-wrap items-center gap-2 shrink-0">
          {actions}
        </div>
      )}
    </div>
  )
}

