import { useEffect, useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'
import { AlertTriangle, CheckCircle2, DollarSign, Plus } from 'lucide-react'
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
import { contactService } from '../../services/contactService'
import { formatCurrency, formatDate, formatNumber } from '../../utils/formatters'

export function OrdersPage() {
  const { showToast } = useToast()
  const [orders, setOrders] = useState([])
  const [opps, setOpps] = useState([])
  const [contacts, setContacts] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [verificationFilter, setVerificationFilter] = useState('all')
  const [formOpen, setFormOpen] = useState(false)

  const { register, handleSubmit, reset } = useForm()

  const fetchOrderResources = () =>
    Promise.all([
      contactService.listOrders(),
      contactService.listOpportunities(),
      contactService.listContacts(),
    ])

  const loadData = async () => {
    setLoading(true)
    const [ordData, oppData, conData] = await fetchOrderResources()
    setOrders(ordData)
    setOpps(oppData)
    setContacts(conData)
    setLoading(false)
  }

  useEffect(() => {
    let active = true
    fetchOrderResources().then(([ordData, oppData, conData]) => {
      if (!active) return
      setOrders(ordData)
      setOpps(oppData)
      setContacts(conData)
      setLoading(false)
    })
    return () => {
      active = false
    }
  }, [])

  const openCreate = () => {
    reset({
      opportunityId: opps[0]?.id || '',
      contactId: contacts[0]?.id || '',
      orderDate: '2026-11-11',
      revenue: 50000,
      currency: 'USD',
      paymentStatus: 'Paid',
      verificationStatus: 'Valid',
    })
    setFormOpen(true)
  }

  const onSubmit = async (values) => {
    await contactService.saveOrder(values)
    showToast({
      type: 'success',
      title: 'Order Recorded',
      message: 'New closed order added and queued for verification.',
    })
    setFormOpen(false)
    await loadData()
  }

  const filtered = useMemo(() => {
    return orders.filter((o) => {
      const q = search.toLowerCase()
      const matchesSearch =
        !q ||
        o.id.toLowerCase().includes(q) ||
        o.opportunityId.toLowerCase().includes(q) ||
        o.contactName.toLowerCase().includes(q)
      const matchesVer =
        verificationFilter === 'all' || o.verificationStatus === verificationFilter
      return matchesSearch && matchesVer
    })
  }, [orders, search, verificationFilter])

  const validOrders = orders.filter((o) => o.verificationStatus === 'Valid')
  const duplicateOrders = orders.filter((o) => o.verificationStatus === 'Duplicate')
  const verifiedTotal = validOrders.reduce((s, o) => s + Number(o.revenue || 0), 0)
  const excludedDuplicateTotal = duplicateOrders.reduce(
    (s, o) => s + Number(o.revenue || 0),
    0
  )

  const columns = [
    {
      key: 'id',
      label: 'Order ID',
      sortable: true,
      render: (r) => <span className="font-mono text-xs font-semibold text-blue-700">{r.id}</span>,
    },
    {
      key: 'opportunityId',
      label: 'Opportunity',
      sortable: true,
      render: (r) => (
        <div>
          <p className="font-mono text-xs font-medium text-slate-800">{r.opportunityId}</p>
          <p className="text-[11px] text-slate-500 line-clamp-1">{r.opportunityName}</p>
        </div>
      ),
    },
    {
      key: 'contactName',
      label: 'Contact',
      sortable: true,
      render: (r) => (
        <div>
          <p className="text-xs font-semibold text-slate-900">{r.contactName}</p>
          <p className="font-mono text-[11px] text-slate-500">{r.contactId}</p>
        </div>
      ),
    },
    {
      key: 'orderDate',
      label: 'Order Date',
      sortable: true,
      render: (r) => formatDate(r.orderDate),
    },
    {
      key: 'revenue',
      label: 'Revenue',
      sortable: true,
      align: 'right',
      render: (r) => (
        <span
          className={`font-bold ${
            r.verificationStatus === 'Duplicate'
              ? 'line-through text-rose-600'
              : 'text-slate-900'
          }`}
        >
          {formatCurrency(r.revenue, r.currency)}
        </span>
      ),
    },
    { key: 'currency', label: 'Currency', sortable: true },
    {
      key: 'paymentStatus',
      label: 'Payment Status',
      sortable: true,
      render: (r) => <Badge status={r.paymentStatus} dot>{r.paymentStatus}</Badge>,
    },
    {
      key: 'verificationStatus',
      label: 'Revenue Verification',
      sortable: true,
      render: (r) => (
        <Badge status={r.verificationStatus} dot>
          {r.verificationStatus === 'Duplicate'
            ? 'Duplicate Warning'
            : r.verificationStatus}
        </Badge>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title="Order Management"
        description="Verify closed revenue transactions and isolate duplicate order entries before attribution."
        badge={<Badge variant="primary">{orders.length} Orders</Badge>}
        actions={
          <Button icon={Plus} onClick={openCreate}>
            Add Order
          </Button>
        }
      />

      {duplicateOrders.length > 0 && (
        <div className="flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-xs text-rose-800">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-rose-600" />
          <div>
            <p className="font-semibold">
              Duplicate Revenue Protection Active ({duplicateOrders.length} flagged)
            </p>
            <p className="mt-0.5 text-rose-700">
              {formatCurrency(excludedDuplicateTotal)} from duplicate order{' '}
              <strong>{duplicateOrders.map((d) => d.id).join(', ')}</strong> is excluded
              from verified closed revenue ({formatCurrency(verifiedTotal)}) and multi-touch attribution.
            </p>
          </div>
        </div>
      )}

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <KpiCard
          title="Verified Closed Revenue"
          value={formatCurrency(verifiedTotal)}
          changeLabel={`${validOrders.length} valid paid orders`}
          icon={DollarSign}
          accent="emerald"
        />
        <KpiCard
          title="Valid Orders"
          value={formatNumber(validOrders.length)}
          changeLabel="Eligible for ROI & attribution"
          icon={CheckCircle2}
          accent="blue"
        />
        <KpiCard
          title="Duplicate Orders Excluded"
          value={formatNumber(duplicateOrders.length)}
          changeLabel={`${formatCurrency(excludedDuplicateTotal)} quarantined`}
          icon={AlertTriangle}
          accent="rose"
        />
      </section>

      <FilterBar
        searchValue={search}
        onSearchChange={setSearch}
        searchPlaceholder="Search order ID, opportunity, or contact..."
        filters={[
          {
            id: 'ord-ver',
            label: 'Verification',
            value: verificationFilter,
            onChange: setVerificationFilter,
            options: [
              { value: 'all', label: 'All Verification States' },
              { value: 'Valid', label: 'Valid' },
              { value: 'Duplicate', label: 'Duplicate' },
            ],
          },
        ]}
        onReset={() => {
          setSearch('')
          setVerificationFilter('all')
        }}
      />

      <DataTable
        columns={columns}
        data={filtered}
        loading={loading}
        pageSize={10}
        rowClassName={(row) =>
          row.verificationStatus === 'Duplicate'
            ? 'bg-rose-50/70 hover:bg-rose-50'
            : ''
        }
      />

      <Modal
        isOpen={formOpen}
        onClose={() => setFormOpen(false)}
        title="Record Closed Order"
        footer={
          <>
            <Button variant="outline" onClick={() => setFormOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" form="order-form">
              Save Order
            </Button>
          </>
        }
      >
        <form id="order-form" onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <FormField label="Opportunity" htmlFor="ord-opp">
              <SelectInput
                id="ord-opp"
                options={opps.map((o) => ({ value: o.id, label: `${o.id} · ${o.name}` }))}
                {...register('opportunityId')}
              />
            </FormField>
            <FormField label="Contact" htmlFor="ord-con">
              <SelectInput
                id="ord-con"
                options={contacts.map((c) => ({ value: c.id, label: `${c.id} · ${c.name}` }))}
                {...register('contactId')}
              />
            </FormField>
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <FormField label="Order Date" htmlFor="ord-date">
              <TextInput id="ord-date" type="date" {...register('orderDate')} />
            </FormField>
            <FormField label="Revenue" htmlFor="ord-rev">
              <TextInput id="ord-rev" type="number" min="0" {...register('revenue')} />
            </FormField>
            <FormField label="Verification" htmlFor="ord-ver-in">
              <SelectInput
                id="ord-ver-in"
                options={[
                  { value: 'Valid', label: 'Valid' },
                  { value: 'Duplicate', label: 'Duplicate' },
                ]}
                {...register('verificationStatus')}
              />
            </FormField>
          </div>
        </form>
      </Modal>
    </div>
  )
}
