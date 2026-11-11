import { useEffect, useState } from 'react'
import { CheckCircle2, DollarSign, Info, Layers, TrendingUp } from 'lucide-react'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  Badge,
  KpiCard,
  PageHeader,
  SkeletonGrid,
} from '../../components/common'
import { ChartCard } from '../../components/charts/ChartCard'
import { DataTable } from '../../components/tables/DataTable'
import { useApp } from '../../hooks/useApp'
import { analyticsService } from '../../services/analyticsService'
import { contactService } from '../../services/contactService'
import { CHART_COLORS, CHART_TOOLTIP_STYLE } from '../../utils/chartTheme'
import { formatCurrency, formatDate, formatNumber } from '../../utils/formatters'

export function RevenueAnalyticsPage() {
  const { dateRange } = useApp()
  const [roiData, setRoiData] = useState(null)
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true
    Promise.all([
      analyticsService.getRoiAnalytics({ dateRange }),
      contactService.listOrders(),
    ]).then(([roiRes, ordRes]) => {
      if (!active) return
      setRoiData(roiRes)
      setOrders(ordRes)
      setLoading(false)
    })
    return () => {
      active = false
    }
  }, [dateRange])

  const summary = roiData?.summary
  const duplicateCount = orders.filter((o) => o.verificationStatus === 'Duplicate').length

  const orderColumns = [
    {
      key: 'id',
      label: 'Order ID',
      sortable: true,
      render: (r) => <span className="font-mono text-xs font-semibold text-blue-700">{r.id}</span>,
    },
    { key: 'contactName', label: 'Customer', sortable: true },
    { key: 'orderDate', label: 'Order Date', sortable: true, render: (r) => formatDate(r.orderDate) },
    {
      key: 'revenue',
      label: 'Order Revenue',
      sortable: true,
      align: 'right',
      render: (r) => <span className="font-bold">{formatCurrency(r.revenue, r.currency)}</span>,
    },
    {
      key: 'verificationStatus',
      label: 'Verification Status',
      sortable: true,
      render: (r) => <Badge status={r.verificationStatus} dot>{r.verificationStatus}</Badge>,
    },
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title="Revenue Analytics"
        description="Separate verified closed order revenue from multi-touch attributed revenue credits for accurate financial reporting."
        badge={<Badge variant="success" dot>Reconciled Ledger</Badge>}
      />

      <div className="flex items-start gap-3 rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-xs text-blue-900">
        <Info className="mt-0.5 h-4 w-4 shrink-0 text-blue-600" />
        <p>
          <strong>Actual Closed Revenue</strong> reflects verified paid orders only ({summary?.validOrderCount || 0}{' '}
          valid orders; {duplicateCount} duplicate excluded).{' '}
          <strong>Attributed Revenue</strong> allocates that verified revenue back across touchpoints under the active attribution model.
        </p>
      </div>

      {loading || !summary ? (
        <SkeletonGrid count={4} />
      ) : (
        <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <KpiCard
            title="Actual Closed Revenue"
            value={formatCurrency(summary.actualClosedRevenue)}
            changeLabel={`${summary.validOrderCount} verified paid orders`}
            icon={DollarSign}
            accent="emerald"
          />
          <KpiCard
            title="Attributed Revenue"
            value={formatCurrency(summary.attributedRevenue)}
            changeLabel="Position Based touch allocation"
            icon={TrendingUp}
            accent="blue"
          />
          <KpiCard
            title="Average Order Value (AOV)"
            value={formatCurrency(summary.aov)}
            changeLabel="Closed Revenue / Valid Orders"
            icon={Layers}
            accent="violet"
          />
          <KpiCard
            title="Verified Order Count"
            value={formatNumber(summary.validOrderCount)}
            changeLabel={`${duplicateCount} duplicate excluded`}
            icon={CheckCircle2}
            accent="slate"
          />
        </section>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <ChartCard
          title="Monthly Closed Revenue Trend"
          subtitle="Verified closed-won revenue across 2026"
          loading={loading}
        >
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={roiData?.monthlyRoi || []}>
              <defs>
                <linearGradient id="revAnalyticsArea" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={CHART_COLORS.primary} stopOpacity={0.25} />
                  <stop offset="100%" stopColor={CHART_COLORS.primary} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={CHART_COLORS.grid} />
              <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#475569' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: '#475569' }} axisLine={false} tickLine={false} tickFormatter={(v) => `$${v / 1000}k`} />
              <Tooltip contentStyle={CHART_TOOLTIP_STYLE} formatter={(val) => formatCurrency(val)} />
              <Area type="monotone" dataKey="revenue" name="Closed Revenue" stroke={CHART_COLORS.primary} strokeWidth={2.5} fill="url(#revAnalyticsArea)" />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard
          title="Attributed Revenue vs Spend by Channel"
          subtitle="Channel contribution to reconciled revenue"
          loading={loading}
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={roiData?.channelRows || []}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={CHART_COLORS.grid} />
              <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#475569' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: '#475569' }} axisLine={false} tickLine={false} tickFormatter={(v) => `$${v / 1000}k`} />
              <Tooltip contentStyle={CHART_TOOLTIP_STYLE} formatter={(val) => formatCurrency(val)} />
              <Legend wrapperStyle={{ fontSize: '12px' }} />
              <Bar dataKey="attributedRevenue" name="Attributed Revenue" fill={CHART_COLORS.emerald} radius={[6, 6, 0, 0]} />
              <Bar dataKey="spend" name="Spend" fill={CHART_COLORS.slate} radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <DataTable columns={orderColumns} data={orders} loading={loading} pageSize={10} />
    </div>
  )
}
