import { useEffect, useMemo, useState } from 'react'
import {
  AlertOctagon,
  AlertTriangle,
  CheckCircle2,
  Eye,
  ShieldAlert,
} from 'lucide-react'
import {
  Badge,
  Button,
  FilterBar,
  KpiCard,
  PageHeader,
} from '../../components/common'
import { FormField, TextArea } from '../../components/forms/FormField'
import { Modal } from '../../components/modals/Modal'
import { DataTable } from '../../components/tables/DataTable'
import { useToast } from '../../hooks/useToast'
import { analyticsService } from '../../services/analyticsService'
import { formatDate, formatNumber } from '../../utils/formatters'

export function ExceptionsPage() {
  const { showToast } = useToast()
  const [exceptions, setExceptions] = useState([])
  const [loading, setLoading] = useState(true)

  const [search, setSearch] = useState('')
  const [severityFilter, setSeverityFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')
  const [issueTypeFilter, setIssueTypeFilter] = useState('all')

  const [detailTarget, setDetailTarget] = useState(null)
  const [resolutionNotes, setResolutionNotes] = useState('')

  const loadData = async () => {
    setLoading(true)
    const data = await analyticsService.listExceptions()
    setExceptions(data)
    setLoading(false)
  }

  useEffect(() => {
    let active = true
    analyticsService.listExceptions().then((data) => {
      if (!active) return
      setExceptions(data)
      setLoading(false)
    })
    return () => {
      active = false
    }
  }, [])

  const openDetail = (item) => {
    setDetailTarget(item)
    setResolutionNotes(item.notes || '')
  }

  const handleStatusUpdate = async (id, nextStatus) => {
    await analyticsService.updateExceptionStatus(id, nextStatus, resolutionNotes)
    showToast({
      type: nextStatus === 'Resolved' ? 'success' : 'info',
      title: `Exception ${nextStatus}`,
      message: `${id} marked as ${nextStatus}.`,
    })
    setDetailTarget(null)
    await loadData()
  }

  const issueTypes = useMemo(
    () => Array.from(new Set(exceptions.map((e) => e.issueType))),
    [exceptions]
  )

  const filtered = useMemo(() => {
    return exceptions.filter((e) => {
      const q = search.toLowerCase()
      const matchesSearch =
        !q ||
        e.id.toLowerCase().includes(q) ||
        e.entityId.toLowerCase().includes(q) ||
        e.issueType.toLowerCase().includes(q) ||
        e.description.toLowerCase().includes(q)
      const matchesSev = severityFilter === 'all' || e.severity === severityFilter
      const matchesStatus =
        statusFilter === 'all' || e.resolutionStatus === statusFilter
      const matchesType =
        issueTypeFilter === 'all' || e.issueType === issueTypeFilter
      return matchesSearch && matchesSev && matchesStatus && matchesType
    })
  }, [exceptions, search, severityFilter, statusFilter, issueTypeFilter])

  const openCount = exceptions.filter((e) => e.resolutionStatus === 'Open').length
  const criticalHighCount = exceptions.filter(
    (e) => e.severity === 'Critical' || e.severity === 'High'
  ).length
  const resolvedCount = exceptions.filter(
    (e) => e.resolutionStatus === 'Resolved'
  ).length

  const columns = [
    {
      key: 'id',
      label: 'Exception ID',
      sortable: true,
      render: (r) => <span className="font-mono text-xs font-semibold text-blue-700">{r.id}</span>,
    },
    {
      key: 'issueType',
      label: 'Issue Type',
      sortable: true,
      render: (r) => <span className="font-semibold text-slate-900">{r.issueType}</span>,
    },
    {
      key: 'entityId',
      label: 'Entity ID',
      sortable: true,
      render: (r) => (
        <div>
          <span className="font-mono text-xs font-semibold text-slate-800">{r.entityId}</span>
          <p className="text-[11px] text-slate-500">{r.entityType}</p>
        </div>
      ),
    },
    {
      key: 'severity',
      label: 'Severity',
      sortable: true,
      render: (r) => <Badge status={r.severity} dot>{r.severity}</Badge>,
    },
    {
      key: 'description',
      label: 'Description',
      render: (r) => (
        <span className="text-xs text-slate-600 line-clamp-2 max-w-xs">{r.description}</span>
      ),
    },
    {
      key: 'expectedDecision',
      label: 'Expected Decision',
      render: (r) => (
        <span className="text-xs text-slate-700 line-clamp-2 max-w-xs">{r.expectedDecision}</span>
      ),
    },
    {
      key: 'actualDecision',
      label: 'Actual Decision',
      render: (r) => (
        <span className="text-xs text-slate-700 line-clamp-2 max-w-xs">{r.actualDecision}</span>
      ),
    },
    {
      key: 'resolutionStatus',
      label: 'Status',
      sortable: true,
      render: (r) => (
        <Badge status={r.resolutionStatus} dot>{r.resolutionStatus}</Badge>
      ),
    },
    {
      key: 'createdDate',
      label: 'Created Date',
      sortable: true,
      render: (r) => formatDate(r.createdDate),
    },
    {
      key: 'actions',
      label: 'Actions',
      align: 'right',
      render: (r) => (
        <div
          className="inline-flex items-center gap-1"
          onClick={(e) => e.stopPropagation()}
        >
          <Button
            variant="ghost"
            size="sm"
            icon={Eye}
            onClick={() => openDetail(r)}
          >
            Inspect
          </Button>
          {r.resolutionStatus !== 'Resolved' && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleStatusUpdate(r.id, 'Resolved')}
            >
              Resolve
            </Button>
          )}
        </div>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title="Exception Management"
        description="Audit and resolve attribution anomalies, duplicate revenue, currency mismatches, omitted costs, and unverified links."
        badge={<Badge variant="danger" dot>{openCount} Open Exceptions</Badge>}
      />

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          title="Total Exceptions"
          value={formatNumber(exceptions.length)}
          changeLabel="5 core anomaly scenarios monitored"
          icon={AlertOctagon}
          accent="blue"
        />
        <KpiCard
          title="Critical & High Severity"
          value={formatNumber(criticalHighCount)}
          changeLabel="Require priority triage"
          icon={ShieldAlert}
          accent="rose"
        />
        <KpiCard
          title="Open / Pending Review"
          value={formatNumber(openCount)}
          changeLabel="Awaiting steward resolution"
          icon={AlertTriangle}
          accent="amber"
        />
        <KpiCard
          title="Resolved Exceptions"
          value={formatNumber(resolvedCount)}
          changeLabel="Verified by governance team"
          icon={CheckCircle2}
          accent="emerald"
        />
      </section>

      <FilterBar
        searchValue={search}
        onSearchChange={setSearch}
        searchPlaceholder="Search exception ID, entity ID, or description..."
        filters={[
          {
            id: 'exc-sev',
            label: 'Severity',
            value: severityFilter,
            onChange: setSeverityFilter,
            options: [
              { value: 'all', label: 'All Severities' },
              { value: 'Critical', label: 'Critical' },
              { value: 'High', label: 'High' },
              { value: 'Medium', label: 'Medium' },
              { value: 'Low', label: 'Low' },
            ],
          },
          {
            id: 'exc-status',
            label: 'Status',
            value: statusFilter,
            onChange: setStatusFilter,
            options: [
              { value: 'all', label: 'All Statuses' },
              { value: 'Open', label: 'Open' },
              { value: 'Reviewed', label: 'Reviewed' },
              { value: 'Resolved', label: 'Resolved' },
            ],
          },
          {
            id: 'exc-type',
            label: 'Issue Type',
            value: issueTypeFilter,
            onChange: setIssueTypeFilter,
            options: [
              { value: 'all', label: 'All Issue Types' },
              ...issueTypes.map((t) => ({ value: t, label: t })),
            ],
          },
        ]}
        onReset={() => {
          setSearch('')
          setSeverityFilter('all')
          setStatusFilter('all')
          setIssueTypeFilter('all')
        }}
      />

      <DataTable
        columns={columns}
        data={filtered}
        loading={loading}
        pageSize={10}
        onRowClick={openDetail}
      />

      {/* Exception Detail & Resolution Modal */}
      <Modal
        isOpen={Boolean(detailTarget)}
        onClose={() => setDetailTarget(null)}
        title={`${detailTarget?.id} · ${detailTarget?.issueType}`}
        subtitle={`Entity: ${detailTarget?.entityId} (${detailTarget?.entityType})`}
        size="lg"
        footer={
          detailTarget && (
            <>
              <Button variant="outline" onClick={() => setDetailTarget(null)}>
                Close
              </Button>
              {detailTarget.resolutionStatus === 'Open' && (
                <Button
                  variant="secondary"
                  onClick={() => handleStatusUpdate(detailTarget.id, 'Reviewed')}
                >
                  Mark as Reviewed
                </Button>
              )}
              {detailTarget.resolutionStatus !== 'Resolved' && (
                <Button
                  onClick={() => handleStatusUpdate(detailTarget.id, 'Resolved')}
                >
                  Resolve Exception
                </Button>
              )}
            </>
          )
        }
      >
        {detailTarget && (
          <div className="space-y-4 text-xs">
            <div className="flex items-center gap-2">
              <Badge status={detailTarget.severity} dot>{detailTarget.severity} Severity</Badge>
              <Badge status={detailTarget.resolutionStatus} dot>
                {detailTarget.resolutionStatus}
              </Badge>
              <span className="text-slate-500">
                Detected {formatDate(detailTarget.createdDate)}
              </span>
            </div>

            <div>
              <p className="font-semibold text-slate-700 mb-1">Description</p>
              <p className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-slate-700 leading-relaxed">
                {detailTarget.description}
              </p>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="rounded-lg border border-emerald-200 bg-emerald-50/60 p-3">
                <p className="font-semibold text-emerald-900 mb-1">Expected Decision</p>
                <p className="text-emerald-800 leading-relaxed">
                  {detailTarget.expectedDecision}
                </p>
              </div>
              <div className="rounded-lg border border-blue-200 bg-blue-50/60 p-3">
                <p className="font-semibold text-blue-900 mb-1">Actual System Decision</p>
                <p className="text-blue-800 leading-relaxed">
                  {detailTarget.actualDecision}
                </p>
              </div>
            </div>

            <FormField label="Steward Resolution Notes" htmlFor="exc-notes">
              <TextArea
                id="exc-notes"
                value={resolutionNotes}
                onChange={(e) => setResolutionNotes(e.target.value)}
                placeholder="Document audit verification or remediation action..."
              />
            </FormField>
          </div>
        )}
      </Modal>
    </div>
  )
}
