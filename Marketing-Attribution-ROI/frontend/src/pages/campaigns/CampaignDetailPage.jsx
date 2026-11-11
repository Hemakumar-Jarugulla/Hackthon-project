import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  Calendar,
  DollarSign,
  Target,
  TrendingUp,
  Users,
} from 'lucide-react'
import {
  Bar,
  BarChart,
  CartesianGrid,
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
  EmptyState,
  KpiCard,
  LoadingState,
  PageHeader,
} from '../../components/common'
import { ChartCard } from '../../components/charts/ChartCard'
import { attributionService } from '../../services/attributionService'
import { campaignService } from '../../services/campaignService'
import { contactService } from '../../services/contactService'
import { CHART_COLORS, CHART_TOOLTIP_STYLE } from '../../utils/chartTheme'
import {
  formatCurrency,
  formatDate,
  formatNumber,
  formatPercent,
} from '../../utils/formatters'

export function CampaignDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [campaign, setCampaign] = useState(null)
  const [costs, setCosts] = useState([])
  const [modelChartData, setModelChartData] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const loadDetail = async () => {
      setLoading(true)
      const [cmp, allCosts, comp] = await Promise.all([
        campaignService.getCampaignById(id),
        contactService.listCosts(),
        attributionService.compareModels(),
      ])
      setCampaign(cmp)
      setCosts(allCosts.filter((c) => c.campaignId === id))
      const row = comp.campaignComparison.find((r) => r.campaignId === id)
      if (row) {
        setModelChartData([
          { model: 'First Touch', revenue: row.first_touch },
          { model: 'Last Touch', revenue: row.last_touch },
          { model: 'Linear', revenue: row.linear },
          { model: 'Time Decay', revenue: row.time_decay },
          { model: 'Position Based', revenue: row.position_based },
        ])
      }
      setLoading(false)
    }
    loadDetail()
  }, [id])

  if (loading) return <LoadingState message="Loading campaign details..." />
  if (!campaign) {
    return (
      <EmptyState
        title="Campaign not found"
        description={`No campaign matched ID "${id}".`}
        actionLabel="Back to Campaigns"
        onAction={() => navigate('/campaigns')}
      />
    )
  }

  const budgetUtilization =
    campaign.budget > 0
      ? Math.min(100, Math.round((campaign.spend / campaign.budget) * 100))
      : 0

  return (
    <div className="space-y-6">
      <PageHeader
        title={campaign.name}
        description={campaign.description}
        badge={
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs font-semibold text-slate-500">
              {campaign.id}
            </span>
            <Badge status={campaign.status} dot>{campaign.status}</Badge>
          </div>
        }
        actions={
          <Button
            variant="outline"
            icon={ArrowLeft}
            onClick={() => navigate('/campaigns')}
          >
            Back to Campaigns
          </Button>
        }
      />

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          title="Budget / Spend"
          value={formatCurrency(campaign.spend, campaign.currency)}
          changeLabel={`of ${formatCurrency(campaign.budget, campaign.currency)} budget (${budgetUtilization}%)`}
          icon={DollarSign}
          accent="amber"
        />
        <KpiCard
          title="Attributed Revenue"
          value={formatCurrency(campaign.attributedRevenue, campaign.currency)}
          changeLabel="Position Based credit"
          icon={TrendingUp}
          accent="blue"
        />
        <KpiCard
          title="Campaign ROI"
          value={campaign.roi !== null ? formatPercent(campaign.roi) : 'Zero Spend'}
          changeLabel={`${campaign.conversions} attributed conversions`}
          icon={Target}
          accent="emerald"
        />
        <KpiCard
          title="Leads Generated"
          value={formatNumber(campaign.leads)}
          changeLabel={campaign.channelName}
          icon={Users}
          accent="violet"
        />
      </section>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <ChartCard
          title="Revenue Credit Across 5 Models"
          subtitle="How each attribution methodology values this campaign"
          className="lg:col-span-2"
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={modelChartData}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={CHART_COLORS.grid} />
              <XAxis dataKey="model" tick={{ fontSize: 12, fill: '#475569' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 12, fill: '#475569' }} axisLine={false} tickLine={false} tickFormatter={(v) => `$${v / 1000}k`} />
              <Tooltip contentStyle={CHART_TOOLTIP_STYLE} formatter={(val) => formatCurrency(val)} />
              <Bar dataKey="revenue" name="Attributed Revenue" fill={CHART_COLORS.primary} radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <Card>
          <CardHeader>
            <div>
              <CardTitle>Campaign Configuration</CardTitle>
              <CardDescription>Linked marketing assets &amp; flight</CardDescription>
            </div>
            <Calendar className="h-4 w-4 text-slate-400" />
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            <div className="flex justify-between border-b border-slate-100 pb-2">
              <span className="text-slate-500">Channel</span>
              <span className="font-semibold text-slate-900">{campaign.channelName}</span>
            </div>
            <div className="flex justify-between border-b border-slate-100 pb-2">
              <span className="text-slate-500">Creative</span>
              <span className="font-semibold text-slate-900">{campaign.creativeName}</span>
            </div>
            <div className="flex justify-between border-b border-slate-100 pb-2">
              <span className="text-slate-500">Audience</span>
              <span className="font-semibold text-slate-900">{campaign.audienceName}</span>
            </div>
            <div className="flex justify-between border-b border-slate-100 pb-2">
              <span className="text-slate-500">Objective</span>
              <span className="font-semibold text-slate-900">{campaign.objective}</span>
            </div>
            <div className="flex justify-between border-b border-slate-100 pb-2">
              <span className="text-slate-500">Flight Dates</span>
              <span className="font-semibold text-slate-900">
                {formatDate(campaign.startDate)} – {formatDate(campaign.endDate)}
              </span>
            </div>
            <div>
              <div className="mb-1 flex justify-between text-slate-500">
                <span>Budget Pacing</span>
                <span className="font-semibold text-slate-800">{budgetUtilization}%</span>
              </div>
              <div className="h-2 w-full rounded-full bg-slate-100 overflow-hidden">
                <div
                  className="h-full rounded-full bg-blue-600"
                  style={{ width: `${budgetUtilization}%` }}
                />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <div>
            <CardTitle>Cost Ledger Entries ({costs.length})</CardTitle>
            <CardDescription>Verified and flagged spend recorded against {campaign.id}</CardDescription>
          </div>
          <Button variant="outline" size="sm" onClick={() => navigate('/costs')}>
            Manage Costs
          </Button>
        </CardHeader>
        <CardContent className="p-0">
          {costs.length === 0 ? (
            <div className="p-6 text-center text-xs text-slate-500">
              No cost ledger entries logged for this campaign yet.
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {costs.map((cost) => (
                <div key={cost.id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-3 text-xs">
                  <div>
                    <p className="font-semibold text-slate-900">
                      {cost.id} · {cost.category}
                    </p>
                    <p className="text-slate-500">{cost.description}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-slate-500">{formatDate(cost.date)}</span>
                    <Badge status={cost.currencyMismatch ? 'Warning' : 'Valid'}>
                      {cost.currencyMismatch ? `Mismatch (${cost.currency})` : cost.currency}
                    </Badge>
                    <span className="font-bold text-slate-900 tabular-nums">
                      {formatCurrency(cost.amount, cost.currency)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

