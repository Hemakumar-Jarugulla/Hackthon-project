import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Compass } from 'lucide-react'
import { Button } from '../../components/common'

/**
 * Fallback 404 page for unrecognized routes.
 */
export function NotFoundPage() {
  const navigate = useNavigate()

  return (
    <div className="flex min-h-[65vh] flex-col items-center justify-center rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-xs">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-50 text-blue-600">
        <Compass className="h-7 w-7" />
      </div>
      <p className="mt-4 text-xs font-semibold uppercase tracking-wider text-blue-600">
        404 · Route Not Found
      </p>
      <h1 className="mt-1 text-2xl font-bold text-slate-900">
        Page could not be found
      </h1>
      <p className="mt-2 max-w-md text-sm text-slate-600">
        The requested route does not match any module in AttributionIQ. Return
        to the executive dashboard to continue.
      </p>
      <div className="mt-6">
        <Button icon={ArrowLeft} onClick={() => navigate('/dashboard')}>
          Back to Dashboard
        </Button>
      </div>
    </div>
  )
}

