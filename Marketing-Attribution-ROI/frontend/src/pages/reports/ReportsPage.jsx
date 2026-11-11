import { useEffect, useState } from 'react'
import { FileBarChart2, FileDown, FileJson, Printer } from 'lucide-react'
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  PageHeader,
} from '../../components/common'
import { DataTable } from '../../components/tables/DataTable'
import { useApp } from '../../hooks/useApp'
import { useToast } from '../../hooks/useToast'
import { analyticsService } from '../../services/analyticsService'
import { campaignService } from '../../services/campaignService'
import { exportToCsv, exportToJson, triggerPrint } from '../../utils/exportUtils'

const REPORT_TYPES = [
  { id: 'campaign_performance', label: 'Campaign Performance Report' },
  { id: 'channel_performance', label: 'Channel Performance Report' },
  { id: 'roi_analysis', label: 'ROI Analysis Report' },
  { id: 'attribution_comparison', label: 'Attribution Comparison Report' },
  { id: 'customer_journey', label: 'Customer Journey Report' },
  { id: 'revenue_analysis', label: 'Revenue Analysis Report' },
  { id: 'exception_report', label: 'Exception Report' },
  { id: 'validation_report', label: 'Data Validation Report' },
]

export function ReportsPage() {
  const { dateRange, setDateRange, dateRangeOptions } = useApp()
  const { showToast } = useToast()

  const [selectedReport, setSelectedReport] = useState('campaign_performance')
  const [campaignFilter, setCampaignFilter] = useState('all')
  const [campaigns, setCampaigns] = useState([])
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    campaignService.listCampaigns().then(setCampaigns)
  }, [])

  useEffect(() => {
    let active = true
    analyticsService
      .buildReportDataset(selectedReport, {
        dateRange,
        campaignId: campaignFilter,
      })
      .then((data) => {
        if (!active) return
        setRows(data)
        setLoading(false)
      })
    return () => {
      active = false
    }
  }, [selectedReport, dateRange, campaignFilter])

  const columns =
    rows.length > 0
      ? Object.keys(rows[0])
          .slice(0, 8)
          .map((key) => ({
            key,
            label: key.replace(/([A-Z])/g, ' $1').replace(/_/g, ' '),
            sortable: true,
            render: (r) => {
              const val = r[key]
              if (typeof val === 'boolean') return val ? 'Yes' : 'No'
              if (val === null || val === undefined) return '—'
              return String(val)
            },
          }))
      : []

  const activeReportLabel =
    REPORT_TYPES.find((r) => r.id === selectedReport)?.label || selectedReport

  return (
    <div className="space-y-6">
      <PageHeader
        title="Enterprise Reports"
        description="Generate, preview, print, and export executive attribution, ROI, revenue, and data governance reports."
        badge={<Badge variant="primary">8 Report Templates</Badge>}
        actions={
          <>
            <Button variant="outline" icon={Printer} onClick={triggerPrint}>
              Print Report
            </Button>
            <Button
              variant="outline"
              icon={FileJson}
              onClick={() => {
                exportToJson(`${selectedReport}.json`, rows)
                showToast({
                  type: 'success',
                  title: 'JSON Exported',
                  message: `Downloaded ${selectedReport}.json`,
                })
              }}
            >
              Export JSON
            </Button>
            <Button
              icon={FileDown}
              onClick={() => {
                exportToCsv(`${selectedReport}.csv`, rows)
                showToast({
                  type: 'success',
                  title: 'CSV Exported',
                  message: `Downloaded ${selectedReport}.csv`,
                })
              }}
            >
              Export CSV
            </Button>
          </>
        }
      />

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4 no-print">
        {REPORT_TYPES.map((rep) => {
          const active = rep.id === selectedReport
          return (
            <button
              key={rep.id}
              type="button"
              onClick={() => setSelectedReport(rep.id)}
              className={`flex items-center gap-3 rounded-xl border p-3.5 text-left transition-all cursor-pointer ${
                active
                  ? 'border-blue-600 bg-blue-50/70 ring-2 ring-blue-500/20'
                  : 'border-slate-200 bg-white hover:border-slate-300'
              }`}
            >
              <FileBarChart2
                className={`h-4 w-4 shrink-0 ${active ? 'text-blue-600' : 'text-slate-400'}`}
              />
              <span className="text-xs font-semibold text-slate-900">
                {rep.label}
              </span>
            </button>
          )
        })}
      </div>

      <Card className="no-print">
        <CardContent className="flex flex-wrap items-center justify-between gap-4 p-4">
          <div>
            <p className="text-xs font-semibold text-slate-900">{activeReportLabel}</p>
            <p className="text-xs text-slate-500">
              Showing {rows.length} row(s) matching current filters
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <select
              aria-label="Report date range"
              value={dateRange}
              onChange={(e) => setDateRange(e.target.value)}
              className="h-9 rounded-lg border border-slate-200 bg-white px-3 text-xs font-medium text-slate-700"
            >
              {dateRangeOptions.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>

            <select
              aria-label="Report campaign filter"
              value={campaignFilter}
              onChange={(e) => setCampaignFilter(e.target.value)}
              className="h-9 rounded-lg border border-slate-200 bg-white px-3 text-xs font-medium text-slate-700"
            >
              <option value="all">All Campaigns</option>
              {campaigns.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div>
            <CardTitle>{activeReportLabel}</CardTitle>
            <CardDescription>
              Print-ready preview · {rows.length} records
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <DataTable
            columns={columns}
            data={rows}
            rowKey={(r, idx) => r.id || r.campaignId || r.channelId || r.contactId || idx}
            loading={loading}
            pageSize={10}
            className="border-0 rounded-t-none"
          />
        </CardContent>
      </Card>
    </div>
  )
}
