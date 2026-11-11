import { useEffect, useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'
import { CheckCircle2, Edit3, Eye, Plus, Sparkles, TrendingUp } from 'lucide-react'
import {
  Badge,
  Button,
  FilterBar,
  KpiCard,
  PageHeader,
} from '../../components/common'
import {
  FormField,
  SelectInput,
  TextInput,
} from '../../components/forms/FormField'
import { Modal } from '../../components/modals/Modal'
import { DataTable } from '../../components/tables/DataTable'
import { useToast } from '../../hooks/useToast'
import { campaignService } from '../../services/campaignService'
import { contactService } from '../../services/contactService'
import { formatDate, formatNumber, formatPercent } from '../../utils/formatters'

export function LeadsPage() {
  const { showToast } = useToast()
  const [leads, setLeads] = useState([])
  const [contacts, setContacts] = useState([])
  const [campaigns, setCampaigns] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [detailTarget, setDetailTarget] = useState(null)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm()

  const fetchLeadResources = () =>
    Promise.all([
      contactService.listLeads(),
      contactService.listContacts(),
      campaignService.listCampaigns(),
    ])

  const loadData = async () => {
    setLoading(true)
    const [leadData, conData, cmpData] = await fetchLeadResources()
    setLeads(leadData)
    setContacts(conData)
    setCampaigns(cmpData)
    setLoading(false)
  }

  useEffect(() => {
    let active = true
    fetchLeadResources().then(([leadData, conData, cmpData]) => {
      if (!active) return
      setLeads(leadData)
      setContacts(conData)
      setCampaigns(cmpData)
      setLoading(false)
    })
    return () => {
      active = false
    }
  }, [])

  const openModal = (item = null) => {
    setEditing(item)
    reset(
      item || {
        contactId: contacts[0]?.id || '',
        campaignId: campaigns[0]?.id || '',
        source: 'Paid Search',
        score: 75,
        createdDate: '2026-11-11',
        status: 'New',
      }
    )
    setFormOpen(true)
  }

  const onSubmit = async (values) => {
    await contactService.saveLead(values, editing?.id || null)
    showToast({
      type: 'success',
      title: editing ? 'Lead Updated' : 'Lead Added',
      message: 'Lead record saved cleanly.',
    })
    setFormOpen(false)
    await loadData()
  }

  const filtered = useMemo(() => {
    return leads.filter((l) => {
      const q = search.toLowerCase()
      const matchesSearch =
        !q ||
        l.id.toLowerCase().includes(q) ||
        l.contactName.toLowerCase().includes(q) ||
        l.campaignName.toLowerCase().includes(q)
      const matchesStatus = statusFilter === 'all' || l.status === statusFilter
      return matchesSearch && matchesStatus
    })
  }, [leads, search, statusFilter])

  const convertedCount = leads.filter((l) => l.status === 'Converted').length
  const qualifiedCount = leads.filter((l) => l.status === 'Qualified').length
  const avgScore =
    leads.length > 0
      ? Math.round(leads.reduce((s, l) => s + Number(l.score || 0), 0) / leads.length)
      : 0

  const columns = [
    {
      key: 'id',
      label: 'Lead ID',
      sortable: true,
      render: (r) => <span className="font-mono text-xs font-semibold text-blue-700">{r.id}</span>,
    },
    {
      key: 'contactId',
      label: 'Contact',
      sortable: true,
      render: (r) => (
        <div>
          <p className="font-semibold text-slate-900">{r.contactName}</p>
          <p className="font-mono text-[11px] text-slate-500">{r.contactId}</p>
        </div>
      ),
    },
    {
      key: 'campaignId',
      label: 'Campaign',
      sortable: true,
      render: (r) => (
        <div>
          <p className="text-xs font-medium text-slate-800">{r.campaignName}</p>
          <p className="font-mono text-[11px] text-slate-500">{r.campaignId}</p>
        </div>
      ),
    },
    { key: 'source', label: 'Source', sortable: true },
    {
      key: 'score',
      label: 'Lead Score',
      sortable: true,
      align: 'right',
      render: (r) => (
        <span className="inline-flex items-center rounded-md bg-slate-100 px-2 py-0.5 text-xs font-bold text-slate-800 tabular-nums">
          {r.score}
        </span>
      ),
    },
    {
      key: 'createdDate',
      label: 'Created Date',
      sortable: true,
      render: (r) => formatDate(r.createdDate),
    },
    {
      key: 'status',
      label: 'Lead Status',
      sortable: true,
      render: (r) => (
        <Badge
          status={
            r.status === 'Converted'
              ? 'Active'
              : r.status === 'Disqualified'
                ? 'Closed Lost'
                : r.status
          }
          dot
        >
          {r.status}
        </Badge>
      ),
    },
    {
      key: 'actions',
      label: 'Actions',
      align: 'right',
      render: (r) => (
        <div className="inline-flex items-center gap-1">
          <button
            type="button"
            title="View lead"
            onClick={() => setDetailTarget(r)}
            className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100 hover:text-blue-600 cursor-pointer"
          >
            <Eye className="h-4 w-4" />
          </button>
          <button
            type="button"
            title="Edit lead"
            onClick={() => openModal(r)}
            className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-900 cursor-pointer"
          >
            <Edit3 className="h-4 w-4" />
          </button>
        </div>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title="Lead Management"
        description="Track lead scoring, source attribution, qualification statuses, and conversion velocity."
        badge={<Badge variant="primary">{leads.length} Leads</Badge>}
        actions={
          <Button icon={Plus} onClick={() => openModal()}>
            Add Lead
          </Button>
        }
      />

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          title="Total Leads"
          value={formatNumber(leads.length)}
          icon={Sparkles}
          accent="blue"
        />
        <KpiCard
          title="Converted Leads"
          value={formatNumber(convertedCount)}
          changeLabel={`${qualifiedCount} currently qualified`}
          icon={CheckCircle2}
          accent="emerald"
        />
        <KpiCard
          title="Conversion Rate"
          value={formatPercent(
            leads.length > 0 ? (convertedCount / leads.length) * 100 : 0
          )}
          changeLabel="Converted / Total Leads"
          icon={TrendingUp}
          accent="violet"
        />
        <KpiCard
          title="Average Lead Score"
          value={`${avgScore} / 100`}
          changeLabel="Intent & firmographic fit"
          icon={Sparkles}
          accent="amber"
        />
      </section>

      <FilterBar
        searchValue={search}
        onSearchChange={setSearch}
        searchPlaceholder="Search lead ID, contact, or campaign..."
        filters={[
          {
            id: 'lead-status',
            label: 'Status',
            value: statusFilter,
            onChange: setStatusFilter,
            options: [
              { value: 'all', label: 'All Statuses' },
              { value: 'Converted', label: 'Converted' },
              { value: 'Qualified', label: 'Qualified' },
              { value: 'New', label: 'New' },
              { value: 'Disqualified', label: 'Disqualified' },
            ],
          },
        ]}
        onReset={() => {
          setSearch('')
          setStatusFilter('all')
        }}
      />

      <DataTable columns={columns} data={filtered} loading={loading} pageSize={10} />

      <Modal
        isOpen={Boolean(detailTarget)}
        onClose={() => setDetailTarget(null)}
        title={`Lead ${detailTarget?.id}`}
        subtitle={detailTarget?.contactName}
      >
        {detailTarget && (
          <div className="space-y-2.5 text-xs">
            <div className="flex justify-between border-b border-slate-100 pb-2">
              <span className="text-slate-500">Contact ID</span>
              <span className="font-mono font-semibold">{detailTarget.contactId}</span>
            </div>
            <div className="flex justify-between border-b border-slate-100 pb-2">
              <span className="text-slate-500">Campaign</span>
              <span className="font-semibold">{detailTarget.campaignName}</span>
            </div>
            <div className="flex justify-between border-b border-slate-100 pb-2">
              <span className="text-slate-500">Lead Score</span>
              <span className="font-bold">{detailTarget.score}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Status</span>
              <Badge status={detailTarget.status}>{detailTarget.status}</Badge>
            </div>
          </div>
        )}
      </Modal>

      <Modal
        isOpen={formOpen}
        onClose={() => setFormOpen(false)}
        title={editing ? `Edit ${editing.id}` : 'Add New Lead'}
        footer={
          <>
            <Button variant="outline" onClick={() => setFormOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" form="lead-form">
              Save Lead
            </Button>
          </>
        }
      >
        <form id="lead-form" onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <FormField label="Contact" htmlFor="lead-contact">
              <SelectInput
                id="lead-contact"
                options={contacts.map((c) => ({ value: c.id, label: `${c.id} · ${c.name}` }))}
                {...register('contactId')}
              />
            </FormField>
            <FormField label="Campaign" htmlFor="lead-campaign">
              <SelectInput
                id="lead-campaign"
                options={campaigns.map((c) => ({ value: c.id, label: c.name }))}
                {...register('campaignId')}
              />
            </FormField>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <FormField label="Source" htmlFor="lead-source">
              <SelectInput
                id="lead-source"
                options={[
                  { value: 'Paid Search', label: 'Paid Search' },
                  { value: 'Paid Social', label: 'Paid Social' },
                  { value: 'Email', label: 'Email' },
                  { value: 'Display', label: 'Display' },
                  { value: 'Events', label: 'Events' },
                  { value: 'Organic', label: 'Organic' },
                ]}
                {...register('source')}
              />
            </FormField>

            <FormField label="Lead Score (0-100)" htmlFor="lead-score" error={errors.score?.message}>
              <TextInput
                id="lead-score"
                type="number"
                min="0"
                max="100"
                {...register('score', {
                  min: { value: 0, message: 'Min 0' },
                  max: { value: 100, message: 'Max 100' },
                })}
              />
            </FormField>

            <FormField label="Status" htmlFor="lead-status-in">
              <SelectInput
                id="lead-status-in"
                options={[
                  { value: 'New', label: 'New' },
                  { value: 'Qualified', label: 'Qualified' },
                  { value: 'Converted', label: 'Converted' },
                  { value: 'Disqualified', label: 'Disqualified' },
                ]}
                {...register('status')}
              />
            </FormField>
          </div>

          <FormField label="Created Date" htmlFor="lead-date">
            <TextInput id="lead-date" type="date" {...register('createdDate')} />
          </FormField>
        </form>
      </Modal>
    </div>
  )
}
