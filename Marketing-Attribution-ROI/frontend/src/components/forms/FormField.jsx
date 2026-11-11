import { cn } from '../../utils/formatters'

const baseInputClasses =
  'w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 transition-colors focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 disabled:bg-slate-50 disabled:text-slate-500'

/**
 * Wraps form inputs with label, required marker, helper text, and error message.
 */
export function FormField({
  label,
  htmlFor,
  required = false,
  error,
  helperText,
  children,
  className = '',
}) {
  return (
    <div className={cn('space-y-1.5', className)}>
      {label && (
        <label
          htmlFor={htmlFor}
          className="block text-xs font-semibold text-slate-700"
        >
          {label}
          {required && <span className="ml-0.5 text-rose-500">*</span>}
        </label>
      )}
      {children}
      {error ? (
        <p className="text-xs font-medium text-rose-600">{error}</p>
      ) : helperText ? (
        <p className="text-xs text-slate-500">{helperText}</p>
      ) : null}
    </div>
  )
}

/**
 * Standard input compatible with React Hook Form register() or controlled props.
 */
export function TextInput({ hasError = false, className = '', ...props }) {
  return (
    <input
      className={cn(
        baseInputClasses,
        hasError && 'border-rose-400 focus:border-rose-500 focus:ring-rose-500/20',
        className
      )}
      {...props}
    />
  )
}

/**
 * Standard select dropdown compatible with React Hook Form register().
 */
export function SelectInput({
  options = [],
  placeholder,
  hasError = false,
  className = '',
  children,
  ...props
}) {
  return (
    <select
      className={cn(
        baseInputClasses,
        'cursor-pointer',
        hasError && 'border-rose-400 focus:border-rose-500 focus:ring-rose-500/20',
        className
      )}
      {...props}
    >
      {placeholder && <option value="">{placeholder}</option>}
      {options.map((opt) => (
        <option key={opt.value} value={opt.value}>
          {opt.label}
        </option>
      ))}
      {children}
    </select>
  )
}

/**
 * Standard multi-line textarea compatible with React Hook Form register().
 */
export function TextArea({
  rows = 3,
  hasError = false,
  className = '',
  ...props
}) {
  return (
    <textarea
      rows={rows}
      className={cn(
        baseInputClasses,
        'resize-y',
        hasError && 'border-rose-400 focus:border-rose-500 focus:ring-rose-500/20',
        className
      )}
      {...props}
    />
  )
}

