import { useEffect, useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'
import {
  AlertTriangle,
  Archive,
  Download,
  Edit3,
  Eye,
  Plus,
} from 'lucide-react'
import {
  Badge,
  Button,
  ErrorState,
  FilterBar,
  PageHeader,
} from '../../components/common'
import {
  FormField,
  SelectInput,
  TextArea,
  TextInput,
} from '../../components/forms/FormField'
import { ConfirmDialog } from '../../components/modals/ConfirmDialog'
import { Modal } from '../../components/modals/Modal'
import { DataTable } from '../../components/tables/DataTable'
import { useApp } from '../../hooks/useApp'
import { useToast } from '../../hooks/useToast'
import { campaignService } from '../../services/campaignService'
import { exportToCsv } from '../../utils/exportUtils'
import {
  formatCurrency,
  formatDate,
  formatNumber,
  formatPercent,
} from '../../utils/formatters'

export function CampaignsPage() {
  const navigate = useNavigate()
  const { dateRange } = useApp()
  const { showToast } = useToast()

  const [campaigns, setCampaigns] = useState([])
  const [channels, setChannels] = useState([])
  const [creatives, setCreatives] = useState([])
  const [audiences, setAudiences] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [channelFilter, setChannelFilter] = useState('all')
  const [dateFrom, setDateFrom] = useState('')

  const [formOpen, setFormOpen] = useState(false)
  const [editingCampaign, setEditingCampaign] = useState(null)
  const [archiveTarget, setArchiveTarget] = useState(null)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm()

  const fetchCampaignResources = () =>
    Promise.all([
      campaignService.listCampaigns({ dateRange }),
      campaignService.listChannels(dateRange),
      campaignService.listCreatives(),
      campaignService.listAudiences(),
    ])

  const loadData = async () => {
    try {
      setLoading(true)
      setError(null)
      const [cmpData, chData, crtData, audData] = await fetchCampaignResources()
      setCampaigns(cmpData)
      setChannels(chData)
      setCreatives(crtData)
      setAudiences(audData)
    } catch (err) {
      setError(err.message || 'Failed to load campaigns.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let active = true
    fetchCampaignResources()
      .then(([cmpData, chData, crtData, audData]) => {
        if (!active) return
        setError(null)
        setCampaigns(cmpData)
        setChannels(chData)
        setCreatives(crtData)
        setAudiences(audData)
        setLoading(false)
      })
      .catch((err) => {
        if (!active) return
        setError(err.message || 'Failed to load campaigns.')
        setLoading(false)
      })
    return () => {
      active = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dateRange])

  const openCreateModal = () => {
    setEditingCampaign(null)
    reset({
      name: '',
      description: '',
      channelId: channels[0]?.id || '',
      creativeId: creatives[0]?.id || '',
      audienceId: audiences[0]?.id || '',
      budget: '',
      currency: 'USD',
      startDate: '2026-01-01',
      endDate: '2026-12-31',
      objective: 'Lead Generation',
      status: 'Active',
    })
    setFormOpen(true)
  }

  const openEditModal = (cmp) => {
    setEditingCampaign(cmp)
    reset({
      name: cmp.name,
      description: cmp.description || '',
      channelId: cmp.channelId,
      creativeId: cmp.creativeId || '',
      audienceId: cmp.audienceId || '',
      budget: cmp.budget,
      currency: cmp.currency || 'USD',
      startDate: cmp.startDate,
      endDate: cmp.endDate,
      objective: cmp.objective || 'Lead Generation',
      status: cmp.status,
    })
    setFormOpen(true)
  }

  const onSubmitCampaign = async (values) => {
    if (editingCampaign) {
      await campaignService.updateCampaign(editingCampaign.id, values)
      showToast({
        type: 'success',
        title: 'Campaign Updated',
        message: `${values.name} has been updated.`,
      })
    } else {
      const created = await campaignService.createCampaign(values)
      showToast({
        type: 'success',
        title: 'Campaign Created',
        message: `Created ${created.id} (${created.name}).`,
      })
    }
    setFormOpen(false)
    await loadData()
  }

  const handleConfirmArchive = async () => {
    if (!archiveTarget) return
    await campaignService.archiveCampaign(archiveTarget.id)
    showToast({
      type: 'warning',
      title: 'Campaign Archived',
      message: `${archiveTarget.id} moved to Archived status.`,
    })
    setArchiveTarget(null)
    await loadData()
  }

  const filteredCampaigns = useMemo(() => {
    return campaigns.filter((c) => {
      const q = search.toLowerCase()
      const matchesSearch =
        !q ||
        c.id.toLowerCase().includes(q) ||
        c.name.toLowerCase().includes(q) ||
        c.channelName.toLowerCase().includes(q)
      const matchesStatus =
        statusFilter === 'all' || c.status === statusFilter
      const matchesChannel =
        channelFilter === 'all' || c.channelId === channelFilter
      const matchesDate = !dateFrom || c.startDate >= dateFrom
      return matchesSearch && matchesStatus && matchesChannel && matchesDate
    })
  }, [campaigns, search, statusFilter, channelFilter, dateFrom])

  const columns = [
    {
      key: 'id',
      label: 'Campaign ID',
      sortable: true,
      render: (row) => (
        <span className="font-mono text-xs font-semibold text-blue-700">
          {row.id}
        </span>
      ),
    },
    {
      key: 'name',
      label: 'Campaign Name',
      sortable: true,
      render: (row) => (
        <div>
          <p className="font-semibold text-slate-900">{row.name}</p>
          {(row.missingCostAlert || row.hasCurrencyMismatch) && (
            <span className="mt-0.5 inline-flex items-center gap-1 text-[11px] font-medium text-amber-700">
              <AlertTriangle className="h-3 w-3" />
              {row.missingCostAlert ? 'Missing cost ledger' : 'Currency mismatch'}
            </span>
          )}
        </div>
      ),
    },
    { key: 'channelName', label: 'Channel', sortable: true },
    {
      key: 'budget',
      label: 'Budget',
      sortable: true,
      align: 'right',
      render: (row) => formatCurrency(row.budget, row.currency),
    },
    {
      key: 'spend',
      label: 'Spend',
      sortable: true,
      align: 'right',
      render: (row) => formatCurrency(row.spend, row.currency),
    },
    {
      key: 'attributedRevenue',
      label: 'Attributed Rev.',
      sortable: true,
      align: 'right',
      render: (row) => (
        <span className="font-semibold text-slate-900">
          {formatCurrency(row.attributedRevenue, row.currency)}
        </span>
      ),
    },
    {
      key: 'leads',
      label: 'Leads',
      sortable: true,
      align: 'right',
      render: (row) => formatNumber(row.leads),
    },
    {
      key: 'roi',
      label: 'ROI',
      sortable: true,
      align: 'right',
      render: (row) =>
        row.roi === null ? (
          <span className="text-xs text-slate-400">Zero Spend</span>
        ) : (
          <span
            className={`font-semibold ${
              row.roi >= 0 ? 'text-emerald-700' : 'text-rose-600'
            }`}
          >
            {formatPercent(row.roi)}
          </span>
        ),
    },
    {
      key: 'startDate',
      label: 'Start Date',
      sortable: true,
      render: (row) => formatDate(row.startDate),
    },
    {
      key: 'endDate',
      label: 'End Date',
      sortable: true,
      render: (row) => formatDate(row.endDate),
    },
    {
      key: 'status',
      label: 'Status',
      sortable: true,
      render: (row) => <Badge status={row.status} dot>{row.status}</Badge>,
    },
    {
      key: 'actions',
      label: 'Actions',
      align: 'right',
      render: (row) => (
        <div
          className="inline-flex items-center gap-1"
          onClick={(e) => e.stopPropagation()}
        >
          <button
            type="button"
            title="View details"
            onClick={() => navigate(`/campaigns/${row.id}`)}
            className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100 hover:text-blue-600 cursor-pointer"
          >
            <Eye className="h-4 w-4" />
          </button>
          <button
            type="button"
            title="Edit campaign"
            onClick={() => openEditModal(row)}
            className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-900 cursor-pointer"
          >
            <Edit3 className="h-4 w-4" />
          </button>
          {row.status !== 'Archived' && (
            <button
              type="button"
              title="Archive campaign"
              onClick={() => setArchiveTarget(row)}
              className="rounded-md p-1.5 text-slate-500 hover:bg-rose-50 hover:text-rose-600 cursor-pointer"
            >
              <Archive className="h-4 w-4" />
            </button>
          )}
        </div>
      ),
    },
  ]

  if (error) {
    return <ErrorState message={error} onRetry={loadData} />
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Campaign Management"
        description="Manage marketing campaigns, budgets, linked creatives, audiences, and attributed ROI."
        badge={<Badge variant="primary">{campaigns.length} Campaigns</Badge>}
        actions={
          <>
            <Button
              variant="outline"
              icon={Download}
              onClick={() => {
                exportToCsv('campaigns.csv', filteredCampaigns)
                showToast({
                  type: 'success',
                  title: 'CSV Exported',
                  message: `Exported ${filteredCampaigns.length} campaigns.`,
                })
              }}
            >
              Export CSV
            </Button>
            <Button icon={Plus} onClick={openCreateModal}>
              Create Campaign
            </Button>
          </>
        }
      />

      <FilterBar
        searchValue={search}
        onSearchChange={setSearch}
        searchPlaceholder="Search ID, campaign name, or channel..."
        filters={[
          {
            id: 'status',
            label: 'Status',
            value: statusFilter,
            onChange: setStatusFilter,
            options: [
              { value: 'all', label: 'All Statuses' },
              { value: 'Active', label: 'Active' },
              { value: 'Completed', label: 'Completed' },
              { value: 'Paused', label: 'Paused' },
              { value: 'Draft', label: 'Draft' },
              { value: 'Archived', label: 'Archived' },
            ],
          },
          {
            id: 'channel',
            label: 'Channel',
            value: channelFilter,
            onChange: setChannelFilter,
            options: [
              { value: 'all', label: 'All Channels' },
              ...channels.map((ch) => ({ value: ch.id, label: ch.name })),
            ],
          },
        ]}
        actions={
          <div className="flex items-center gap-1.5">
            <label
              htmlFor="cmp-start-filter"
              className="text-xs font-medium text-slate-500 whitespace-nowrap"
            >
              Start From
            </label>
            <input
              id="cmp-start-filter"
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="h-9 rounded-lg border border-slate-200 bg-white px-2.5 text-xs text-slate-700 focus:border-blue-500 focus:outline-none"
            />
          </div>
        }
        onReset={() => {
          setSearch('')
          setStatusFilter('all')
          setChannelFilter('all')
          setDateFrom('')
        }}
      />

      <DataTable
        columns={columns}
        data={filteredCampaigns}
        loading={loading}
        pageSize={8}
        onRowClick={(row) => navigate(`/campaigns/${row.id}`)}
        onResetFilters={() => {
          setSearch('')
          setStatusFilter('all')
          setChannelFilter('all')
          setDateFrom('')
        }}
      />

      {/* Create / Edit Campaign Modal */}
      <Modal
        isOpen={formOpen}
        onClose={() => setFormOpen(false)}
        title={editingCampaign ? `Edit ${editingCampaign.id}` : 'Create New Campaign'}
        subtitle="Configure budget, channel, creative, audience, and flight schedule"
        size="lg"
        footer={
          <>
            <Button variant="outline" onClick={() => setFormOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" form="campaign-form">
              {editingCampaign ? 'Save Changes' : 'Create Campaign'}
            </Button>
          </>
        }
      >
        <form
          id="campaign-form"
          onSubmit={handleSubmit(onSubmitCampaign)}
          className="space-y-4"
        >
          <FormField
            label="Campaign Name"
            htmlFor="cmp-name"
            required
            error={errors.name?.message}
          >
            <TextInput
              id="cmp-name"
              placeholder="e.g., Q4 Enterprise Demand Capture"
              hasError={Boolean(errors.name)}
              {...register('name', { required: 'Campaign name is required.' })}
            />
          </FormField>

          <FormField label="Campaign Description" htmlFor="cmp-desc">
            <TextArea
              id="cmp-desc"
              placeholder="Describe campaign target objective and positioning..."
              {...register('description')}
            />
          </FormField>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <FormField
              label="Channel"
              htmlFor="cmp-channel"
              required
              error={errors.channelId?.message}
            >
              <SelectInput
                id="cmp-channel"
                options={channels.map((ch) => ({ value: ch.id, label: ch.name }))}
                {...register('channelId', { required: 'Channel is required.' })}
              />
            </FormField>

            <FormField label="Creative" htmlFor="cmp-creative">
              <SelectInput
                id="cmp-creative"
                options={creatives.map((crt) => ({ value: crt.id, label: crt.name }))}
                {...register('creativeId')}
              />
            </FormField>

            <FormField label="Audience" htmlFor="cmp-audience">
              <SelectInput
                id="cmp-audience"
                options={audiences.map((aud) => ({ value: aud.id, label: aud.name }))}
                {...register('audienceId')}
              />
            </FormField>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <FormField
              label="Budget"
              htmlFor="cmp-budget"
              required
              error={errors.budget?.message}
            >
              <TextInput
                id="cmp-budget"
                type="number"
                min="0"
                hasError={Boolean(errors.budget)}
                {...register('budget', {
                  required: 'Budget is required.',
                  min: { value: 0, message: 'Budget cannot be negative.' },
                })}
              />
            </FormField>

            <FormField label="Currency" htmlFor="cmp-currency">
              <SelectInput
                id="cmp-currency"
                options={[
                  { value: 'USD', label: 'USD ($)' },
                  { value: 'EUR', label: 'EUR (€)' },
                  { value: 'GBP', label: 'GBP (£)' },
                ]}
                {...register('currency')}
              />
            </FormField>

            <FormField label="Objective" htmlFor="cmp-objective">
              <SelectInput
                id="cmp-objective"
                options={[
                  { value: 'Lead Generation', label: 'Lead Generation' },
                  { value: 'Pipeline Acceleration', label: 'Pipeline Acceleration' },
                  { value: 'Conversion Lift', label: 'Conversion Lift' },
                  { value: 'Retargeting', label: 'Retargeting' },
                  { value: 'Brand & Pipeline', label: 'Brand & Pipeline' },
                  { value: 'Awareness', label: 'Awareness' },
                ]}
                {...register('objective')}
              />
            </FormField>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <FormField
              label="Start Date"
              htmlFor="cmp-start"
              required
              error={errors.startDate?.message}
            >
              <TextInput
                id="cmp-start"
                type="date"
                {...register('startDate', { required: 'Start date is required.' })}
              />
            </FormField>

            <FormField
              label="End Date"
              htmlFor="cmp-end"
              required
              error={errors.endDate?.message}
            >
              <TextInput
                id="cmp-end"
                type="date"
                {...register('endDate', { required: 'End date is required.' })}
              />
            </FormField>

            <FormField label="Campaign Status" htmlFor="cmp-status">
              <SelectInput
                id="cmp-status"
                options={[
                  { value: 'Active', label: 'Active' },
                  { value: 'Paused', label: 'Paused' },
                  { value: 'Completed', label: 'Completed' },
                  { value: 'Draft', label: 'Draft' },
                  { value: 'Archived', label: 'Archived' },
                ]}
                {...register('status')}
              />
            </FormField>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        isOpen={Boolean(archiveTarget)}
        onClose={() => setArchiveTarget(null)}
        onConfirm={handleConfirmArchive}
        title="Archive Campaign"
        message={`Archive "${archiveTarget?.name}" (${archiveTarget?.id})? Historical attribution and cost records remain preserved.`}
        confirmLabel="Archive Campaign"
      />
    </div>
  )
}
