import { Inbox } from 'lucide-react'
import { cn } from '../../utils/formatters'
import { Button } from './Button'

/**
 * Standard empty state displayed when tables or filters return no records.
 */
export function EmptyState({
  icon: Icon = Inbox,
  title = 'No records found',
  description = 'Try adjusting your search or filter criteria.',
  actionLabel,
  onAction,
  className = '',
}) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50/50 py-14 px-6 text-center',
        className
      )}
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-white border border-slate-200 text-slate-400 shadow-xs">
        <Icon className="h-6 w-6" />
      </div>
      <h3 className="mt-4 text-sm font-semibold text-slate-900">{title}</h3>
      <p className="mt-1 max-w-sm text-xs text-slate-500 leading-relaxed">
        {description}
      </p>
      {actionLabel && onAction && (
        <div className="mt-4">
          <Button variant="outline" size="sm" onClick={onAction}>
            {actionLabel}
          </Button>
        </div>
      )}
    </div>
  )
}

