import { useCallback, useState } from 'react'
import { AlertCircle, AlertTriangle, CheckCircle2, Info, X } from 'lucide-react'
import { ToastContext } from './toastStore'

const TOAST_STYLES = {
  success: {
    container: 'bg-white border-emerald-200 text-slate-900',
    iconWrap: 'bg-emerald-50 text-emerald-600',
    Icon: CheckCircle2,
  },
  error: {
    container: 'bg-white border-rose-200 text-slate-900',
    iconWrap: 'bg-rose-50 text-rose-600',
    Icon: AlertCircle,
  },
  warning: {
    container: 'bg-white border-amber-200 text-slate-900',
    iconWrap: 'bg-amber-50 text-amber-600',
    Icon: AlertTriangle,
  },
  info: {
    container: 'bg-white border-blue-200 text-slate-900',
    iconWrap: 'bg-blue-50 text-blue-600',
    Icon: Info,
  },
}

/**
 * Provides application-wide toast notifications accessible via useToast().
 */
export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])

  const dismissToast = useCallback((id) => {
    setToasts((prev) => prev.filter((item) => item.id !== id))
  }, [])

  const showToast = useCallback(
    ({ title, message, type = 'info', duration = 3500 }) => {
      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
      setToasts((prev) => [...prev, { id, title, message, type }])
      if (duration > 0) {
        window.setTimeout(() => {
          dismissToast(id)
        }, duration)
      }
      return id
    },
    [dismissToast]
  )

  return (
    <ToastContext.Provider value={{ showToast, dismissToast }}>
      {children}
      <div
        aria-live="polite"
        className="fixed bottom-4 right-4 z-50 flex w-full max-w-sm flex-col gap-2.5 px-4 sm:px-0 no-print"
      >
        {toasts.map((toast) => {
          const style = TOAST_STYLES[toast.type] || TOAST_STYLES.info
          const IconComponent = style.Icon
          return (
            <div
              key={toast.id}
              role="status"
              className={`flex items-start gap-3 rounded-xl border p-3.5 shadow-lg transition-all ${style.container}`}
            >
              <div
                className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg ${style.iconWrap}`}
              >
                <IconComponent className="h-4 w-4" />
              </div>
              <div className="min-w-0 flex-1">
                {toast.title && (
                  <p className="text-sm font-semibold text-slate-900">
                    {toast.title}
                  </p>
                )}
                {toast.message && (
                  <p className="mt-0.5 text-xs text-slate-600 leading-relaxed">
                    {toast.message}
                  </p>
                )}
              </div>
              <button
                type="button"
                onClick={() => dismissToast(toast.id)}
                aria-label="Dismiss notification"
                className="rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600 cursor-pointer"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          )
        })}
      </div>
    </ToastContext.Provider>
  )
}
