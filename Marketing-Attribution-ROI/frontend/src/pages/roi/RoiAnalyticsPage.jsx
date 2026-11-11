import { useEffect, useState } from 'react'
import {
  AlertTriangle,
  Award,
  DollarSign,
  Percent,
  Target,
  TrendingDown,
  TrendingUp,
  Wallet,
} from 'lucide-react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  Badge,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  KpiCard,
  PageHeader,
  SkeletonGrid,
} from '../../components/common'
import { ChartCard } from '../../components/charts/ChartCard'
import { DataTable } from '../../components/tables/DataTable'
import { useApp } from '../../hooks/useApp'
import { analyticsService } from '../../services/analyticsService'
import { CHART_COLORS, CHART_TOOLTIP_STYLE } from '../../utils/chartTheme'
import {
  formatCurrency,
  formatNumber,
  formatPercent,
} from '../../utils/formatters'

const MODELS = [
  { value: 'position_based', label: 'Position Based' },
  { value: 'first_touch', label: 'First Touch' },
  { value: 'last_touch', label: 'Last Touch' },
  { value: 'linear', label: 'Linear' },
  { value: 'time_decay', label: 'Time Decay' },
]

export function RoiAnalyticsPage() {
  const { dateRange } = useApp()
  const [modelId, setModelId] = useState('position_based')
  const [roiData, setRoiData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true
    analyticsService.getRoiAnalytics({ dateRange, modelId }).then((res) => {
      if (!active) return
      setRoiData(res)
      setLoading(false)
    })
    return () => {
      active = false
    }
  }, [dateRange, modelId])

  const summary = roiData?.summary
  const campaignRows = roiData?.campaignRows || []
  const channelRows = roiData?.channelRows || []

  const campaignColumns = [
    {
      key: 'name',
      label: 'Campaign',
      sortable: true,
      render: (r) => (
        <div>
          <p className="font-semibold text-slate-900">{r.name}</p>
          <p className="font-mono text-[11px] text-slate-500">
            {r.id} · {r.channelName}
          </p>
        </div>
      ),
    },
    {
      key: 'spend',
      label: 'Marketing Cost',
      sortable: true,
      align: 'right',
      render: (r) => (
        <div>
          <span>{formatCurrency(r.spend)}</span>
          {r.missingCostAlert && (
            <p className="text-[10px] font-semibold text-amber-700">Cost omitted</p>
          )}
        </div>
      ),
    },
    {
      key: 'attributedRevenue',
      label: 'Attributed Rev.',
      sortable: true,
      align: 'right',
      render: (r) => <span className="font-semibold">{formatCurrency(r.attributedRevenue)}</span>,
    },
    {
      key: 'roi',
      label: 'ROI (%)',
      sortable: true,
      align: 'right',
      render: (r) =>
        r.roi === null ? (
          <Badge variant="default">Zero Spend Safe</Badge>
        ) : (
          <span
            className={`font-bold ${
              r.roi >= 0 ? 'text-emerald-700' : 'text-rose-600'
            }`}
          >
            {formatPercent(r.roi)}
          </span>
        ),
    },
    {
      key: 'roas',
      label: 'ROAS',
      sortable: true,
      align: 'right',
      render: (r) => (r.roas === null ? '—' : `${r.roas}x`),
    },
    {
      key: 'leads',
      label: 'Leads',
      sortable: true,
      align: 'right',
      render: (r) => formatNumber(r.leads),
    },
    {
      key: 'cpl',
      label: 'CPL',
      sortable: true,
      align: 'right',
      render: (r) => (r.cpl === null ? '—' : formatCurrency(r.cpl, 'USD', 2)),
    },
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title="Campaign ROI Analytics"
        description="Evaluate ROI, ROAS, CPL, Conversion Rate, and AOV with safe handling for zero-spend and missing cost campaigns."
        badge={<Badge variant="primary" dot>Financial Intelligence</Badge>}
        actions={
          <label className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 h-9 text-xs text-slate-700">
            <span className="font-medium">Attribution Basis</span>
            <select
              value={modelId}
              onChange={(e) => setModelId(e.target.value)}
              className="bg-transparent font-semibold focus:outline-none cursor-pointer"
            >
              {MODELS.map((m) => (
                <option key={m.value} value={m.value}>
                  {m.label}
                </option>
              ))}
            </select>
          </label>
        }
      />

      {/* 8 Financial ROI KPIs from Section 22 */}
      {loading || !summary ? (
        <SkeletonGrid count={8} />
      ) : (
        <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <KpiCard
            title="Total Marketing Spend"
            value={formatCurrency(summary.totalSpend)}
            changeLabel="Verified USD ledger costs"
            icon={Wallet}
            accent="amber"
          />
          <KpiCard
            title="Attributed Revenue"
            value={formatCurrency(summary.attributedRevenue)}
            changeLabel="Used in ROI & ROAS formulas"
            icon={TrendingUp}
            accent="blue"
          />
          <KpiCard
            title="Actual Closed Revenue"
            value={formatCurrency(summary.actualClosedRevenue)}
            changeLabel={`${summary.validOrderCount} valid paid orders`}
            icon={DollarSign}
            accent="emerald"
          />
          <KpiCard
            title="Blended ROI"
            value={summary.roi === null ? 'N/A' : formatPercent(summary.roi)}
            changeLabel="((Attr. Rev - Cost) / Cost) × 100"
            icon={Percent}
            accent="emerald"
          />
          <KpiCard
            title="ROAS"
            value={summary.roas === null ? 'N/A' : `${summary.roas}x`}
            changeLabel="Attributed Revenue / Cost"
            icon={Target}
            accent="blue"
          />
          <KpiCard
            title="Cost Per Lead (CPL)"
            value={summary.cpl === null ? 'N/A' : formatCurrency(summary.cpl, 'USD', 2)}
            changeLabel={`${summary.totalLeads} total leads`}
            icon={Wallet}
            accent="violet"
          />
          <KpiCard
            title="Lead Conversion Rate"
            value={formatPercent(summary.conversionRate)}
            changeLabel={`${summary.convertedLeads} / ${summary.totalLeads} leads converted`}
            icon={TrendingUp}
            accent="emerald"
          />
          <KpiCard
            title="Average Order Value"
            value={formatCurrency(summary.aov)}
            changeLabel="Closed Revenue / Valid Orders"
            icon={DollarSign}
            accent="slate"
          />
        </section>
      )}

      {/* Charts */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <ChartCard
          title="Revenue vs Spend & Monthly ROI"
          subtitle="Monthly spend, verified revenue, and ROI trend"
          loading={loading}
        >
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={roiData?.monthlyRoi || []}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={CHART_COLORS.grid} />
              <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#475569' }} axisLine={false} tickLine={false} />
              <YAxis yAxisId="left" tick={{ fontSize: 11, fill: '#475569' }} axisLine={false} tickLine={false} tickFormatter={(v) => `$${v / 1000}k`} />
              <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11, fill: '#475569' }} axisLine={false} tickLine={false} tickFormatter={(v) => `${v}%`} />
              <Tooltip contentStyle={CHART_TOOLTIP_STYLE} />
              <Legend wrapperStyle={{ fontSize: '12px' }} />
              <Bar yAxisId="left" dataKey="revenue" name="Revenue ($)" fill={CHART_COLORS.primary} radius={[4, 4, 0, 0]} />
              <Bar yAxisId="left" dataKey="spend" name="Spend ($)" fill={CHART_COLORS.slate} radius={[4, 4, 0, 0]} />
              <Line yAxisId="right" type="monotone" dataKey="roi" name="Monthly ROI (%)" stroke={CHART_COLORS.emerald} strokeWidth={2.5} />
            </ComposedChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard
          title="Channel ROI Ranking"
          subtitle="Channels with verified positive spend"
          loading={loading}
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              layout="vertical"
              data={channelRows.filter((c) => c.roi !== null).sort((a, b) => b.roi - a.roi)}
              margin={{ left: 20, right: 20 }}
            >
              <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke={CHART_COLORS.grid} />
              <XAxis type="number" tick={{ fontSize: 11, fill: '#475569' }} tickFormatter={(v) => `${v}%`} />
              <YAxis type="category" dataKey="name" width={135} tick={{ fontSize: 11, fill: '#334155' }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={CHART_TOOLTIP_STYLE} formatter={(val) => `${val}%`} />
              <Bar dataKey="roi" name="Channel ROI (%)" fill={CHART_COLORS.emerald} radius={[0, 6, 6, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      {/* Best vs Lowest Performing Campaigns */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Award className="h-4 w-4 text-emerald-600" />
              <div>
                <CardTitle>Best Performing Campaigns</CardTitle>
                <CardDescription>Highest verified ROI</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="divide-y divide-slate-100 p-0">
            {(roiData?.bestCampaigns || []).map((c) => (
              <div key={c.id} className="flex items-center justify-between px-5 py-3 text-xs">
                <div>
                  <p className="font-semibold text-slate-900">{c.name}</p>
                  <p className="text-slate-500">
                    Spend {formatCurrency(c.spend)} → Attr. {formatCurrency(c.attributedRevenue)}
                  </p>
                </div>
                <span className="font-bold text-emerald-700 tabular-nums">
                  {formatPercent(c.roi)}
                </span>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <TrendingDown className="h-4 w-4 text-rose-600" />
              <div>
                <CardTitle>Lowest Performing Campaigns</CardTitle>
                <CardDescription>Lowest ROI among spend-tracked campaigns</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="divide-y divide-slate-100 p-0">
            {(roiData?.lowestCampaigns || []).map((c) => (
              <div key={c.id} className="flex items-center justify-between px-5 py-3 text-xs">
                <div>
                  <p className="font-semibold text-slate-900">{c.name}</p>
                  <p className="text-slate-500">
                    Spend {formatCurrency(c.spend)} → Attr. {formatCurrency(c.attributedRevenue)}
                  </p>
                </div>
                <span
                  className={`font-bold tabular-nums ${
                    c.roi >= 0 ? 'text-amber-700' : 'text-rose-600'
                  }`}
                >
                  {formatPercent(c.roi)}
                </span>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Zero-spend / missing cost protection note */}
      <div className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-900">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
        <p>
          Campaigns with <strong>$0 spend</strong> (such as{' '}
          <span className="font-mono">CMP-2026-000008</span> Organic Hub and{' '}
          <span className="font-mono">CMP-2026-000007</span> with omitted cost ledger)
          display <strong>Zero Spend Safe</strong> instead of dividing by zero.
        </p>
      </div>

      <DataTable
        columns={campaignColumns}
        data={campaignRows}
        loading={loading}
        pageSize={10}
      />
    </div>
  )
}
