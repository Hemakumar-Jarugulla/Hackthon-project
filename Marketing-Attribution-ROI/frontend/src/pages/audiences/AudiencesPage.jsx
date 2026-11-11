import { useEffect, useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'
import { Edit3, Eye, Plus } from 'lucide-react'
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
import { formatNumber } from '../../utils/formatters'

export function AudiencesPage() {
  const { showToast } = useToast()
  const [audiences, setAudiences] = useState([])
  const [campaigns, setCampaigns] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState('all')
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [detailTarget, setDetailTarget] = useState(null)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm()

  const fetchAudiences = () =>
    Promise.all([
      campaignService.listAudiences(),
      campaignService.listCampaigns(),
    ])

  const loadAudiences = async () => {
    setLoading(true)
    const [audList, cmpList] = await fetchAudiences()
    setAudiences(audList)
    setCampaigns(cmpList)
    setLoading(false)
  }

  useEffect(() => {
    let active = true
    fetchAudiences().then(([audList, cmpList]) => {
      if (!active) return
      setAudiences(audList)
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
        type: 'Account-Based (ABM)',
        size: 15000,
        campaignId: campaigns[0]?.id || '',
        status: 'Active',
        criteria: '',
      }
    )
    setFormOpen(true)
  }

  const onSubmit = async (values) => {
    await campaignService.saveAudience(values, editing?.id || null)
    showToast({
      type: 'success',
      title: editing ? 'Audience Updated' : 'Audience Created',
      message: `${values.name} saved.`,
    })
    setFormOpen(false)
    await loadAudiences()
  }

  const filtered = useMemo(() => {
    return audiences.filter((a) => {
      const q = search.toLowerCase()
      const matchesSearch =
        !q ||
        a.id.toLowerCase().includes(q) ||
        a.name.toLowerCase().includes(q) ||
        a.campaignName.toLowerCase().includes(q)
      const matchesType = typeFilter === 'all' || a.type === typeFilter
      return matchesSearch && matchesType
    })
  }, [audiences, search, typeFilter])

  const columns = [
    {
      key: 'id',
      label: 'Audience ID',
      sortable: true,
      render: (r) => <span className="font-mono text-xs font-semibold text-blue-700">{r.id}</span>,
    },
    {
      key: 'name',
      label: 'Audience Name',
      sortable: true,
      render: (r) => <span className="font-semibold text-slate-900">{r.name}</span>,
    },
    { key: 'type', label: 'Audience Type', sortable: true },
    {
      key: 'size',
      label: 'Audience Size',
      sortable: true,
      align: 'right',
      render: (r) => <span className="font-semibold">{formatNumber(r.size)}</span>,
    },
    {
      key: 'campaignName',
      label: 'Campaign Association',
      sortable: true,
      render: (r) => (
        <div>
          <p className="text-xs font-medium text-slate-900">{r.campaignName}</p>
          <p className="font-mono text-[11px] text-slate-500">{r.campaignId}</p>
        </div>
      ),
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
        <div className="inline-flex items-center gap-1">
          <button
            type="button"
            title="Inspect segment"
            onClick={() => setDetailTarget(r)}
            className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100 hover:text-blue-600 cursor-pointer"
          >
            <Eye className="h-4 w-4" />
          </button>
          <button
            type="button"
            title="Edit audience"
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
        title="Audience Management"
        description="Manage target segments, reach estimates, targeting criteria, and campaign bindings."
        badge={<Badge variant="primary">{audiences.length} Segments</Badge>}
        actions={
          <Button icon={Plus} onClick={() => openModal()}>
            Create Audience
          </Button>
        }
      />

      <FilterBar
        searchValue={search}
        onSearchChange={setSearch}
        searchPlaceholder="Search audience ID, name, or campaign..."
        filters={[
          {
            id: 'aud-type',
            label: 'Type',
            value: typeFilter,
            onChange: setTypeFilter,
            options: [
              { value: 'all', label: 'All Types' },
              { value: 'Intent Keywords', label: 'Intent Keywords' },
              { value: 'Account-Based (ABM)', label: 'Account-Based (ABM)' },
              { value: 'Lifecycle Segment', label: 'Lifecycle Segment' },
              { value: 'Retargeting Pool', label: 'Retargeting Pool' },
              { value: 'Geo & Firmographic', label: 'Geo & Firmographic' },
              { value: 'Organic Audience', label: 'Organic Audience' },
            ],
          },
        ]}
        onReset={() => {
          setSearch('')
          setTypeFilter('all')
        }}
      />

      <DataTable columns={columns} data={filtered} loading={loading} pageSize={10} />

      <Modal
        isOpen={Boolean(detailTarget)}
        onClose={() => setDetailTarget(null)}
        title={detailTarget?.name}
        subtitle={`${detailTarget?.id} · ${detailTarget?.type}`}
      >
        {detailTarget && (
          <div className="space-y-3 text-xs">
            <div className="flex justify-between border-b border-slate-100 pb-2">
              <span className="text-slate-500">Estimated Reach</span>
              <span className="font-semibold text-slate-900">
                {formatNumber(detailTarget.size)} contacts
              </span>
            </div>
            <div className="flex justify-between border-b border-slate-100 pb-2">
              <span className="text-slate-500">Linked Campaign</span>
              <span className="font-semibold text-slate-900">
                {detailTarget.campaignName} ({detailTarget.campaignId})
              </span>
            </div>
            <div>
              <p className="font-semibold text-slate-700 mb-1">Targeting Criteria</p>
              <p className="rounded-lg bg-slate-50 border border-slate-200 p-3 text-slate-600 leading-relaxed">
                {detailTarget.criteria || 'No criteria notes defined.'}
              </p>
            </div>
          </div>
        )}
      </Modal>

      <Modal
        isOpen={formOpen}
        onClose={() => setFormOpen(false)}
        title={editing ? `Edit ${editing.id}` : 'Create Audience Segment'}
        footer={
          <>
            <Button variant="outline" onClick={() => setFormOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" form="audience-form">
              Save Audience
            </Button>
          </>
        }
      >
        <form id="audience-form" onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <FormField label="Audience Name" htmlFor="aud-name" required error={errors.name?.message}>
            <TextInput
              id="aud-name"
              hasError={Boolean(errors.name)}
              {...register('name', { required: 'Audience name is required.' })}
            />
          </FormField>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <FormField label="Audience Type" htmlFor="aud-type-in">
              <SelectInput
                id="aud-type-in"
                options={[
                  { value: 'Intent Keywords', label: 'Intent Keywords' },
                  { value: 'Account-Based (ABM)', label: 'Account-Based (ABM)' },
                  { value: 'Lifecycle Segment', label: 'Lifecycle Segment' },
                  { value: 'Retargeting Pool', label: 'Retargeting Pool' },
                  { value: 'Geo & Firmographic', label: 'Geo & Firmographic' },
                  { value: 'Organic Audience', label: 'Organic Audience' },
                ]}
                {...register('type')}
              />
            </FormField>
            <FormField label="Audience Size" htmlFor="aud-size">
              <TextInput id="aud-size" type="number" min="0" {...register('size')} />
            </FormField>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <FormField label="Associated Campaign" htmlFor="aud-cmp">
              <SelectInput
                id="aud-cmp"
                options={campaigns.map((c) => ({ value: c.id, label: c.name }))}
                {...register('campaignId')}
              />
            </FormField>
            <FormField label="Status" htmlFor="aud-status">
              <SelectInput
                id="aud-status"
                options={[
                  { value: 'Active', label: 'Active' },
                  { value: 'Paused', label: 'Paused' },
                ]}
                {...register('status')}
              />
            </FormField>
          </div>

          <FormField label="Segment Criteria" htmlFor="aud-criteria">
            <TextArea id="aud-criteria" {...register('criteria')} />
          </FormField>
        </form>
      </Modal>
    </div>
  )
}
