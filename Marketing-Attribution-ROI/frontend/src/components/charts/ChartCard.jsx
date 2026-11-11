import { cn } from '../../utils/formatters'
import { EmptyState } from '../common/EmptyState'
import { LoadingState } from '../common/LoadingState'

/**
 * Standardized analytics chart wrapper card for Recharts visualizations.
 */
export function ChartCard({
  title,
  subtitle,
  actions,
  loading = false,
  isEmpty = false,
  emptyMessage = 'No chart data available for the selected filters.',
  heightClass = 'h-72',
  children,
  className = '',
}) {
  return (
    <div
      className={cn(
        'rounded-xl border border-slate-200 bg-white shadow-xs',
        className
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 px-5 py-4">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
          {subtitle && (
            <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>
          )}
        </div>
        {actions && (
          <div className="flex items-center gap-2 shrink-0 no-print">
            {actions}
          </div>
        )}
      </div>

      <div className="p-5">
        {loading ? (
          <LoadingState className="border-0 py-10" />
        ) : isEmpty ? (
          <EmptyState
            className="border-0 py-10"
            title="No visualization data"
            description={emptyMessage}
          />
        ) : (
          <div className={cn('w-full', heightClass)}>{children}</div>
        )}
      </div>
    </div>
  )
}

