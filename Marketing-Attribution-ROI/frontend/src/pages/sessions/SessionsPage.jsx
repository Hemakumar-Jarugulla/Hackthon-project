import { useEffect, useMemo, useState } from 'react'
import { AlertTriangle, CheckCircle2, HelpCircle } from 'lucide-react'
import {
  Badge,
  FilterBar,
  KpiCard,
  PageHeader,
} from '../../components/common'
import { DataTable } from '../../components/tables/DataTable'
import { contactService } from '../../services/contactService'
import { formatDateTime, formatNumber } from '../../utils/formatters'

export function SessionsPage() {
  const [sessions, setSessions] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [identityFilter, setIdentityFilter] = useState('all')
  const [deviceFilter, setDeviceFilter] = useState('all')

  useEffect(() => {
    contactService.listSessions().then((data) => {
      setSessions(data)
      setLoading(false)
    })
  }, [])

  const filtered = useMemo(() => {
    return sessions.filter((s) => {
      const q = search.toLowerCase()
      const matchesSearch =
        !q ||
        s.id.toLowerCase().includes(q) ||
        s.anonymousId.toLowerCase().includes(q) ||
        (s.contactId || '').toLowerCase().includes(q) ||
        s.landingPage.toLowerCase().includes(q)
      const matchesIdentity =
        identityFilter === 'all' || s.identityStatus === identityFilter
      const matchesDevice =
        deviceFilter === 'all' || s.deviceType === deviceFilter
      return matchesSearch && matchesIdentity && matchesDevice
    })
  }, [sessions, search, identityFilter, deviceFilter])

  const identifiedCount = sessions.filter((s) => s.identityStatus === 'Identified').length
  const anonymousCount = sessions.filter((s) => s.identityStatus === 'Anonymous').length
  const unverifiedCount = sessions.filter((s) => s.identityStatus === 'Unverified Link').length

  const columns = [
    {
      key: 'id',
      label: 'Session ID',
      sortable: true,
      render: (r) => <span className="font-mono text-xs font-semibold text-blue-700">{r.id}</span>,
    },
    {
      key: 'anonymousId',
      label: 'Anonymous ID',
      sortable: true,
      render: (r) => <span className="font-mono text-xs text-slate-600">{r.anonymousId}</span>,
    },
    {
      key: 'contactId',
      label: 'Contact ID',
      sortable: true,
      render: (r) =>
        r.contactId ? (
          <div>
            <p className="text-xs font-semibold text-slate-900">{r.contactName}</p>
            <p className="font-mono text-[11px] text-slate-500">{r.contactId}</p>
          </div>
        ) : (
          <span className="text-xs italic text-slate-400">Unlinked Visitor</span>
        ),
    },
    { key: 'landingPage', label: 'Landing Page', sortable: true },
    { key: 'referrer', label: 'Referrer', sortable: true },
    {
      key: 'campaignSource',
      label: 'Campaign Source',
      sortable: true,
      render: (r) => (
        <div>
          <p className="text-xs font-medium text-slate-800">{r.campaignName}</p>
          <p className="font-mono text-[11px] text-slate-500">{r.campaignSource}</p>
        </div>
      ),
    },
    {
      key: 'timestamp',
      label: 'Session Timestamp',
      sortable: true,
      render: (r) => formatDateTime(r.timestamp),
    },
    { key: 'deviceType', label: 'Device', sortable: true },
    {
      key: 'identityStatus',
      label: 'Identity Linking',
      sortable: true,
      render: (r) => (
        <div>
          <Badge
            status={
              r.identityStatus === 'Identified'
                ? 'Identified'
                : r.identityStatus === 'Unverified Link'
                  ? 'Critical'
                  : 'Anonymous'
            }
            dot
          >
            {r.identityStatus}
          </Badge>
          {r.linkingIssue && (
            <p className="mt-1 max-w-[210px] text-[11px] text-rose-700 leading-snug">
              {r.linkingIssue}
            </p>
          )}
        </div>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title="Web Session Management"
        description="Monitor identified sessions, anonymous visits, and identity-resolution evidence."
        badge={<Badge variant="primary">{sessions.length} Sessions</Badge>}
      />

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <KpiCard
          title="Identified Sessions"
          value={formatNumber(identifiedCount)}
          changeLabel="Deterministic email/form evidence"
          icon={CheckCircle2}
          accent="emerald"
        />
        <KpiCard
          title="Anonymous Sessions"
          value={formatNumber(anonymousCount)}
          changeLabel="Unconverted visitor cookies"
          icon={HelpCircle}
          accent="slate"
        />
        <KpiCard
          title="Unverified Identity Links"
          value={formatNumber(unverifiedCount)}
          changeLabel="Linked without evidence (flagged)"
          icon={AlertTriangle}
          accent="rose"
        />
      </section>

      <FilterBar
        searchValue={search}
        onSearchChange={setSearch}
        searchPlaceholder="Search session ID, anonymous ID, contact, or landing page..."
        filters={[
          {
            id: 'ses-identity',
            label: 'Identity',
            value: identityFilter,
            onChange: setIdentityFilter,
            options: [
              { value: 'all', label: 'All Identity States' },
              { value: 'Identified', label: 'Identified' },
              { value: 'Anonymous', label: 'Anonymous' },
              { value: 'Unverified Link', label: 'Unverified Link' },
            ],
          },
          {
            id: 'ses-device',
            label: 'Device',
            value: deviceFilter,
            onChange: setDeviceFilter,
            options: [
              { value: 'all', label: 'All Devices' },
              { value: 'Desktop', label: 'Desktop' },
              { value: 'Mobile', label: 'Mobile' },
              { value: 'Tablet', label: 'Tablet' },
            ],
          },
        ]}
        onReset={() => {
          setSearch('')
          setIdentityFilter('all')
          setDeviceFilter('all')
        }}
      />

      <DataTable
        columns={columns}
        data={filtered}
        loading={loading}
        pageSize={10}
        rowClassName={(row) =>
          row.identityStatus === 'Unverified Link'
            ? 'bg-rose-50/70 hover:bg-rose-50'
            : ''
        }
      />
    </div>
  )
}

