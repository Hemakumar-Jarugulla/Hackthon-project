import { cn } from '../../utils/formatters'

/**
 * Standard page header displaying title, description, optional badge, and action controls.
 */
export function PageHeader({
  title,
  description,
  badge,
  actions,
  className = '',
}) {
  return (
    <div
      className={cn(
        'flex flex-col gap-4 border-b border-slate-200 pb-5 sm:flex-row sm:items-center sm:justify-between',
        className
      )}
    >
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2.5">
          <h1 className="text-xl font-bold tracking-tight text-slate-900 sm:text-2xl">
            {title}
          </h1>
          {badge}
        </div>
        {description && (
          <p className="mt-1 text-sm text-slate-600">{description}</p>
        )}
      </div>

      {actions && (
        <div className="flex flex-wrap items-center gap-2.5 shrink-0 no-print">
          {actions}
        </div>
      )}
    </div>
  )
}

