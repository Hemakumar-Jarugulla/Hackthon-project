import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  CheckCircle2,
  DollarSign,
  Eye,
  GitBranch,
  Play,
  Scale,
} from 'lucide-react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  KpiCard,
  PageHeader,
} from '../../components/common'
import { ChartCard } from '../../components/charts/ChartCard'
import { Modal } from '../../components/modals/Modal'
import { DataTable } from '../../components/tables/DataTable'
import { useApp } from '../../hooks/useApp'
import { useToast } from '../../hooks/useToast'
import { attributionService } from '../../services/attributionService'
import {
  CHART_COLORS,
  CHART_SERIES_PALETTE,
  CHART_TOOLTIP_STYLE,
} from '../../utils/chartTheme'
import {
  formatCurrency,
  formatDateTime,
  formatNumber,
  formatPercent,
} from '../../utils/formatters'

export function AttributionModelsPage() {
  const navigate = useNavigate()
  const { dateRange, setDateRange, dateRangeOptions } = useApp()
  const { showToast } = useToast()

  const [models, setModels] = useState([])
  const [selectedModel, setSelectedModel] = useState('position_based')
  const [conversionWindow, setConversionWindow] = useState(90)
  const [result, setResult] = useState(null)
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [detailCampaign, setDetailCampaign] = useState(null)

  const fetchAttributionData = async () =>
    Promise.all([
      attributionService.getModelsConfig(),
      attributionService.calculateAttribution({
        modelId: selectedModel,
        conversionWindowDays: conversionWindow,
        dateRange,
      }),
      attributionService.getCalculationHistory(),
    ])

  const loadAttribution = async () => {
    setLoading(true)
    const [modelCfg, calcRes, histData] = await fetchAttributionData()
    setModels(modelCfg)
    setResult(calcRes)
    setHistory(histData)
    setLoading(false)
  }

  useEffect(() => {
    let active = true
    fetchAttributionData().then(([modelCfg, calcRes, histData]) => {
      if (!active) return
      setModels(modelCfg)
      setResult(calcRes)
      setHistory(histData)
      setLoading(false)
    })
    return () => {
      active = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedModel, conversionWindow, dateRange])

  const handleRecalculate = async () => {
    if (!result) return
    const periodLabel =
      dateRangeOptions.find((o) => o.value === dateRange)?.label || dateRange
    await attributionService.recordCalculationRun({
      period: periodLabel,
      conversionWindowDays: conversionWindow,
      totalAttributedRevenue: result.totalAttributedRevenue,
      validOrdersProcessed: result.validOrderCount,
    })
    showToast({
      type: 'success',
      title: 'Attribution Recalculated',
      message: `Logged new ${activeModelMeta?.name || selectedModel} calculation run.`,
    })
    await loadAttribution()
  }

  const activeModelMeta = models.find((m) => m.id === selectedModel)
  const sortedCampaigns = [...(result?.campaignResults || [])].sort(
    (a, b) => b.attributedRevenue - a.attributedRevenue
  )

  const campaignColumns = [
    {
      key: 'rank',
      label: 'Rank',
      render: (r) => {
        const idx = sortedCampaigns.findIndex((c) => c.campaignId === r.campaignId)
        return (
          <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-slate-100 text-xs font-bold text-slate-700">
            #{idx + 1}
          </span>
        )
      },
    },
    {
      key: 'campaignName',
      label: 'Campaign',
      sortable: true,
      render: (r) => (
        <div>
          <p className="font-semibold text-slate-900">{r.campaignName}</p>
          <p className="font-mono text-[11px] text-slate-500">{r.campaignId}</p>
        </div>
      ),
    },
    { key: 'channelName', label: 'Channel', sortable: true },
    {
      key: 'conversions',
      label: 'Conversions',
      sortable: true,
      align: 'right',
      render: (r) => formatNumber(r.conversions),
    },
    {
      key: 'attributedRevenue',
      label: 'Attributed Revenue',
      sortable: true,
      align: 'right',
      render: (r) => (
        <span className="font-bold text-slate-900">
          {formatCurrency(r.attributedRevenue)}
        </span>
      ),
    },
    {
      key: 'sharePercent',
      label: 'Attribution %',
      sortable: true,
      align: 'right',
      render: (r) => (
        <span className="font-semibold text-blue-700">
          {formatPercent(r.sharePercent)}
        </span>
      ),
    },
    {
      key: 'actions',
      label: 'Breakdown',
      align: 'right',
      render: (r) => (
        <Button
          variant="ghost"
          size="sm"
          icon={Eye}
          onClick={() => setDetailCampaign(r)}
        >
          Credits
        </Button>
      ),
    },
  ]

  const detailCredits = (result?.orderCredits || []).filter(
    (c) => c.campaignId === detailCampaign?.campaignId
  )

  return (
    <div className="space-y-6">
      <PageHeader
        title="Attribution Models"
        description="Execute and inspect First Touch, Last Touch, Linear, Time Decay, and Position Based attribution."
        badge={<Badge variant="primary" dot>Demo Calculation Engine</Badge>}
        actions={
          <>
            <Button
              variant="outline"
              icon={Scale}
              onClick={() => navigate('/attribution/comparison')}
            >
              Compare All 5 Models
            </Button>
            <Button icon={Play} onClick={handleRecalculate}>
              Run Recalculation
            </Button>
          </>
        }
      />

      {/* Model Selector Cards */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {models.map((model) => {
          const active = model.id === selectedModel
          return (
            <button
              key={model.id}
              type="button"
              onClick={() => setSelectedModel(model.id)}
              className={`rounded-xl border p-4 text-left transition-all cursor-pointer ${
                active
                  ? 'border-blue-600 bg-blue-50/70 ring-2 ring-blue-500/20'
                  : 'border-slate-200 bg-white hover:border-slate-300'
              }`}
            >
              <div className="flex items-center justify-between">
                <GitBranch
                  className={`h-4 w-4 ${active ? 'text-blue-600' : 'text-slate-400'}`}
                />
                {active && <Badge variant="primary">Active</Badge>}
              </div>
              <p className="mt-2 text-sm font-bold text-slate-900">{model.name}</p>
              <p className="mt-1 text-[11px] text-slate-600 line-clamp-2 leading-relaxed">
                {model.description}
              </p>
            </button>
          )
        })}
      </div>

      {/* Period & Conversion Window Controls */}
      <Card>
        <CardContent className="flex flex-wrap items-center justify-between gap-4 p-4">
          <div>
            <p className="text-xs font-semibold text-slate-900">
              Active Methodology: {activeModelMeta?.name}
            </p>
            <p className="text-xs text-slate-500">{activeModelMeta?.description}</p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <label className="flex items-center gap-2 text-xs text-slate-600">
              <span className="font-medium">Period</span>
              <select
                value={dateRange}
                onChange={(e) => setDateRange(e.target.value)}
                className="h-9 rounded-lg border border-slate-200 bg-white px-2.5 text-xs font-medium text-slate-700"
              >
                {dateRangeOptions.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="flex items-center gap-2 text-xs text-slate-600">
              <span className="font-medium">Conversion Window</span>
              <select
                value={conversionWindow}
                onChange={(e) => setConversionWindow(Number(e.target.value))}
                className="h-9 rounded-lg border border-slate-200 bg-white px-2.5 text-xs font-medium text-slate-700"
              >
                <option value={30}>30 Days</option>
                <option value={60}>60 Days</option>
                <option value={90}>90 Days</option>
                <option value={180}>180 Days</option>
              </select>
            </label>
          </div>
        </CardContent>
      </Card>

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <KpiCard
          title="Total Attributed Revenue"
          value={formatCurrency(result?.totalAttributedRevenue || 0)}
          changeLabel="100% reconciled with valid closed orders"
          icon={DollarSign}
          accent="emerald"
        />
        <KpiCard
          title="Valid Orders Attributed"
          value={formatNumber(result?.validOrderCount || 0)}
          changeLabel={`Within ${conversionWindow}-day lookback`}
          icon={CheckCircle2}
          accent="blue"
        />
        <KpiCard
          title="Top Channel"
          value={
            [...(result?.channelResults || [])].sort(
              (a, b) => b.attributedRevenue - a.attributedRevenue
            )[0]?.channelName || '—'
          }
          changeLabel="Highest revenue share under selected model"
          icon={GitBranch}
          accent="violet"
        />
      </section>

      <section className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <ChartCard
          title="Attributed Revenue by Campaign"
          subtitle={`Calculated using ${activeModelMeta?.name || selectedModel}`}
          loading={loading}
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={sortedCampaigns}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={CHART_COLORS.grid} />
              <XAxis
                dataKey="campaignName"
                tick={{ fontSize: 10, fill: '#475569' }}
                tickFormatter={(v) => (v.length > 14 ? `${v.slice(0, 14)}...` : v)}
                axisLine={false}
                tickLine={false}
              />
              <YAxis tick={{ fontSize: 11, fill: '#475569' }} axisLine={false} tickLine={false} tickFormatter={(v) => `$${v / 1000}k`} />
              <Tooltip contentStyle={CHART_TOOLTIP_STYLE} formatter={(val) => formatCurrency(val)} />
              <Bar dataKey="attributedRevenue" name="Attributed Revenue" fill={CHART_COLORS.primary} radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard
          title="Channel Attribution Contribution"
          subtitle="Percentage share across marketing channels"
          loading={loading}
        >
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={(result?.channelResults || []).filter((c) => c.attributedRevenue > 0)}
                dataKey="attributedRevenue"
                nameKey="channelName"
                innerRadius={55}
                outerRadius={90}
                paddingAngle={3}
              >
                {(result?.channelResults || []).map((entry, idx) => (
                  <Cell
                    key={entry.channelId}
                    fill={CHART_SERIES_PALETTE[idx % CHART_SERIES_PALETTE.length]}
                  />
                ))}
              </Pie>
              <Tooltip contentStyle={CHART_TOOLTIP_STYLE} formatter={(val) => formatCurrency(val)} />
              <Legend wrapperStyle={{ fontSize: '12px' }} />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>
      </section>

      <DataTable
        columns={campaignColumns}
        data={sortedCampaigns}
        rowKey="campaignId"
        loading={loading}
        pageSize={10}
      />

      {/* Calculation History */}
      <Card>
        <CardHeader>
          <div>
            <CardTitle>Attribution Calculation History</CardTitle>
            <CardDescription>Audit log of scheduled and manual model executions</CardDescription>
          </div>
        </CardHeader>
        <CardContent className="divide-y divide-slate-100 p-0">
          {history.map((run) => (
            <div
              key={run.runId}
              className="flex flex-wrap items-center justify-between gap-3 px-5 py-3 text-xs"
            >
              <div>
                <p className="font-semibold text-slate-900">
                  {run.runId} · {run.period} ({run.conversionWindowDays}d window)
                </p>
                <p className="text-slate-500">
                  {formatDateTime(run.executedAt)} · Triggered by {run.triggeredBy} · Excluded{' '}
                  {run.excludedDuplicateOrders} duplicate order &amp;{' '}
                  {run.excludedPostConversionTouches} post-conversion touch
                </p>
              </div>
              <div className="flex items-center gap-3">
                <span className="font-bold text-slate-900 tabular-nums">
                  {formatCurrency(run.totalAttributedRevenue)}
                </span>
                <Badge status="Completed" dot>{run.status}</Badge>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Attribution Details Modal */}
      <Modal
        isOpen={Boolean(detailCampaign)}
        onClose={() => setDetailCampaign(null)}
        title={detailCampaign?.campaignName}
        subtitle={`Order-level touchpoint credit breakdown (${activeModelMeta?.name})`}
        size="lg"
      >
        {detailCredits.length === 0 ? (
          <p className="text-xs text-slate-500">
            No attributed closed-order credits recorded for this campaign under the selected window.
          </p>
        ) : (
          <div className="space-y-2.5">
            {detailCredits.map((cr) => (
              <div
                key={`${cr.orderId}-${cr.touchpointId}`}
                className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs"
              >
                <div>
                  <p className="font-semibold text-slate-900">
                    Order {cr.orderId} ({formatCurrency(cr.orderRevenue)})
                  </p>
                  <p className="font-mono text-[11px] text-slate-500">
                    {cr.touchpointId} · {formatDateTime(cr.timestamp)}
                  </p>
                </div>
                <div className="text-right">
                  <p className="font-bold text-emerald-700 tabular-nums">
                    {formatCurrency(cr.attributedCredit)}
                  </p>
                  <p className="text-[11px] font-semibold text-blue-700">
                    {formatPercent(cr.weightPercent)} weight
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </Modal>
    </div>
  )
}
