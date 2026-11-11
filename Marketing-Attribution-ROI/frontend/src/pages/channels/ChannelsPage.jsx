import { useEffect, useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'
import { Edit3, Plus, Trash2 } from 'lucide-react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  Badge,
  Button,
  FilterBar,
  PageHeader,
} from '../../components/common'
import { ChartCard } from '../../components/charts/ChartCard'
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
import { CHART_COLORS, CHART_TOOLTIP_STYLE } from '../../utils/chartTheme'
import {
  formatCurrency,
  formatNumber,
  formatPercent,
} from '../../utils/formatters'

export function ChannelsPage() {
  const { dateRange } = useApp()
  const { showToast } = useToast()

  const [channels, setChannels] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState('all')
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [deleteTarget, setDeleteTarget] = useState(null)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm()

  const loadChannels = async () => {
    setLoading(true)
    const data = await campaignService.listChannels(dateRange)
    setChannels(data)
    setLoading(false)
  }

  useEffect(() => {
    let active = true
    campaignService.listChannels(dateRange).then((data) => {
      if (!active) return
      setChannels(data)
      setLoading(false)
    })
    return () => {
      active = false
    }
  }, [dateRange])

  const openModal = (channel = null) => {
    setEditing(channel)
    reset(
      channel || {
        name: '',
        type: 'Paid Search',
        status: 'Active',
        owner: '',
        description: '',
      }
    )
    setFormOpen(true)
  }

  const onSubmit = async (values) => {
    await campaignService.saveChannel(values, editing?.id || null)
    showToast({
      type: 'success',
      title: editing ? 'Channel Updated' : 'Channel Added',
      message: `${values.name} saved cleanly.`,
    })
    setFormOpen(false)
    await loadChannels()
  }

  const handleDelete = async () => {
    if (!deleteTarget) return
    await campaignService.deleteChannel(deleteTarget.id)
    showToast({
      type: 'warning',
      title: 'Channel Removed',
      message: `${deleteTarget.name} (${deleteTarget.id}) deleted.`,
    })
    setDeleteTarget(null)
    await loadChannels()
  }

  const filtered = useMemo(() => {
    return channels.filter((c) => {
      const q = search.toLowerCase()
      const matchesSearch =
        !q ||
        c.name.toLowerCase().includes(q) ||
        c.id.toLowerCase().includes(q)
      const matchesType = typeFilter === 'all' || c.type === typeFilter
      return matchesSearch && matchesType
    })
  }, [channels, search, typeFilter])

  const columns = [
    {
      key: 'id',
      label: 'Channel ID',
      sortable: true,
      render: (r) => <span className="font-mono text-xs font-semibold text-blue-700">{r.id}</span>,
    },
    {
      key: 'name',
      label: 'Channel Name',
      sortable: true,
      render: (r) => <span className="font-semibold text-slate-900">{r.name}</span>,
    },
    { key: 'type', label: 'Channel Type', sortable: true },
    {
      key: 'totalCampaigns',
      label: 'Total Campaigns',
      sortable: true,
      align: 'right',
      render: (r) => formatNumber(r.totalCampaigns),
    },
    {
      key: 'totalSpend',
      label: 'Total Spend',
      sortable: true,
      align: 'right',
      render: (r) => formatCurrency(r.totalSpend),
    },
    {
      key: 'totalLeads',
      label: 'Total Leads',
      sortable: true,
      align: 'right',
      render: (r) => formatNumber(r.totalLeads),
    },
    {
      key: 'revenue',
      label: 'Revenue',
      sortable: true,
      align: 'right',
      render: (r) => <span className="font-semibold">{formatCurrency(r.revenue)}</span>,
    },
    {
      key: 'roi',
      label: 'ROI',
      sortable: true,
      align: 'right',
      render: (r) =>
        r.roi === null ? (
          <span className="text-xs text-slate-400">Zero Spend</span>
        ) : (
          <span className="font-semibold text-emerald-700">{formatPercent(r.roi)}</span>
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
            title="Edit channel"
            onClick={() => openModal(r)}
            className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-900 cursor-pointer"
          >
            <Edit3 className="h-4 w-4" />
          </button>
          <button
            type="button"
            title="Delete channel"
            onClick={() => setDeleteTarget(r)}
            className="rounded-md p-1.5 text-slate-500 hover:bg-rose-50 hover:text-rose-600 cursor-pointer"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title="Channel Management"
        description="Analyze multi-channel attribution revenue, spend efficiency, lead generation, and ROI."
        badge={<Badge variant="primary">{channels.length} Channels</Badge>}
        actions={
          <Button icon={Plus} onClick={() => openModal()}>
            Add Channel
          </Button>
        }
      />

      <ChartCard
        title="Channel Spend vs Attributed Revenue"
        subtitle="Direct comparison across active acquisition channels"
        loading={loading}
      >
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={filtered}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={CHART_COLORS.grid} />
            <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#475569' }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 11, fill: '#475569' }} axisLine={false} tickLine={false} tickFormatter={(v) => `$${v / 1000}k`} />
            <Tooltip contentStyle={CHART_TOOLTIP_STYLE} formatter={(val) => formatCurrency(val)} />
            <Legend wrapperStyle={{ fontSize: '12px' }} />
            <Bar dataKey="revenue" name="Attributed Revenue" fill={CHART_COLORS.primary} radius={[6, 6, 0, 0]} />
            <Bar dataKey="totalSpend" name="Total Spend" fill={CHART_COLORS.amber} radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      <FilterBar
        searchValue={search}
        onSearchChange={setSearch}
        searchPlaceholder="Search channel ID or name..."
        filters={[
          {
            id: 'channel-type',
            label: 'Type',
            value: typeFilter,
            onChange: setTypeFilter,
            options: [
              { value: 'all', label: 'All Types' },
              { value: 'Paid Search', label: 'Paid Search' },
              { value: 'Paid Social', label: 'Paid Social' },
              { value: 'Email', label: 'Email' },
              { value: 'Display', label: 'Display' },
              { value: 'Events', label: 'Events' },
              { value: 'Organic', label: 'Organic' },
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
        isOpen={formOpen}
        onClose={() => setFormOpen(false)}
        title={editing ? `Edit ${editing.id}` : 'Add Marketing Channel'}
        footer={
          <>
            <Button variant="outline" onClick={() => setFormOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" form="channel-form">
              Save Channel
            </Button>
          </>
        }
      >
        <form id="channel-form" onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <FormField label="Channel Name" htmlFor="chn-name" required error={errors.name?.message}>
            <TextInput
              id="chn-name"
              placeholder="e.g., Partner Co-Marketing"
              hasError={Boolean(errors.name)}
              {...register('name', { required: 'Channel name is required.' })}
            />
          </FormField>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <FormField label="Channel Type" htmlFor="chn-type">
              <SelectInput
                id="chn-type"
                options={[
                  { value: 'Paid Search', label: 'Paid Search' },
                  { value: 'Paid Social', label: 'Paid Social' },
                  { value: 'Email', label: 'Email' },
                  { value: 'Display', label: 'Display' },
                  { value: 'Events', label: 'Events' },
                  { value: 'Organic', label: 'Organic' },
                ]}
                {...register('type')}
              />
            </FormField>

            <FormField label="Channel Owner" htmlFor="chn-owner">
              <TextInput id="chn-owner" placeholder="Owner name" {...register('owner')} />
            </FormField>
          </div>

          <FormField label="Description" htmlFor="chn-desc">
            <TextArea id="chn-desc" placeholder="Describe channel role..." {...register('description')} />
          </FormField>
        </form>
      </Modal>

      <ConfirmDialog
        isOpen={Boolean(deleteTarget)}
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
        title="Delete Channel"
        message={`Remove "${deleteTarget?.name}" from active channel definitions?`}
        confirmLabel="Delete Channel"
      />
    </div>
  )
}
