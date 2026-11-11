import { useEffect, useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'
import { Edit3, Kanban, Plus, Table2 } from 'lucide-react'
import {
  Badge,
  Button,
  FilterBar,
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
import { contactService } from '../../services/contactService'
import { formatCurrency, formatDate } from '../../utils/formatters'

const PIPELINE_STAGES = [
  'New',
  'Qualification',
  'Proposal',
  'Negotiation',
  'Closed Won',
  'Closed Lost',
]

export function OpportunitiesPage() {
  const { showToast } = useToast()
  const [opportunities, setOpportunities] = useState([])
  const [leads, setLeads] = useState([])
  const [contacts, setContacts] = useState([])
  const [loading, setLoading] = useState(true)
  const [viewMode, setViewMode] = useState('pipeline')
  const [search, setSearch] = useState('')
  const [stageFilter, setStageFilter] = useState('all')
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState(null)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm()

  const fetchOpportunityResources = () =>
    Promise.all([
      contactService.listOpportunities(),
      contactService.listLeads(),
      contactService.listContacts(),
    ])

  const loadData = async () => {
    setLoading(true)
    const [oppData, leadData, conData] = await fetchOpportunityResources()
    setOpportunities(oppData)
    setLeads(leadData)
    setContacts(conData)
    setLoading(false)
  }

  useEffect(() => {
    let active = true
    fetchOpportunityResources().then(([oppData, leadData, conData]) => {
      if (!active) return
      setOpportunities(oppData)
      setLeads(leadData)
      setContacts(conData)
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
        leadId: leads[0]?.id || '',
        contactId: contacts[0]?.id || '',
        name: '',
        stage: 'New',
        expectedRevenue: 50000,
        actualRevenue: 0,
        closingDate: '2026-12-15',
        status: 'Open',
      }
    )
    setFormOpen(true)
  }

  const onSubmit = async (values) => {
    const derivedStatus =
      values.stage === 'Closed Won'
        ? 'Won'
        : values.stage === 'Closed Lost'
          ? 'Lost'
          : 'Open'
    await contactService.saveOpportunity(
      { ...values, status: derivedStatus },
      editing?.id || null
    )
    showToast({
      type: 'success',
      title: editing ? 'Opportunity Updated' : 'Opportunity Created',
      message: `${values.name} saved in ${values.stage}.`,
    })
    setFormOpen(false)
    await loadData()
  }

  const filtered = useMemo(() => {
    return opportunities.filter((o) => {
      const q = search.toLowerCase()
      const matchesSearch =
        !q ||
        o.id.toLowerCase().includes(q) ||
        o.name.toLowerCase().includes(q) ||
        o.contactName.toLowerCase().includes(q)
      const matchesStage = stageFilter === 'all' || o.stage === stageFilter
      return matchesSearch && matchesStage
    })
  }, [opportunities, search, stageFilter])

  const columns = [
    {
      key: 'id',
      label: 'Opportunity ID',
      sortable: true,
      render: (r) => <span className="font-mono text-xs font-semibold text-blue-700">{r.id}</span>,
    },
    {
      key: 'name',
      label: 'Opportunity Name',
      sortable: true,
      render: (r) => <span className="font-semibold text-slate-900">{r.name}</span>,
    },
    { key: 'leadId', label: 'Lead ID', sortable: true },
    {
      key: 'contactName',
      label: 'Contact',
      sortable: true,
      render: (r) => (
        <div>
          <p className="text-xs font-medium text-slate-900">{r.contactName}</p>
          <p className="font-mono text-[11px] text-slate-500">{r.contactId}</p>
        </div>
      ),
    },
    {
      key: 'stage',
      label: 'Stage',
      sortable: true,
      render: (r) => <Badge status={r.stage} dot>{r.stage}</Badge>,
    },
    {
      key: 'expectedRevenue',
      label: 'Expected Rev.',
      sortable: true,
      align: 'right',
      render: (r) => formatCurrency(r.expectedRevenue),
    },
    {
      key: 'actualRevenue',
      label: 'Actual Rev.',
      sortable: true,
      align: 'right',
      render: (r) => (
        <span className="font-semibold text-emerald-700">
          {formatCurrency(r.actualRevenue)}
        </span>
      ),
    },
    {
      key: 'closingDate',
      label: 'Closing Date',
      sortable: true,
      render: (r) => formatDate(r.closingDate),
    },
    {
      key: 'status',
      label: 'Status',
      sortable: true,
      render: (r) => (
        <Badge status={r.status === 'Won' ? 'Active' : r.status === 'Lost' ? 'Closed Lost' : 'Pending'}>
          {r.status}
        </Badge>
      ),
    },
    {
      key: 'actions',
      label: 'Actions',
      align: 'right',
      render: (r) => (
        <button
          type="button"
          title="Edit opportunity"
          onClick={() => openModal(r)}
          className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-900 cursor-pointer"
        >
          <Edit3 className="h-4 w-4" />
        </button>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title="Opportunity Management"
        description="Track B2B pipeline stages from New and Qualification through Closed Won and Closed Lost."
        badge={<Badge variant="primary">{opportunities.length} Opportunities</Badge>}
        actions={
          <>
            <div className="inline-flex rounded-lg border border-slate-200 bg-white p-0.5">
              <button
                type="button"
                onClick={() => setViewMode('pipeline')}
                className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-semibold cursor-pointer ${
                  viewMode === 'pipeline'
                    ? 'bg-blue-600 text-white'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Kanban className="h-3.5 w-3.5" />
                Pipeline Board
              </button>
              <button
                type="button"
                onClick={() => setViewMode('table')}
                className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-semibold cursor-pointer ${
                  viewMode === 'table'
                    ? 'bg-blue-600 text-white'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Table2 className="h-3.5 w-3.5" />
                Table View
              </button>
            </div>
            <Button icon={Plus} onClick={() => openModal()}>
              New Opportunity
            </Button>
          </>
        }
      />

      <FilterBar
        searchValue={search}
        onSearchChange={setSearch}
        searchPlaceholder="Search opportunity ID, deal name, or contact..."
        filters={[
          {
            id: 'opp-stage',
            label: 'Stage',
            value: stageFilter,
            onChange: setStageFilter,
            options: [
              { value: 'all', label: 'All Stages' },
              ...PIPELINE_STAGES.map((st) => ({ value: st, label: st })),
            ],
          },
        ]}
        onReset={() => {
          setSearch('')
          setStageFilter('all')
        }}
      />

      {viewMode === 'pipeline' ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-6">
          {PIPELINE_STAGES.map((stage) => {
            const stageDeals = filtered.filter((o) => o.stage === stage)
            const stageSum = stageDeals.reduce(
              (s, o) => s + (o.actualRevenue || o.expectedRevenue || 0),
              0
            )
            return (
              <div
                key={stage}
                className="flex flex-col rounded-xl border border-slate-200 bg-slate-100/70 p-3"
              >
                <div className="mb-3 flex items-center justify-between">
                  <div>
                    <p className="text-xs font-bold text-slate-900">{stage}</p>
                    <p className="text-[11px] font-semibold text-slate-500 tabular-nums">
                      {formatCurrency(stageSum)}
                    </p>
                  </div>
                  <Badge status={stage}>{stageDeals.length}</Badge>
                </div>

                <div className="space-y-2.5 flex-1">
                  {stageDeals.length === 0 ? (
                    <div className="rounded-lg border border-dashed border-slate-300 py-6 text-center text-[11px] text-slate-400">
                      No deals
                    </div>
                  ) : (
                    stageDeals.map((deal) => (
                      <button
                        key={deal.id}
                        type="button"
                        onClick={() => openModal(deal)}
                        className="w-full rounded-lg border border-slate-200 bg-white p-3 text-left shadow-xs hover:border-blue-400 cursor-pointer"
                      >
                        <p className="font-mono text-[10px] font-semibold text-blue-700">
                          {deal.id}
                        </p>
                        <p className="mt-1 text-xs font-semibold text-slate-900 leading-snug">
                          {deal.name}
                        </p>
                        <p className="mt-1 text-[11px] text-slate-500">
                          {deal.contactName}
                        </p>
                        <div className="mt-2 flex items-center justify-between border-t border-slate-100 pt-2 text-[11px]">
                          <span className="font-bold text-slate-900 tabular-nums">
                            {formatCurrency(
                              deal.stage === 'Closed Won'
                                ? deal.actualRevenue
                                : deal.expectedRevenue
                            )}
                          </span>
                          <span className="text-slate-400">
                            {formatDate(deal.closingDate)}
                          </span>
                        </div>
                      </button>
                    ))
                  )}
                </div>
              </div>
            )
          })}
        </div>
      ) : (
        <DataTable columns={columns} data={filtered} loading={loading} pageSize={10} />
      )}

      <Modal
        isOpen={formOpen}
        onClose={() => setFormOpen(false)}
        title={editing ? `Edit ${editing.id}` : 'Create Opportunity'}
        footer={
          <>
            <Button variant="outline" onClick={() => setFormOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" form="opp-form">
              Save Opportunity
            </Button>
          </>
        }
      >
        <form id="opp-form" onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <FormField
            label="Opportunity Name"
            htmlFor="opp-name"
            required
            error={errors.name?.message}
          >
            <TextInput
              id="opp-name"
              hasError={Boolean(errors.name)}
              {...register('name', { required: 'Opportunity name is required.' })}
            />
          </FormField>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <FormField label="Lead" htmlFor="opp-lead">
              <SelectInput
                id="opp-lead"
                options={leads.map((l) => ({ value: l.id, label: l.id }))}
                {...register('leadId')}
              />
            </FormField>
            <FormField label="Contact" htmlFor="opp-con">
              <SelectInput
                id="opp-con"
                options={contacts.map((c) => ({ value: c.id, label: `${c.id} · ${c.name}` }))}
                {...register('contactId')}
              />
            </FormField>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <FormField label="Pipeline Stage" htmlFor="opp-stage-in">
              <SelectInput
                id="opp-stage-in"
                options={PIPELINE_STAGES.map((st) => ({ value: st, label: st }))}
                {...register('stage')}
              />
            </FormField>
            <FormField label="Closing Date" htmlFor="opp-close">
              <TextInput id="opp-close" type="date" {...register('closingDate')} />
            </FormField>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <FormField label="Expected Revenue (USD)" htmlFor="opp-exp">
              <TextInput id="opp-exp" type="number" min="0" {...register('expectedRevenue')} />
            </FormField>
            <FormField label="Actual Revenue (USD)" htmlFor="opp-act">
              <TextInput id="opp-act" type="number" min="0" {...register('actualRevenue')} />
            </FormField>
          </div>
        </form>
      </Modal>
    </div>
  )
}
