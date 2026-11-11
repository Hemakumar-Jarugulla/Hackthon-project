import { AlertTriangle, RefreshCw } from 'lucide-react'
import { cn } from '../../utils/formatters'
import { Button } from './Button'

/**
 * Standard error state panel with optional retry action.
 */
export function ErrorState({
  title = 'Unable to load data',
  message = 'An unexpected error occurred while loading this view.',
  onRetry,
  className = '',
}) {
  return (
    <div
      role="alert"
      className={cn(
        'flex flex-col items-center justify-center rounded-xl border border-rose-200 bg-rose-50/60 py-12 px-6 text-center',
        className
      )}
    >
      <div className="flex h-11 w-11 items-center justify-center rounded-full bg-rose-100 text-rose-600">
        <AlertTriangle className="h-5 w-5" />
      </div>
      <h3 className="mt-3 text-sm font-semibold text-slate-900">{title}</h3>
      <p className="mt-1 max-w-md text-xs text-slate-600 leading-relaxed">
        {message}
      </p>
      {onRetry && (
        <div className="mt-4">
          <Button
            variant="outline"
            size="sm"
            icon={RefreshCw}
            onClick={onRetry}
          >
            Try Again
          </Button>
        </div>
      )}
    </div>
  )
}

