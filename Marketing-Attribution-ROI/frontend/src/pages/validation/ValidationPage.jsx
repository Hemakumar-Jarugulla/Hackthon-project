import { useEffect, useState } from 'react'
import {
  AlertTriangle,
  CheckCircle2,
  Database,
  Play,
  XCircle,
} from 'lucide-react'
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
import { DataTable } from '../../components/tables/DataTable'
import { useToast } from '../../hooks/useToast'
import { analyticsService } from '../../services/analyticsService'
import { formatDateTime, formatNumber } from '../../utils/formatters'

export function ValidationPage() {
  const { showToast } = useToast()
  const [report, setReport] = useState({ checks: [], history: [] })
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)

  useEffect(() => {
    let active = true
    analyticsService.getValidationReport().then((data) => {
      if (!active) return
      setReport(data)
      setLoading(false)
    })
    return () => {
      active = false
    }
  }, [])

  const handleRunSuite = async () => {
    setRunning(true)
    const updated = await analyticsService.runValidationSuite()
    setReport(updated)
    setRunning(false)
    showToast({
      type: 'success',
      title: 'Validation Suite Completed',
      message: `Executed ${updated.checks.length} integrity checks across workspace datasets.`,
    })
  }

  const checks = report.checks || []
  const history = report.history || []

  const totalRecordsChecked = checks.reduce((s, c) => s + Number(c.recordsChecked || 0), 0)
  const passedCount = checks.filter((c) => c.status === 'Passed').length
  const failedCount = checks.filter((c) => c.status === 'Failed').length
  const warningCount = checks.filter((c) => c.status === 'Warning').length

  const columns = [
    {
      key: 'checkName',
      label: 'Check Name',
      sortable: true,
      render: (r) => (
        <div>
          <p className="font-semibold text-slate-900">{r.checkName}</p>
          <p className="text-[11px] text-slate-500">{r.details}</p>
        </div>
      ),
    },
    { key: 'entity', label: 'Entity', sortable: true },
    {
      key: 'recordsChecked',
      label: 'Records Checked',
      sortable: true,
      align: 'right',
      render: (r) => formatNumber(r.recordsChecked),
    },
    {
      key: 'failedRecords',
      label: 'Failed Records',
      sortable: true,
      align: 'right',
      render: (r) => (
        <span
          className={`font-bold ${
            r.failedRecords > 0 ? 'text-rose-600' : 'text-emerald-700'
          }`}
        >
          {formatNumber(r.failedRecords)}
        </span>
      ),
    },
    {
      key: 'status',
      label: 'Status',
      sortable: true,
      render: (r) => <Badge status={r.status} dot>{r.status}</Badge>,
    },
    {
      key: 'lastRun',
      label: 'Last Run Timestamp',
      sortable: true,
      render: (r) => formatDateTime(r.lastRun),
    },
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title="Data Validation"
        description="Automated quality assurance across keys, foreign references, dates, revenue, costs, attribution totals, and currencies."
        badge={<Badge variant="primary">{checks.length} Validation Rules</Badge>}
        actions={
          <Button icon={Play} loading={running} onClick={handleRunSuite}>
            Run Validation Suite
          </Button>
        }
      />

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          title="Total Records Checked"
          value={formatNumber(totalRecordsChecked)}
          changeLabel="Across 10 integrity rules"
          icon={Database}
          accent="blue"
        />
        <KpiCard
          title="Passed Checks"
          value={formatNumber(passedCount)}
          changeLabel="Zero anomalies detected"
          icon={CheckCircle2}
          accent="emerald"
        />
        <KpiCard
          title="Failed Checks"
          value={formatNumber(failedCount)}
          changeLabel="Linked to Exception Management"
          icon={XCircle}
          accent="rose"
        />
        <KpiCard
          title="Warnings"
          value={formatNumber(warningCount)}
          changeLabel="Cost & linking advisories"
          icon={AlertTriangle}
          accent="amber"
        />
      </section>

      <DataTable columns={columns} data={checks} loading={loading} pageSize={10} />

      <Card>
        <CardHeader>
          <div>
            <CardTitle>Validation Execution History</CardTitle>
            <CardDescription>Historical data quality audit runs</CardDescription>
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
                  {run.runId} · {formatDateTime(run.timestamp)}
                </p>
                <p className="text-slate-500">
                  Triggered by {run.triggeredBy} · Completed in {run.durationMs} ms
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Badge status="Passed">{run.passed} Passed</Badge>
                <Badge status="Failed">{run.failed} Failed</Badge>
                <Badge status="Warning">{run.warnings} Warnings</Badge>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}
