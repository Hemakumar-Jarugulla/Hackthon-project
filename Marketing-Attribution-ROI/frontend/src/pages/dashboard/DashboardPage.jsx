import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Activity,
  AlertTriangle,
  Briefcase,
  DollarSign,
  Download,
  Megaphone,
  Sparkles,
  TrendingUp,
  Users,
  Wallet,
} from 'lucide-react'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
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
  ErrorState,
  KpiCard,
  PageHeader,
  SkeletonGrid,
} from '../../components/common'
import { ChartCard } from '../../components/charts/ChartCard'
import { useApp } from '../../hooks/useApp'
import { useAuth } from '../../hooks/useAuth'
import { useToast } from '../../hooks/useToast'
import { analyticsService } from '../../services/analyticsService'
import { campaignService } from '../../services/campaignService'
import {
  CHART_COLORS,
  CHART_SERIES_PALETTE,
  CHART_TOOLTIP_STYLE,
} from '../../utils/chartTheme'
import { exportToCsv } from '../../utils/exportUtils'
import {
  formatCurrency,
  formatDateTime,
  formatNumber,
  formatPercent,
} from '../../utils/formatters'

export function DashboardPage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const { dateRange, setDateRange, dateRangeOptions } = useApp()
  const { showToast } = useToast()

  const [campaignFilter, setCampaignFilter] = useState('all')
  const [channelFilter, setChannelFilter] = useState('all')
  const [campaigns, setCampaigns] = useState([])
  const [channels, setChannels] = useState([])
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchDashboardResources = () =>
    Promise.all([
      campaignService.listCampaigns({ dateRange }),
      campaignService.listChannels(dateRange),
      analyticsService.getDashboardSummary({
        dateRange,
        campaignId: campaignFilter,
        channelId: channelFilter,
      }),
    ])

  const loadDashboard = async () => {
    try {
      setLoading(true)
      setError(null)
      const [cmpList, chList, dash] = await fetchDashboardResources()
      setCampaigns(cmpList)
      setChannels(chList)
      setSummary(dash)
    } catch (err) {
      setError(err.message || 'Failed to load dashboard metrics.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let active = true
    fetchDashboardResources()
      .then(([cmpList, chList, dash]) => {
        if (!active) return
        setError(null)
        setCampaigns(cmpList)
        setChannels(chList)
        setSummary(dash)
        setLoading(false)
      })
      .catch((err) => {
        if (!active) return
        setError(err.message || 'Failed to load dashboard metrics.')
        setLoading(false)
      })
    return () => {
      active = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dateRange, campaignFilter, channelFilter])

  const activePeriodLabel =
    dateRangeOptions.find((o) => o.value === dateRange)?.label || dateRange

  const handleExport = () => {
    if (!summary?.widgets?.topCampaigns?.length) return
    exportToCsv('dashboard-campaign-summary.csv', summary.widgets.topCampaigns, [
      { key: 'id', label: 'Campaign ID' },
      { key: 'name', label: 'Campaign Name' },
      { key: 'channelName', label: 'Channel' },
      { key: 'spend', label: 'Spend (USD)' },
      { key: 'attributedRevenue', label: 'Attributed Revenue (USD)' },
      { key: 'leads', label: 'Leads' },
      { key: 'roi', label: 'ROI (%)' },
      { key: 'status', label: 'Status' },
    ])
    showToast({
      type: 'success',
      title: 'Dashboard Exported',
      message: 'Downloaded dashboard-campaign-summary.csv.',
    })
  }

  if (error) {
    return <ErrorState message={error} onRetry={loadDashboard} />
  }

  const kpis = summary?.kpis
  const charts = summary?.charts
  const widgets = summary?.widgets

  const revenueSpark = (charts?.monthlySeries || []).map((m) => ({ value: m.revenue }))
  const spendSpark = (charts?.monthlySeries || []).map((m) => ({ value: m.spend }))

  return (
    <div className="space-y-6">
      <PageHeader
        title={`Welcome back, ${user?.name?.split(' ')[0] || 'Alex'}`}
        description={`Executive attribution & ROI overview · Reporting period: ${activePeriodLabel}`}
        badge={<Badge variant="primary" dot>Live Intelligence</Badge>}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <select
              aria-label="Dashboard reporting period"
              value={dateRange}
              onChange={(e) => setDateRange(e.target.value)}
              className="h-9 rounded-lg border border-slate-200 bg-white px-3 text-xs font-medium text-slate-700 focus:border-blue-500 focus:outline-none cursor-pointer"
            >
              {dateRangeOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>

            <select
              aria-label="Filter by channel"
              value={channelFilter}
              onChange={(e) => setChannelFilter(e.target.value)}
              className="h-9 rounded-lg border border-slate-200 bg-white px-3 text-xs font-medium text-slate-700 focus:border-blue-500 focus:outline-none cursor-pointer"
            >
              <option value="all">All Channels</option>
              {channels.map((ch) => (
                <option key={ch.id} value={ch.id}>
                  {ch.name}
                </option>
              ))}
            </select>

            <select
              aria-label="Filter by campaign"
              value={campaignFilter}
              onChange={(e) => setCampaignFilter(e.target.value)}
              className="h-9 max-w-[200px] rounded-lg border border-slate-200 bg-white px-3 text-xs font-medium text-slate-700 focus:border-blue-500 focus:outline-none cursor-pointer"
            >
              <option value="all">All Campaigns</option>
              {campaigns.map((cmp) => (
                <option key={cmp.id} value={cmp.id}>
                  {cmp.name}
                </option>
              ))}
            </select>

            <Button
              variant="outline"
              size="md"
              icon={Download}
              onClick={handleExport}
            >
              Export CSV
            </Button>
          </div>
        }
      />

      {/* 8 KPI Cards */}
      {loading || !kpis ? (
        <SkeletonGrid count={8} />
      ) : (
        <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <KpiCard
            title="Total Campaigns"
            value={formatNumber(kpis.totalCampaigns)}
            change={14.2}
            icon={Megaphone}
            accent="blue"
          />
          <KpiCard
            title="Total Marketing Spend"
            value={formatCurrency(kpis.totalSpend)}
            change={-3.1}
            trend="down"
            icon={Wallet}
            accent="amber"
            sparklineData={spendSpark}
            sparklineColor={CHART_COLORS.amber}
          />
          <KpiCard
            title="Total Contacts"
            value={formatNumber(kpis.totalContacts)}
            change={11.5}
            icon={Users}
            accent="violet"
          />
          <KpiCard
            title="Total Touchpoints"
            value={formatNumber(kpis.totalTouchpoints)}
            change={19.4}
            icon={Activity}
            accent="blue"
          />
          <KpiCard
            title="Total Leads"
            value={formatNumber(kpis.totalLeads)}
            change={16.8}
            icon={Sparkles}
            accent="blue"
          />
          <KpiCard
            title="Total Opportunities"
            value={formatNumber(kpis.totalOpportunities)}
            change={12.0}
            icon={Briefcase}
            accent="violet"
          />
          <KpiCard
            title="Closed Revenue"
            value={formatCurrency(kpis.closedRevenue)}
            change={24.6}
            icon={DollarSign}
            accent="emerald"
            sparklineData={revenueSpark}
            sparklineColor={CHART_COLORS.emerald}
          />
          <KpiCard
            title="Marketing ROI"
            value={formatPercent(kpis.blendedRoi)}
            change={8.9}
            icon={TrendingUp}
            accent="emerald"
          />
        </section>
      )}

      {/* Charts Row 1: Revenue vs Marketing Spend & Monthly Revenue */}
      <section className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <ChartCard
          title="Revenue vs Marketing Spend"
          subtitle="Monthly verified closed revenue compared against verified USD spend"
          loading={loading}
        >
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={charts?.monthlySeries || []}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={CHART_COLORS.grid} />
              <XAxis dataKey="month" tick={{ fontSize: 12, fill: '#475569' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 12, fill: '#475569' }} axisLine={false} tickLine={false} tickFormatter={(v) => `$${v / 1000}k`} />
              <Tooltip contentStyle={CHART_TOOLTIP_STYLE} formatter={(val) => formatCurrency(val)} />
              <Legend wrapperStyle={{ fontSize: '12px' }} />
              <Line type="monotone" dataKey="revenue" name="Closed Revenue" stroke={CHART_COLORS.primary} strokeWidth={2.5} dot={{ r: 3 }} />
              <Line type="monotone" dataKey="spend" name="Marketing Spend" stroke={CHART_COLORS.amber} strokeWidth={2.5} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard
          title="Monthly Closed Revenue"
          subtitle="Verified order revenue velocity across 2026"
          loading={loading}
        >
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={charts?.monthlySeries || []}>
              <defs>
                <linearGradient id="dashRevArea" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={CHART_COLORS.emerald} stopOpacity={0.28} />
                  <stop offset="100%" stopColor={CHART_COLORS.emerald} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={CHART_COLORS.grid} />
              <XAxis dataKey="month" tick={{ fontSize: 12, fill: '#475569' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 12, fill: '#475569' }} axisLine={false} tickLine={false} tickFormatter={(v) => `$${v / 1000}k`} />
              <Tooltip contentStyle={CHART_TOOLTIP_STYLE} formatter={(val) => formatCurrency(val)} />
              <Area type="monotone" dataKey="revenue" name="Monthly Revenue" stroke={CHART_COLORS.emerald} strokeWidth={2.5} fill="url(#dashRevArea)" />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>
      </section>

      {/* Charts Row 2: Campaign ROI Ranking & Channel Performance */}
      <section className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <ChartCard
          title="Campaign ROI Ranking"
          subtitle="Horizontal ranking of return on marketing investment (%)"
          loading={loading}
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              layout="vertical"
              data={charts?.campaignRoiRanking || []}
              margin={{ left: 20, right: 20 }}
            >
              <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke={CHART_COLORS.grid} />
              <XAxis type="number" tick={{ fontSize: 11, fill: '#475569' }} tickFormatter={(v) => `${v}%`} />
              <YAxis type="category" dataKey="name" width={145} tick={{ fontSize: 11, fill: '#334155' }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={CHART_TOOLTIP_STYLE} formatter={(val) => `${val}%`} />
              <Bar dataKey="roi" name="Campaign ROI (%)" fill={CHART_COLORS.primary} radius={[0, 6, 6, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard
          title="Channel Performance"
          subtitle="Attributed revenue vs marketing spend by channel"
          loading={loading}
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={charts?.channelPerformance || []}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={CHART_COLORS.grid} />
              <XAxis dataKey="channel" tick={{ fontSize: 11, fill: '#475569' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: '#475569' }} axisLine={false} tickLine={false} tickFormatter={(v) => `$${v / 1000}k`} />
              <Tooltip contentStyle={CHART_TOOLTIP_STYLE} formatter={(val) => formatCurrency(val)} />
              <Legend wrapperStyle={{ fontSize: '12px' }} />
              <Bar dataKey="revenue" name="Attributed Revenue" fill={CHART_COLORS.primary} radius={[6, 6, 0, 0]} />
              <Bar dataKey="spend" name="Spend" fill={CHART_COLORS.slate} radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </section>

      {/* Charts Row 3: Funnel, Attribution Pie, Journey Dist, Exception Dist */}
      <section className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-4">
        <ChartCard
          title="Lead Conversion Funnel"
          subtitle="Touchpoints to Closed Orders"
          loading={loading}
          heightClass="h-60"
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart layout="vertical" data={charts?.funnelData || []}>
              <XAxis type="number" hide />
              <YAxis type="category" dataKey="stage" width={95} tick={{ fontSize: 11, fill: '#334155' }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={CHART_TOOLTIP_STYLE} />
              <Bar dataKey="count" name="Records" fill={CHART_COLORS.violet} radius={[0, 6, 6, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard
          title="Attribution Distribution"
          subtitle="Channel share (Position Based)"
          loading={loading}
          heightClass="h-60"
        >
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={charts?.modelDistribution || []}
                dataKey="value"
                nameKey="name"
                innerRadius={42}
                outerRadius={72}
                paddingAngle={3}
              >
                {(charts?.modelDistribution || []).map((entry, idx) => (
                  <Cell
                    key={entry.name}
                    fill={CHART_SERIES_PALETTE[idx % CHART_SERIES_PALETTE.length]}
                  />
                ))}
              </Pie>
              <Tooltip contentStyle={CHART_TOOLTIP_STYLE} formatter={(val) => formatCurrency(val)} />
              <Legend wrapperStyle={{ fontSize: '11px' }} />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard
          title="Customer Journey Depth"
          subtitle="Contacts by touchpoint count"
          loading={loading}
          heightClass="h-60"
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={charts?.journeyDistribution || []}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={CHART_COLORS.grid} />
              <XAxis dataKey="bucket" tick={{ fontSize: 11, fill: '#475569' }} axisLine={false} tickLine={false} />
              <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: '#475569' }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={CHART_TOOLTIP_STYLE} />
              <Bar dataKey="contacts" name="Contacts" fill={CHART_COLORS.cyan} radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard
          title="Exception Distribution"
          subtitle="Data quality issues by severity"
          loading={loading}
          heightClass="h-60"
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={charts?.exceptionDistribution || []}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={CHART_COLORS.grid} />
              <XAxis dataKey="severity" tick={{ fontSize: 11, fill: '#475569' }} axisLine={false} tickLine={false} />
              <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: '#475569' }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={CHART_TOOLTIP_STYLE} />
              <Bar dataKey="count" name="Exceptions" fill={CHART_COLORS.rose} radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </section>

      {/* 6 Operational Summary Widgets */}
      <section className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* 1. Top Performing Campaigns */}
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Top Performing Campaigns</CardTitle>
              <CardDescription>Ranked by attributed revenue</CardDescription>
            </div>
            <Button variant="ghost" size="sm" onClick={() => navigate('/campaigns')}>
              View All
            </Button>
          </CardHeader>
          <CardContent className="divide-y divide-slate-100 p-0">
            {(widgets?.topCampaigns || []).map((cmp) => (
              <button
                key={cmp.id}
                type="button"
                onClick={() => navigate(`/campaigns/${cmp.id}`)}
                className="flex w-full items-center justify-between px-5 py-3 text-left hover:bg-slate-50 cursor-pointer"
              >
                <div className="min-w-0 pr-3">
                  <p className="truncate text-xs font-semibold text-slate-900">
                    {cmp.name}
                  </p>
                  <p className="text-[11px] text-slate-500">
                    {cmp.channelName} · {cmp.id}
                  </p>
                </div>
                <div className="text-right shrink-0">
                  <p className="text-xs font-bold text-slate-900 tabular-nums">
                    {formatCurrency(cmp.attributedRevenue)}
                  </p>
                  <p className="text-[11px] font-medium text-emerald-600 tabular-nums">
                    {cmp.roi !== null ? `ROI ${formatPercent(cmp.roi)}` : 'Zero Spend'}
                  </p>
                </div>
              </button>
            ))}
          </CardContent>
        </Card>

        {/* 2. Recent Campaign Activity (Touchpoints) */}
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Recent Campaign Activity</CardTitle>
              <CardDescription>Latest recorded touchpoints</CardDescription>
            </div>
            <Button variant="ghost" size="sm" onClick={() => navigate('/touchpoints')}>
              View All
            </Button>
          </CardHeader>
          <CardContent className="divide-y divide-slate-100 p-0">
            {(widgets?.recentTouchpoints || []).map((tp) => (
              <div key={tp.id} className="flex items-start justify-between gap-3 px-5 py-3">
                <div className="min-w-0">
                  <p className="truncate text-xs font-semibold text-slate-900">
                    {tp.interactionType}
                  </p>
                  <p className="truncate text-[11px] text-slate-500">
                    {tp.contactId} · {tp.campaignId}
                  </p>
                </div>
                <Badge status={tp.isPostConversion ? 'Invalid' : 'Valid'}>
                  {tp.isPostConversion ? 'Post-Conv' : tp.device}
                </Badge>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* 3. Data Quality Alerts */}
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Data Quality Alerts</CardTitle>
              <CardDescription>Open attribution &amp; ledger exceptions</CardDescription>
            </div>
            <Button variant="ghost" size="sm" onClick={() => navigate('/exceptions')}>
              Triage
            </Button>
          </CardHeader>
          <CardContent className="divide-y divide-slate-100 p-0">
            {(widgets?.dataQualityAlerts || []).map((exc) => (
              <button
                key={exc.id}
                type="button"
                onClick={() => navigate('/exceptions')}
                className="flex w-full items-start justify-between gap-2 px-5 py-3 text-left hover:bg-slate-50 cursor-pointer"
              >
                <div className="flex items-start gap-2.5 min-w-0">
                  <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-600" />
                  <div className="min-w-0">
                    <p className="truncate text-xs font-semibold text-slate-900">
                      {exc.issueType}
                    </p>
                    <p className="truncate text-[11px] text-slate-500">
                      {exc.entityId}
                    </p>
                  </div>
                </div>
                <Badge status={exc.severity}>{exc.severity}</Badge>
              </button>
            ))}
          </CardContent>
        </Card>

        {/* 4. Recent Leads */}
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Recent Leads</CardTitle>
              <CardDescription>Lead scoring &amp; source overview</CardDescription>
            </div>
            <Button variant="ghost" size="sm" onClick={() => navigate('/leads')}>
              View All
            </Button>
          </CardHeader>
          <CardContent className="divide-y divide-slate-100 p-0">
            {(widgets?.recentLeads || []).map((lead) => (
              <div key={lead.id} className="flex items-center justify-between px-5 py-3">
                <div className="min-w-0">
                  <p className="truncate text-xs font-semibold text-slate-900">
                    {lead.contactName}
                  </p>
                  <p className="text-[11px] text-slate-500">
                    {lead.id} · Score {lead.score}
                  </p>
                </div>
                <Badge status={lead.status}>{lead.status}</Badge>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* 5. Recent Opportunities */}
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Recent Opportunities</CardTitle>
              <CardDescription>Active and closed sales deals</CardDescription>
            </div>
            <Button variant="ghost" size="sm" onClick={() => navigate('/opportunities')}>
              Pipeline
            </Button>
          </CardHeader>
          <CardContent className="divide-y divide-slate-100 p-0">
            {(widgets?.recentOpportunities || []).map((opp) => (
              <div key={opp.id} className="flex items-center justify-between gap-2 px-5 py-3">
                <div className="min-w-0">
                  <p className="truncate text-xs font-semibold text-slate-900">
                    {opp.name}
                  </p>
                  <p className="text-[11px] text-slate-500">
                    {opp.id} · {formatCurrency(opp.expectedRevenue)}
                  </p>
                </div>
                <Badge status={opp.stage}>{opp.stage}</Badge>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* 6. Recent Attribution Calculations */}
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Recent Attribution Calculations</CardTitle>
              <CardDescription>Audit log of model calculation runs</CardDescription>
            </div>
            <Button variant="ghost" size="sm" onClick={() => navigate('/attribution')}>
              Explore
            </Button>
          </CardHeader>
          <CardContent className="divide-y divide-slate-100 p-0">
            {(widgets?.recentAttributionRuns || []).map((run) => (
              <div key={run.runId} className="flex items-center justify-between gap-2 px-5 py-3">
                <div className="min-w-0">
                  <p className="text-xs font-semibold text-slate-900">
                    {run.runId} · {run.conversionWindowDays}d window
                  </p>
                  <p className="text-[11px] text-slate-500">
                    {formatDateTime(run.executedAt)} · {run.validOrdersProcessed} orders
                  </p>
                </div>
                <span className="text-xs font-bold text-emerald-700 tabular-nums">
                  {formatCurrency(run.totalAttributedRevenue)}
                </span>
              </div>
            ))}
          </CardContent>
        </Card>
      </section>
    </div>
  )
}
