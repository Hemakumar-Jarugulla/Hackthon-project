import { useEffect, useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'
import { Edit3, Plus } from 'lucide-react'
import {
  Badge,
  Button,
  FilterBar,
  PageHeader,
} from '../../components/common'
import {
  FormField,
  SelectInput,
  TextArea,
  TextInput,
} from '../../components/forms/FormField'
import { Modal } from '../../components/modals/Modal'
import { DataTable } from '../../components/tables/DataTable'
import { useToast } from '../../hooks/useToast'
import { campaignService } from '../../services/campaignService'
import { formatDate } from '../../utils/formatters'

export function CreativesPage() {
  const { showToast } = useToast()
  const [creatives, setCreatives] = useState([])
  const [campaigns, setCampaigns] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState(null)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm()

  const fetchCreativeResources = () =>
    Promise.all([
      campaignService.listCreatives(),
      campaignService.listCampaigns(),
    ])

  const loadCreatives = async () => {
    setLoading(true)
    const [crtList, cmpList] = await fetchCreativeResources()
    setCreatives(crtList)
    setCampaigns(cmpList)
    setLoading(false)
  }

  useEffect(() => {
    let active = true
    fetchCreativeResources().then(([crtList, cmpList]) => {
      if (!active) return
      setCreatives(crtList)
      setCampaigns(cmpList)
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
        name: '',
        campaignId: campaigns[0]?.id || '',
        type: 'Responsive Search Ad',
        description: '',
        startDate: '2026-01-01',
        endDate: '2026-12-31',
        status: 'Active',
      }
    )
    setFormOpen(true)
  }

  const onSubmit = async (values) => {
    await campaignService.saveCreative(values, editing?.id || null)
    showToast({
      type: 'success',
      title: editing ? 'Creative Updated' : 'Creative Created',
      message: `${values.name} saved.`,
    })
    setFormOpen(false)
    await loadCreatives()
  }

  const filtered = useMemo(() => {
    return creatives.filter((c) => {
      const q = search.toLowerCase()
      const matchesSearch =
        !q ||
        c.id.toLowerCase().includes(q) ||
        c.name.toLowerCase().includes(q) ||
        c.campaignId.toLowerCase().includes(q)
      const matchesStatus = statusFilter === 'all' || c.status === statusFilter
      return matchesSearch && matchesStatus
    })
  }, [creatives, search, statusFilter])

  const columns = [
    {
      key: 'id',
      label: 'Creative ID',
      sortable: true,
      render: (r) => <span className="font-mono text-xs font-semibold text-blue-700">{r.id}</span>,
    },
    {
      key: 'name',
      label: 'Creative Name',
      sortable: true,
      render: (r) => (
        <div>
          <p className="font-semibold text-slate-900">{r.name}</p>
          <p className="text-xs text-slate-500 line-clamp-1">{r.description}</p>
        </div>
      ),
    },
    {
      key: 'campaignId',
      label: 'Campaign ID',
      sortable: true,
      render: (r) => (
        <div>
          <span className="font-mono text-xs text-slate-700">{r.campaignId}</span>
          <p className="text-[11px] text-slate-500">{r.campaignName}</p>
        </div>
      ),
    },
    { key: 'type', label: 'Creative Type', sortable: true },
    {
      key: 'startDate',
      label: 'Start Date',
      sortable: true,
      render: (r) => formatDate(r.startDate),
    },
    {
      key: 'endDate',
      label: 'End Date',
      sortable: true,
      render: (r) => formatDate(r.endDate),
    },
    {
      key: 'status',
      label: 'Status',
      sortable: true,
      render: (r) => <Badge status={r.status} dot>{r.status}</Badge>,
    },
    {
      key: 'actions',
      label: 'Actions',
      align: 'right',
      render: (r) => (
        <button
          type="button"
          title="Edit creative"
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
        title="Creative Management"
        description="Track ad formats, messaging variants, flight schedules, and campaign associations."
        badge={<Badge variant="primary">{creatives.length} Creatives</Badge>}
        actions={
          <Button icon={Plus} onClick={() => openModal()}>
            New Creative
          </Button>
        }
      />

      <FilterBar
        searchValue={search}
        onSearchChange={setSearch}
        searchPlaceholder="Search creative ID, name, or campaign..."
        filters={[
          {
            id: 'crt-status',
            label: 'Status',
            value: statusFilter,
            onChange: setStatusFilter,
            options: [
              { value: 'all', label: 'All Statuses' },
              { value: 'Active', label: 'Active' },
              { value: 'Completed', label: 'Completed' },
              { value: 'Paused', label: 'Paused' },
              { value: 'Draft', label: 'Draft' },
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
        isOpen={formOpen}
        onClose={() => setFormOpen(false)}
        title={editing ? `Edit ${editing.id}` : 'Create Ad Creative'}
        footer={
          <>
            <Button variant="outline" onClick={() => setFormOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" form="creative-form">
              Save Creative
            </Button>
          </>
        }
      >
        <form id="creative-form" onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <FormField label="Creative Name" htmlFor="crt-name" required error={errors.name?.message}>
            <TextInput
              id="crt-name"
              placeholder="e.g., Search RSA · Attribution ROI"
              hasError={Boolean(errors.name)}
              {...register('name', { required: 'Creative name is required.' })}
            />
          </FormField>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <FormField label="Campaign" htmlFor="crt-campaign">
              <SelectInput
                id="crt-campaign"
                options={campaigns.map((c) => ({ value: c.id, label: `${c.id} · ${c.name}` }))}
                {...register('campaignId')}
              />
            </FormField>

            <FormField label="Creative Type" htmlFor="crt-type">
              <SelectInput
                id="crt-type"
                options={[
                  { value: 'Responsive Search Ad', label: 'Responsive Search Ad' },
                  { value: 'Carousel Ad', label: 'Carousel Ad' },
                  { value: 'Video Ad', label: 'Video Ad' },
                  { value: 'Email Template', label: 'Email Template' },
                  { value: 'Display Banner', label: 'Display Banner' },
                  { value: 'Event Collateral', label: 'Event Collateral' },
                  { value: 'Editorial Guide', label: 'Editorial Guide' },
                ]}
                {...register('type')}
              />
            </FormField>
          </div>

          <FormField label="Description" htmlFor="crt-desc">
            <TextArea id="crt-desc" {...register('description')} />
          </FormField>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <FormField label="Start Date" htmlFor="crt-start">
              <TextInput id="crt-start" type="date" {...register('startDate')} />
            </FormField>
            <FormField label="End Date" htmlFor="crt-end">
              <TextInput id="crt-end" type="date" {...register('endDate')} />
            </FormField>
            <FormField label="Status" htmlFor="crt-status-in">
              <SelectInput
                id="crt-status-in"
                options={[
                  { value: 'Active', label: 'Active' },
                  { value: 'Paused', label: 'Paused' },
                  { value: 'Completed', label: 'Completed' },
                  { value: 'Draft', label: 'Draft' },
                ]}
                {...register('status')}
              />
            </FormField>
          </div>
        </form>
      </Modal>
    </div>
  )
}
