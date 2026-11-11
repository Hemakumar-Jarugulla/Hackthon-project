import { cn } from '../../utils/formatters'

const VARIANT_CLASSES = {
  default: 'bg-slate-100 text-slate-700 border-slate-200',
  primary: 'bg-blue-50 text-blue-700 border-blue-200',
  success: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  warning: 'bg-amber-50 text-amber-700 border-amber-200',
  danger: 'bg-rose-50 text-rose-700 border-rose-200',
  purple: 'bg-violet-50 text-violet-700 border-violet-200',
  navy: 'bg-slate-900 text-white border-slate-800',
}

const STATUS_VARIANT_MAP = {
  active: 'success',
  completed: 'primary',
  verified: 'success',
  valid: 'success',
  paid: 'success',
  passed: 'success',
  resolved: 'success',
  'closed won': 'success',
  qualified: 'primary',
  identified: 'primary',
  reviewed: 'primary',
  negotiation: 'purple',
  proposal: 'purple',
  pending: 'warning',
  paused: 'warning',
  warning: 'warning',
  open: 'warning',
  anonymous: 'default',
  draft: 'default',
  archived: 'default',
  inactive: 'default',
  critical: 'danger',
  high: 'danger',
  failed: 'danger',
  invalid: 'danger',
  duplicate: 'danger',
  'closed lost': 'danger',
  medium: 'warning',
  low: 'primary',
}

/**
 * Displays semantic status, severity, or category pills.
 * Pass either `variant` explicitly or `status` to auto-map enterprise labels.
 */
export function Badge({
  children,
  variant,
  status,
  dot = false,
  className = '',
}) {
  const resolvedVariant =
    variant ||
    STATUS_VARIANT_MAP[String(status || children || '').toLowerCase()] ||
    'default'

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold whitespace-nowrap',
        VARIANT_CLASSES[resolvedVariant] || VARIANT_CLASSES.default,
        className
      )}
    >
      {dot && (
        <span
          className="h-1.5 w-1.5 rounded-full bg-current opacity-80"
          aria-hidden="true"
        />
      )}
      {children}
    </span>
  )
}

