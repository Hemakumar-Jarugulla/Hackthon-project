import { useEffect, useState } from 'react'
import { Eye, Scale } from 'lucide-react'
import {
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
  Button,
  PageHeader,
} from '../../components/common'
import { ChartCard } from '../../components/charts/ChartCard'
import { Modal } from '../../components/modals/Modal'
import { DataTable } from '../../components/tables/DataTable'
import { useApp } from '../../hooks/useApp'
import { attributionService } from '../../services/attributionService'
import { CHART_COLORS, CHART_TOOLTIP_STYLE } from '../../utils/chartTheme'
import { formatCurrency } from '../../utils/formatters'

export function AttributionComparisonPage() {
  const { dateRange } = useApp()
  const [conversionWindow, setConversionWindow] = useState(90)
  const [comparison, setComparison] = useState(null)
  const [loading, setLoading] = useState(true)
  const [selectedRow, setSelectedRow] = useState(null)

  useEffect(() => {
    let active = true
    attributionService
      .compareModels({ conversionWindowDays: conversionWindow, dateRange })
      .then((res) => {
        if (!active) return
        setComparison(res)
        setLoading(false)
      })
    return () => {
      active = false
    }
  }, [conversionWindow, dateRange])

  const campaignRows = comparison?.campaignComparison || []
  const channelRows = comparison?.channelComparison || []

  const columns = [
    {
      key: 'campaignName',
      label: 'Campaign',
      sortable: true,
      render: (r) => (
        <div>
          <p className="font-semibold text-slate-900">{r.campaignName}</p>
          <p className="text-[11px] text-slate-500">
            {r.campaignId} · {r.channelName}
          </p>
        </div>
      ),
    },
    {
      key: 'first_touch',
      label: 'First Touch',
      sortable: true,
      align: 'right',
      render: (r) => formatCurrency(r.first_touch),
    },
    {
      key: 'last_touch',
      label: 'Last Touch',
      sortable: true,
      align: 'right',
      render: (r) => formatCurrency(r.last_touch),
    },
    {
      key: 'linear',
      label: 'Linear',
      sortable: true,
      align: 'right',
      render: (r) => formatCurrency(r.linear),
    },
    {
      key: 'time_decay',
      label: 'Time Decay',
      sortable: true,
      align: 'right',
      render: (r) => formatCurrency(r.time_decay),
    },
    {
      key: 'position_based',
      label: 'Position Based',
      sortable: true,
      align: 'right',
      render: (r) => (
        <span className="font-bold text-blue-700">
          {formatCurrency(r.position_based)}
        </span>
      ),
    },
    {
      key: 'actions',
      label: 'Inspect',
      align: 'right',
      render: (r) => (
        <Button
          variant="ghost"
          size="sm"
          icon={Eye}
          onClick={() => setSelectedRow(r)}
        >
          Details
        </Button>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title="Attribution Model Comparison"
        description="Compare how revenue credit shifts across campaigns and channels under all five attribution methodologies."
        badge={<Badge variant="primary" dot>5-Model Matrix</Badge>}
        actions={
          <label className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 h-9 text-xs text-slate-700">
            <Scale className="h-3.5 w-3.5 text-blue-600" />
            <span>Lookback Window</span>
            <select
              value={conversionWindow}
              onChange={(e) => setConversionWindow(Number(e.target.value))}
              className="bg-transparent font-semibold focus:outline-none cursor-pointer"
            >
              <option value={30}>30 Days</option>
              <option value={60}>60 Days</option>
              <option value={90}>90 Days</option>
              <option value={180}>180 Days</option>
            </select>
          </label>
        }
      />

      <ChartCard
        title="Channel Revenue Comparison Across All 5 Models"
        subtitle="Direct visualization of model credit divergence per marketing channel"
        loading={loading}
        heightClass="h-80"
      >
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={channelRows}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={CHART_COLORS.grid} />
            <XAxis dataKey="channelName" tick={{ fontSize: 11, fill: '#475569' }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 11, fill: '#475569' }} axisLine={false} tickLine={false} tickFormatter={(v) => `$${v / 1000}k`} />
            <Tooltip contentStyle={CHART_TOOLTIP_STYLE} formatter={(val) => formatCurrency(val)} />
            <Legend wrapperStyle={{ fontSize: '12px' }} />
            <Bar dataKey="first_touch" name="First Touch" fill={CHART_COLORS.primary} radius={[4, 4, 0, 0]} />
            <Bar dataKey="last_touch" name="Last Touch" fill={CHART_COLORS.emerald} radius={[4, 4, 0, 0]} />
            <Bar dataKey="linear" name="Linear" fill={CHART_COLORS.violet} radius={[4, 4, 0, 0]} />
            <Bar dataKey="time_decay" name="Time Decay" fill={CHART_COLORS.amber} radius={[4, 4, 0, 0]} />
            <Bar dataKey="position_based" name="Position Based" fill={CHART_COLORS.cyan} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      <DataTable
        columns={columns}
        data={campaignRows}
        rowKey="campaignId"
        loading={loading}
        pageSize={10}
      />

      <Modal
        isOpen={Boolean(selectedRow)}
        onClose={() => setSelectedRow(null)}
        title={selectedRow?.campaignName}
        subtitle={`${selectedRow?.campaignId} · Multi-model attribution comparison`}
      >
        {selectedRow && (
          <div className="space-y-3 text-xs">
            {[
              { label: 'First Touch', val: selectedRow.first_touch },
              { label: 'Last Touch', val: selectedRow.last_touch },
              { label: 'Linear', val: selectedRow.linear },
              { label: 'Time Decay', val: selectedRow.time_decay },
              { label: 'Position Based', val: selectedRow.position_based },
            ].map((row) => (
              <div
                key={row.label}
                className="flex items-center justify-between border-b border-slate-100 pb-2"
              >
                <span className="font-medium text-slate-700">{row.label}</span>
                <span className="font-bold text-slate-900 tabular-nums">
                  {formatCurrency(row.val)}
                </span>
              </div>
            ))}
            <div className="rounded-lg bg-blue-50 border border-blue-200 p-3 text-blue-900">
              <p className="font-semibold">First vs Last Touch Shift</p>
              <p className="mt-0.5">
                Difference:{' '}
                <strong>
                  {formatCurrency(selectedRow.last_touch - selectedRow.first_touch)}
                </strong>{' '}
                (positive indicates stronger closing influence; negative indicates stronger top-of-funnel discovery).
              </p>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}
