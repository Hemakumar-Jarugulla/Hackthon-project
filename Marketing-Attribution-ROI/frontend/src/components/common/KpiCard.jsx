import { ArrowDownRight, ArrowUpRight, Minus } from 'lucide-react'
import { Area, AreaChart, ResponsiveContainer } from 'recharts'
import { cn, formatPercent } from '../../utils/formatters'

/**
 * Enterprise KPI metric card with trend badge, icon, and optional mini sparkline.
 */
export function KpiCard({
  title,
  value,
  change,
  changeLabel = 'vs prior period',
  trend,
  icon: Icon,
  sparklineData,
  sparklineColor = '#2563eb',
  accent = 'blue',
  className = '',
}) {
  const resolvedTrend =
    trend || (change > 0 ? 'up' : change < 0 ? 'down' : 'neutral')

  const trendConfig = {
    up: {
      badge: 'bg-emerald-50 text-emerald-700',
      Icon: ArrowUpRight,
    },
    down: {
      badge: 'bg-rose-50 text-rose-700',
      Icon: ArrowDownRight,
    },
    neutral: {
      badge: 'bg-slate-100 text-slate-600',
      Icon: Minus,
    },
  }[resolvedTrend]

  const iconAccentMap = {
    blue: 'bg-blue-50 text-blue-600',
    emerald: 'bg-emerald-50 text-emerald-600',
    violet: 'bg-violet-50 text-violet-600',
    amber: 'bg-amber-50 text-amber-600',
    rose: 'bg-rose-50 text-rose-600',
    slate: 'bg-slate-100 text-slate-700',
  }

  const TrendIcon = trendConfig.Icon
  const gradientId = `kpi-grad-${String(title).replace(/[^a-zA-Z0-9]/g, '')}`

  return (
    <div
      className={cn(
        'rounded-xl border border-slate-200 bg-white p-5 shadow-xs transition-shadow hover:shadow-sm',
        className
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 truncate">
            {title}
          </p>
          <p className="mt-2 text-2xl font-bold tracking-tight text-slate-900 tabular-nums">
            {value}
          </p>
        </div>

        {Icon && (
          <div
            className={cn(
              'flex h-10 w-10 shrink-0 items-center justify-center rounded-lg',
              iconAccentMap[accent] || iconAccentMap.blue
            )}
          >
            <Icon className="h-5 w-5" />
          </div>
        )}
      </div>

      <div className="mt-4 flex items-end justify-between gap-3">
        <div className="flex flex-wrap items-center gap-1.5">
          {change !== undefined && change !== null && (
            <span
              className={cn(
                'inline-flex items-center gap-0.5 rounded-full px-2 py-0.5 text-xs font-semibold tabular-nums',
                trendConfig.badge
              )}
            >
              <TrendIcon className="h-3.5 w-3.5" />
              {formatPercent(Math.abs(change), 1)}
            </span>
          )}
          {changeLabel && (
            <span className="text-xs text-slate-500">{changeLabel}</span>
          )}
        </div>

        {Array.isArray(sparklineData) && sparklineData.length > 1 && (
          <div className="h-9 w-20 shrink-0">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={sparklineData}>
                <defs>
                  <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                    <stop
                      offset="0%"
                      stopColor={sparklineColor}
                      stopOpacity={0.25}
                    />
                    <stop
                      offset="100%"
                      stopColor={sparklineColor}
                      stopOpacity={0}
                    />
                  </linearGradient>
                </defs>
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke={sparklineColor}
                  strokeWidth={2}
                  fill={`url(#${gradientId})`}
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  )
}

