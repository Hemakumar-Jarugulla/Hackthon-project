import { Loader2 } from 'lucide-react'
import { cn } from '../../utils/formatters'

/**
 * Centered spinner loading state for pages or sections.
 */
export function LoadingState({
  message = 'Loading analytics data...',
  className = '',
}) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center rounded-xl border border-slate-200 bg-white py-14 px-6 text-center',
        className
      )}
    >
      <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      <p className="mt-3 text-sm font-medium text-slate-700">{message}</p>
    </div>
  )
}

/**
 * Animated skeleton grid for dashboard cards or tables while loading.
 */
export function SkeletonGrid({ count = 4, className = '' }) {
  return (
    <div
      className={cn(
        'grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4',
        className
      )}
    >
      {Array.from({ length: count }).map((_, index) => (
        <div
          key={index}
          className="animate-pulse rounded-xl border border-slate-200 bg-white p-5"
        >
          <div className="h-3 w-24 rounded bg-slate-200" />
          <div className="mt-3 h-7 w-32 rounded bg-slate-200" />
          <div className="mt-4 h-3 w-20 rounded bg-slate-100" />
        </div>
      ))}
    </div>
  )
}

