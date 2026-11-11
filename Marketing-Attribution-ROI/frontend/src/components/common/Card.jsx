import { cn } from '../../utils/formatters'

/**
 * Base surface card container with subtle border and shadow.
 */
export function Card({
  children,
  variant = 'white',
  className = '',
  ...props
}) {
  return (
    <div
      className={cn(
        'rounded-xl border border-slate-200 shadow-xs',
        variant === 'muted' ? 'bg-slate-50' : 'bg-white',
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
}

export function CardHeader({ children, className = '' }) {
  return (
    <div
      className={cn(
        'flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-4',
        className
      )}
    >
      {children}
    </div>
  )
}

export function CardTitle({ children, className = '' }) {
  return (
    <h3 className={cn('text-sm font-semibold text-slate-900', className)}>
      {children}
    </h3>
  )
}

export function CardDescription({ children, className = '' }) {
  return (
    <p className={cn('mt-0.5 text-xs text-slate-500', className)}>
      {children}
    </p>
  )
}

export function CardContent({ children, className = '' }) {
  return <div className={cn('p-5', className)}>{children}</div>
}

export function CardFooter({ children, className = '' }) {
  return (
    <div
      className={cn(
        'flex items-center justify-between border-t border-slate-100 bg-slate-50/60 px-5 py-3 rounded-b-xl',
        className
      )}
    >
      {children}
    </div>
  )
}

