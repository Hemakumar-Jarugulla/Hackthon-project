import { Loader2 } from 'lucide-react'
import { cn } from '../../utils/formatters'

const VARIANT_CLASSES = {
  primary:
    'bg-blue-600 text-white hover:bg-blue-700 border-transparent shadow-xs focus-visible:ring-blue-500',
  secondary:
    'bg-slate-100 text-slate-800 hover:bg-slate-200 border-transparent focus-visible:ring-slate-400',
  outline:
    'bg-white text-slate-700 hover:bg-slate-50 border-slate-200 shadow-xs focus-visible:ring-blue-500',
  ghost:
    'bg-transparent text-slate-600 hover:bg-slate-100 hover:text-slate-900 border-transparent focus-visible:ring-slate-400',
  danger:
    'bg-rose-600 text-white hover:bg-rose-700 border-transparent shadow-xs focus-visible:ring-rose-500',
}

const SIZE_CLASSES = {
  sm: 'h-8 px-3 text-xs gap-1.5',
  md: 'h-9 px-4 text-sm gap-2',
  lg: 'h-11 px-5 text-sm gap-2',
}

/**
 * Reusable enterprise SaaS button supporting variants, sizes, icons, and loading state.
 */
export function Button({
  children,
  variant = 'primary',
  size = 'md',
  type = 'button',
  loading = false,
  disabled = false,
  icon: Icon,
  className = '',
  ...props
}) {
  const isDisabled = disabled || loading

  return (
    <button
      type={type}
      disabled={isDisabled}
      className={cn(
        'inline-flex items-center justify-center rounded-lg border font-medium transition-colors cursor-pointer',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        VARIANT_CLASSES[variant] || VARIANT_CLASSES.primary,
        SIZE_CLASSES[size] || SIZE_CLASSES.md,
        className
      )}
      {...props}
    >
      {loading ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : Icon ? (
        <Icon className="h-4 w-4 shrink-0" />
      ) : null}
      {children}
    </button>
  )
}

