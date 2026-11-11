import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Eye, Route } from 'lucide-react'
import {
  Badge,
  Button,
  FilterBar,
  PageHeader,
} from '../../components/common'
import { DataTable } from '../../components/tables/DataTable'
import { contactService } from '../../services/contactService'
import { formatCurrency, formatDate, formatNumber } from '../../utils/formatters'

export function ContactsPage() {
  const navigate = useNavigate()
  const [contacts, setContacts] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [lifecycleFilter, setLifecycleFilter] = useState('all')

  useEffect(() => {
    contactService.listContacts().then((data) => {
      setContacts(data)
      setLoading(false)
    })
  }, [])

  const filtered = useMemo(() => {
    return contacts.filter((c) => {
      const q = search.toLowerCase()
      const matchesSearch =
        !q ||
        c.id.toLowerCase().includes(q) ||
        c.name.toLowerCase().includes(q) ||
        c.email.toLowerCase().includes(q) ||
        c.company.toLowerCase().includes(q)
      const matchesLifecycle =
        lifecycleFilter === 'all' || c.lifecycleStatus === lifecycleFilter
      return matchesSearch && matchesLifecycle
    })
  }, [contacts, search, lifecycleFilter])

  const columns = [
    {
      key: 'id',
      label: 'Contact ID',
      sortable: true,
      render: (r) => <span className="font-mono text-xs font-semibold text-blue-700">{r.id}</span>,
    },
    {
      key: 'name',
      label: 'Contact Name',
      sortable: true,
      render: (r) => (
        <div>
          <p className="font-semibold text-slate-900">{r.name}</p>
          <p className="text-xs text-slate-500">{r.company}</p>
        </div>
      ),
    },
    { key: 'email', label: 'Email', sortable: true },
    { key: 'phone', label: 'Phone' },
    { key: 'source', label: 'Source', sortable: true },
    {
      key: 'createdDate',
      label: 'Created Date',
      sortable: true,
      render: (r) => formatDate(r.createdDate),
    },
    {
      key: 'touchpointCount',
      label: 'Touchpoints',
      sortable: true,
      align: 'right',
      render: (r) => formatNumber(r.touchpointCount),
    },
    {
      key: 'totalRevenue',
      label: 'Closed Rev.',
      sortable: true,
      align: 'right',
      render: (r) => (
        <span className="font-semibold">{formatCurrency(r.totalRevenue)}</span>
      ),
    },
    {
      key: 'lifecycleStatus',
      label: 'Lifecycle Status',
      sortable: true,
      render: (r) => <Badge status={r.lifecycleStatus} dot>{r.lifecycleStatus}</Badge>,
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
            onClick={() => navigate(`/contacts/${r.id}`)}
          >
            Details
          </Button>
          <Button
            variant="outline"
            size="sm"
            icon={Route}
            onClick={() => navigate(`/customer-journey?contactId=${r.id}`)}
          >
            Journey
          </Button>
        </div>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title="Contact Management"
        description="Unified directory of synthetic CRM contacts, acquisition sources, and lifecycle stages."
        badge={<Badge variant="primary">{contacts.length} Contacts</Badge>}
      />

      <FilterBar
        searchValue={search}
        onSearchChange={setSearch}
        searchPlaceholder="Search contact ID, name, email, or company..."
        filters={[
          {
            id: 'lifecycle',
            label: 'Lifecycle',
            value: lifecycleFilter,
            onChange: setLifecycleFilter,
            options: [
              { value: 'all', label: 'All Stages' },
              { value: 'Customer', label: 'Customer' },
              { value: 'Opportunity', label: 'Opportunity' },
              { value: 'Lead', label: 'Lead' },
              { value: 'Subscriber', label: 'Subscriber' },
            ],
          },
        ]}
        onReset={() => {
          setSearch('')
          setLifecycleFilter('all')
        }}
      />

      <DataTable
        columns={columns}
        data={filtered}
        loading={loading}
        pageSize={10}
        onRowClick={(row) => navigate(`/contacts/${row.id}`)}
      />
    </div>
  )
}

