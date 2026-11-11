import { useEffect, useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'
import { AlertTriangle, Coins, Edit3, Plus } from 'lucide-react'
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
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
import { contactService } from '../../services/contactService'
import { formatCurrency, formatDate } from '../../utils/formatters'

export function CostsPage() {
  const { showToast } = useToast()
  const [costs, setCosts] = useState([])
  const [campaigns, setCampaigns] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [campaignFilter, setCampaignFilter] = useState('all')
  const [currencyFilter, setCurrencyFilter] = useState('all')
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState(null)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm()

  const fetchCostResources = () =>
    Promise.all([
      contactService.listCosts(),
      campaignService.listCampaigns(),
    ])

  const loadData = async () => {
    setLoading(true)
    const [costData, cmpData] = await fetchCostResources()
    setCosts(costData)
    setCampaigns(cmpData)
    setLoading(false)
  }

  useEffect(() => {
    let active = true
    fetchCostResources().then(([costData, cmpData]) => {
      if (!active) return
      setCosts(costData)
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
        campaignId: campaigns[0]?.id || '',
        channel: 'Google Paid Search',
        category: 'Media Spend',
        amount: '',
        currency: 'USD',
        date: '2026-11-11',
        description: '',
      }
    )
    setFormOpen(true)
  }

  const onSubmit = async (values) => {
    const selectedCmp = campaigns.find((c) => c.id === values.campaignId)
    await contactService.saveCost(
      {
        ...values,
        channel: selectedCmp?.channelName || values.channel,
      },
      editing?.id || null
    )
    showToast({
      type: 'success',
      title: editing ? 'Cost Updated' : 'Cost Recorded',
      message: `Saved cost entry for ${values.campaignId}.`,
    })
    setFormOpen(false)
    await loadData()
  }

  const missingCostCampaigns = campaigns.filter((c) => c.missingCostAlert)
  const currencyMismatches = costs.filter((c) => c.currencyMismatch)

  const filtered = useMemo(() => {
    return costs.filter((c) => {
      const q = search.toLowerCase()
      const matchesSearch =
        !q ||
        c.id.toLowerCase().includes(q) ||
        c.campaignName.toLowerCase().includes(q) ||
        c.category.toLowerCase().includes(q) ||
        c.description.toLowerCase().includes(q)
      const matchesCmp =
        campaignFilter === 'all' || c.campaignId === campaignFilter
      const matchesCurr =
        currencyFilter === 'all' || c.currency === currencyFilter
      return matchesSearch && matchesCmp && matchesCurr
    })
  }, [costs, search, campaignFilter, currencyFilter])

  const campaignSummaries = useMemo(() => {
    return campaigns.map((cmp) => {
      const entries = costs.filter((c) => c.campaignId === cmp.id)
      const usdTotal = entries
        .filter((e) => e.currency === 'USD')
        .reduce((s, e) => s + Number(e.amount || 0), 0)
      return {
        id: cmp.id,
        name: cmp.name,
        budget: cmp.budget,
        usdTotal,
        entriesCount: entries.length,
        missingAlert: cmp.missingCostAlert,
      }
    })
  }, [campaigns, costs])

  const columns = [
    {
      key: 'id',
      label: 'Cost ID',
      sortable: true,
      render: (r) => <span className="font-mono text-xs font-semibold text-blue-700">{r.id}</span>,
    },
    {
      key: 'campaignId',
      label: 'Campaign',
      sortable: true,
      render: (r) => (
        <div>
          <p className="font-semibold text-slate-900">{r.campaignName}</p>
          <p className="font-mono text-[11px] text-slate-500">{r.campaignId}</p>
        </div>
      ),
    },
    { key: 'channel', label: 'Channel', sortable: true },
    { key: 'category', label: 'Cost Category', sortable: true },
    {
      key: 'amount',
      label: 'Amount',
      sortable: true,
      align: 'right',
      render: (r) => (
        <span className="font-bold text-slate-900">
          {formatCurrency(r.amount, r.currency)}
        </span>
      ),
    },
    {
      key: 'currency',
      label: 'Currency',
      sortable: true,
      render: (r) => (
        <Badge status={r.currencyMismatch ? 'Warning' : 'Valid'}>
          {r.currencyMismatch ? `${r.currency} (Mismatch)` : r.currency}
        </Badge>
      ),
    },
    {
      key: 'date',
      label: 'Date',
      sortable: true,
      render: (r) => formatDate(r.date),
    },
    {
      key: 'description',
      label: 'Description',
      render: (r) => (
        <span className="text-xs text-slate-600 line-clamp-1">{r.description}</span>
      ),
    },
    {
      key: 'actions',
      label: 'Actions',
      align: 'right',
      render: (r) => (
        <button
          type="button"
          title="Edit cost record"
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
        title="Marketing Cost Management"
        description="Track media spend, agency fees, currency integrity, and missing-cost alerts per campaign."
        badge={<Badge variant="primary">{costs.length} Ledger Entries</Badge>}
        actions={
          <Button icon={Plus} onClick={() => openModal()}>
            Add Cost Record
          </Button>
        }
      />

      {(missingCostCampaigns.length > 0 || currencyMismatches.length > 0) && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {missingCostCampaigns.length > 0 && (
            <div className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-900">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
              <div>
                <p className="font-semibold">
                  Missing-Cost Alert ({missingCostCampaigns.length} Campaign)
                </p>
                <p className="mt-0.5 text-amber-800">
                  {missingCostCampaigns.map((c) => `${c.id} (${c.name})`).join(', ')}{' '}
                  recorded active budget and touchpoints with $0 logged in cost ledger.
                </p>
              </div>
            </div>
          )}

          {currencyMismatches.length > 0 && (
            <div className="flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-xs text-rose-900">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-rose-600" />
              <div>
                <p className="font-semibold">
                  Currency Mismatch Detected ({currencyMismatches.length} Entry)
                </p>
                <p className="mt-0.5 text-rose-800">
                  {currencyMismatches
                    .map((c) => `${c.id} (${c.currency} vs ${c.campaignCurrency})`)
                    .join(', ')}{' '}
                  requires FX normalization before ROI aggregation.
                </p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Campaign Cost Summary Cards */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Coins className="h-4 w-4 text-blue-600" />
            <div>
              <CardTitle>Campaign Cost Summaries</CardTitle>
              <CardDescription>Verified USD spend vs approved budget</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {campaignSummaries.map((cs) => (
            <div
              key={cs.id}
              className={`rounded-lg border p-3 text-xs ${
                cs.missingAlert
                  ? 'border-amber-200 bg-amber-50/50'
                  : 'border-slate-200 bg-slate-50/70'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-mono text-[11px] font-semibold text-blue-700">
                  {cs.id}
                </span>
                <span className="text-[11px] text-slate-500">
                  {cs.entriesCount} entry(ies)
                </span>
              </div>
              <p className="mt-1 truncate font-semibold text-slate-900">{cs.name}</p>
              <div className="mt-2 flex items-center justify-between">
                <span className="font-bold text-slate-900 tabular-nums">
                  {formatCurrency(cs.usdTotal)}
                </span>
                <span className="text-slate-500 tabular-nums">
                  / {formatCurrency(cs.budget)}
                </span>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      <FilterBar
        searchValue={search}
        onSearchChange={setSearch}
        searchPlaceholder="Search cost ID, campaign, category, or notes..."
        filters={[
          {
            id: 'cost-cmp',
            label: 'Campaign',
            value: campaignFilter,
            onChange: setCampaignFilter,
            options: [
              { value: 'all', label: 'All Campaigns' },
              ...campaigns.map((c) => ({ value: c.id, label: c.name })),
            ],
          },
          {
            id: 'cost-curr',
            label: 'Currency',
            value: currencyFilter,
            onChange: setCurrencyFilter,
            options: [
              { value: 'all', label: 'All Currencies' },
              { value: 'USD', label: 'USD' },
              { value: 'EUR', label: 'EUR' },
              { value: 'GBP', label: 'GBP' },
            ],
          },
        ]}
        onReset={() => {
          setSearch('')
          setCampaignFilter('all')
          setCurrencyFilter('all')
        }}
      />

      <DataTable
        columns={columns}
        data={filtered}
        loading={loading}
        pageSize={10}
        rowClassName={(row) =>
          row.currencyMismatch ? 'bg-amber-50/60 hover:bg-amber-50' : ''
        }
      />

      <Modal
        isOpen={formOpen}
        onClose={() => setFormOpen(false)}
        title={editing ? `Edit ${editing.id}` : 'Add Marketing Cost Record'}
        footer={
          <>
            <Button variant="outline" onClick={() => setFormOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" form="cost-form">
              Save Cost Entry
            </Button>
          </>
        }
      >
        <form id="cost-form" onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <FormField label="Campaign" htmlFor="cost-cmp-in">
              <SelectInput
                id="cost-cmp-in"
                options={campaigns.map((c) => ({ value: c.id, label: `${c.id} · ${c.name}` }))}
                {...register('campaignId')}
              />
            </FormField>
            <FormField label="Cost Category" htmlFor="cost-cat">
              <SelectInput
                id="cost-cat"
                options={[
                  { value: 'Media Spend', label: 'Media Spend' },
                  { value: 'Agency & Bid Management', label: 'Agency & Bid Management' },
                  { value: 'Creative Production', label: 'Creative Production' },
                  { value: 'Platform & Automation', label: 'Platform & Automation' },
                  { value: 'Sponsorship & Venue', label: 'Sponsorship & Venue' },
                ]}
                {...register('category')}
              />
            </FormField>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <FormField
              label="Amount"
              htmlFor="cost-amount"
              required
              error={errors.amount?.message}
            >
              <TextInput
                id="cost-amount"
                type="number"
                min="0"
                hasError={Boolean(errors.amount)}
                {...register('amount', { required: 'Amount is required.' })}
              />
            </FormField>
            <FormField label="Currency" htmlFor="cost-curr-in">
              <SelectInput
                id="cost-curr-in"
                options={[
                  { value: 'USD', label: 'USD' },
                  { value: 'EUR', label: 'EUR' },
                  { value: 'GBP', label: 'GBP' },
                ]}
                {...register('currency')}
              />
            </FormField>
            <FormField label="Date" htmlFor="cost-date">
              <TextInput id="cost-date" type="date" {...register('date')} />
            </FormField>
          </div>

          <FormField label="Description" htmlFor="cost-desc">
            <TextArea id="cost-desc" {...register('description')} />
          </FormField>
        </form>
      </Modal>
    </div>
  )
}
