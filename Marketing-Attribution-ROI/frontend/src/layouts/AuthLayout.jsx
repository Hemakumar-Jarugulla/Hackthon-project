import { Outlet } from 'react-router-dom'
import { CheckCircle2, ShieldCheck, TrendingUp } from 'lucide-react'

const PLATFORM_HIGHLIGHTS = [
  {
    icon: TrendingUp,
    title: '5-Model Multi-Touch Attribution',
    description:
      'Compare First Touch, Last Touch, Linear, Time Decay, and Position Based revenue credits.',
  },
  {
    icon: ShieldCheck,
    title: 'Automated Revenue & Cost Governance',
    description:
      'Detect duplicate order revenue, currency mismatches, and omitted campaign costs.',
  },
  {
    icon: CheckCircle2,
    title: 'Full Contact-to-Order Journey Traceability',
    description:
      'Follow every web session, touchpoint, lead, opportunity, and closed order chronologically.',
  },
]

/**
 * Split-screen SaaS authentication layout for login, registration, and password recovery.
 */
export function AuthLayout() {
  return (
    <div className="flex min-h-screen bg-slate-50">
      {/* Left enterprise brand panel */}
      <div className="hidden lg:flex lg:w-[44%] flex-col justify-between bg-slate-900 p-12 text-white">
        <div className="flex items-center gap-3">
          <img
            src="/logo.svg"
            alt="AttributionIQ"
            className="h-10 w-10 rounded-xl"
          />
          <div>
            <p className="text-base font-bold tracking-tight">AttributionIQ</p>
            <p className="text-xs text-slate-400">
              Marketing Attribution &amp; ROI Intelligence
            </p>
          </div>
        </div>

        <div className="space-y-8">
          <div>
            <span className="inline-flex items-center rounded-full bg-blue-600/20 border border-blue-500/30 px-3 py-1 text-xs font-semibold text-blue-300">
              Enterprise RevOps Platform
            </span>
            <h1 className="mt-4 text-3xl font-bold tracking-tight leading-tight">
              Turn fragmented touchpoints into verified marketing ROI.
            </h1>
          </div>

          <div className="space-y-5">
            {PLATFORM_HIGHLIGHTS.map((item) => {
              const Icon = item.icon
              return (
                <div key={item.title} className="flex items-start gap-3.5">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-800 border border-slate-700 text-blue-400">
                    <Icon className="h-4 w-4" />
                  </div>
                  <div>
                    <h2 className="text-sm font-semibold text-white">
                      {item.title}
                    </h2>
                    <p className="mt-0.5 text-xs text-slate-400 leading-relaxed">
                      {item.description}
                    </p>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        <p className="text-xs text-slate-500">
          AttributionIQ Frontend · Ready for Django REST &amp; JWT Integration
        </p>
      </div>

      {/* Right form container */}
      <div className="flex flex-1 flex-col items-center justify-center p-6 sm:p-10">
        <div className="mb-8 flex items-center gap-2.5 lg:hidden">
          <img
            src="/logo.svg"
            alt="AttributionIQ"
            className="h-9 w-9 rounded-lg"
          />
          <span className="text-lg font-bold text-slate-900">
            AttributionIQ
          </span>
        </div>

        <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
          <Outlet />
        </div>
      </div>
    </div>
  )
}
