import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  AlertCircle,
  ArrowRight,
  Briefcase,
  CheckCircle2,
  CreditCard,
  Globe,
  Megaphone,
  Search,
  Sparkles,
} from 'lucide-react'
import {
  Badge,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  EmptyState,
  KpiCard,
  LoadingState,
  PageHeader,
} from '../../components/common'
import { contactService } from '../../services/contactService'
import { formatCurrency, formatDateTime, formatPercent } from '../../utils/formatters'

const LIFECYCLE_STAGES = [
  'Advertisement',
  'Website Visit',
  'Email Interaction',
  'Lead Created',
  'Opportunity Created',
  'Closed Order',
]

const MODELS = [
  { value: 'position_based', label: 'Position Based (40/20/40)' },
  { value: 'first_touch', label: 'First Touch' },
  { value: 'last_touch', label: 'Last Touch' },
  { value: 'linear', label: 'Linear' },
  { value: 'time_decay', label: 'Time Decay' },
]

export function CustomerJourneyPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const initialContactId = searchParams.get('contactId') || 'CON-2026-000001'

  const [contacts, setContacts] = useState([])
  const [selectedContactId, setSelectedContactId] = useState(initialContactId)
  const [contactSearchInput, setContactSearchInput] = useState(initialContactId)
  const [modelId, setModelId] = useState('position_based')
  const [journey, setJourney] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    contactService.listContacts().then(setContacts)
  }, [])

  useEffect(() => {
    let active = true
    contactService.getContactJourney(selectedContactId, modelId).then((data) => {
      if (!active) return
      setJourney(data)
      setLoading(false)
    })
    return () => {
      active = false
    }
  }, [selectedContactId, modelId])

  const handleSelectContact = (contactId) => {
    setSelectedContactId(contactId)
    setContactSearchInput(contactId)
    setSearchParams({ contactId })
  }

  const handleSearchSubmit = (e) => {
    e.preventDefault()
    const trimmed = contactSearchInput.trim().toUpperCase()
    if (!trimmed) return
    handleSelectContact(trimmed)
  }

  const validRevenue = (journey?.orders || [])
    .filter((o) => o.verificationStatus === 'Valid')
    .reduce((s, o) => s + o.revenue, 0)

  const uniqueCampaigns = new Set(
    (journey?.touchpoints || []).map((t) => t.campaignName)
  )

  return (
    <div className="space-y-6">
      <PageHeader
        title="Customer Journey Explorer"
        description="Chronological lifecycle trace across campaigns, web sessions, leads, opportunities, closed orders, and attribution credits."
        badge={<Badge variant="primary" dot>Full Lifecycle</Badge>}
      />

      {/* Search & Selector Toolbar */}
      <Card>
        <CardContent className="flex flex-col gap-3 p-4 lg:flex-row lg:items-center lg:justify-between">
          <form
            onSubmit={handleSearchSubmit}
            className="flex flex-1 flex-wrap items-center gap-2.5"
          >
            <div className="relative min-w-[220px] flex-1 sm:max-w-xs">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                value={contactSearchInput}
                onChange={(e) => setContactSearchInput(e.target.value)}
                placeholder="Enter Contact ID (e.g. CON-2026-000001)"
                className="h-9 w-full rounded-lg border border-slate-200 bg-slate-50 pl-9 pr-3 text-xs font-mono text-slate-900 focus:border-blue-500 focus:bg-white focus:outline-none"
              />
            </div>

            <select
              aria-label="Select contact"
              value={selectedContactId}
              onChange={(e) => handleSelectContact(e.target.value)}
              className="h-9 rounded-lg border border-slate-200 bg-white px-3 text-xs font-medium text-slate-700 cursor-pointer"
            >
              {contacts.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.id} · {c.name} ({c.lifecycleStatus})
                </option>
              ))}
            </select>

            <button
              type="submit"
              className="h-9 rounded-lg bg-blue-600 px-4 text-xs font-semibold text-white hover:bg-blue-700 cursor-pointer"
            >
              Inspect Journey
            </button>
          </form>

          <div className="flex items-center gap-2">
            <label
              htmlFor="journey-model"
              className="text-xs font-medium text-slate-500 whitespace-nowrap"
            >
              Attribution Model
            </label>
            <select
              id="journey-model"
              value={modelId}
              onChange={(e) => setModelId(e.target.value)}
              className="h-9 rounded-lg border border-slate-200 bg-white px-3 text-xs font-medium text-slate-700 cursor-pointer"
            >
              {MODELS.map((m) => (
                <option key={m.value} value={m.value}>
                  {m.label}
                </option>
              ))}
            </select>
          </div>
        </CardContent>
      </Card>

      {/* Visual Lifecycle Flow Strip */}
      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
        <div className="flex min-w-[680px] items-center justify-between gap-2">
          {LIFECYCLE_STAGES.map((stage, idx) => (
            <div key={stage} className="flex items-center gap-2">
              <div className="flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-800">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-blue-600 text-[10px] font-bold text-white">
                  {idx + 1}
                </span>
                <span>{stage}</span>
              </div>
              {idx < LIFECYCLE_STAGES.length - 1 && (
                <ArrowRight className="h-4 w-4 text-slate-400 shrink-0" />
              )}
            </div>
          ))}
        </div>
      </div>

      {loading ? (
        <LoadingState message="Building customer journey timeline..." />
      ) : !journey?.contact ? (
        <EmptyState
          title="Contact ID not found"
          description={`No contact matched "${selectedContactId}". Try CON-2026-000001 through CON-2026-000012.`}
          actionLabel="Load CON-2026-000001"
          onAction={() => handleSelectContact('CON-2026-000001')}
        />
      ) : (
        <>
          {/* Contact & Outcome KPIs */}
          <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <KpiCard
              title="Contact"
              value={journey.contact.name}
              changeLabel={`${journey.contact.company} · ${journey.contact.lifecycleStatus}`}
              icon={Sparkles}
              accent="blue"
            />
            <KpiCard
              title="Campaigns Touched"
              value={String(uniqueCampaigns.size)}
              changeLabel={`${journey.touchpoints.length} total touchpoints`}
              icon={Megaphone}
              accent="violet"
            />
            <KpiCard
              title="Web Sessions"
              value={String(journey.sessions.length)}
              changeLabel={`${journey.opportunities.length} opportunity(ies)`}
              icon={Globe}
              accent="amber"
            />
            <KpiCard
              title="Verified Closed Revenue"
              value={formatCurrency(validRevenue)}
              changeLabel={`${journey.orders.length} order record(s)`}
              icon={CreditCard}
              accent="emerald"
            />
          </section>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            {/* Chronological Timeline */}
            <Card className="lg:col-span-2">
              <CardHeader>
                <div>
                  <CardTitle>Chronological Journey Timeline</CardTitle>
                  <CardDescription>
                    Multi-campaign touchpoints, sessions, leads, opportunities, and orders for {journey.contact.id}
                  </CardDescription>
                </div>
                <Badge status={journey.contact.lifecycleStatus}>
                  {journey.contact.lifecycleStatus}
                </Badge>
              </CardHeader>
              <CardContent>
                {journey.timeline.length === 0 ? (
                  <p className="py-8 text-center text-xs text-slate-500">
                    No recorded events for this contact.
                  </p>
                ) : (
                  <ol className="relative ml-3 border-l border-slate-200 space-y-6">
                    {journey.timeline.map((event) => (
                      <li key={event.id} className="ml-6">
                        <span
                          className={`absolute -left-2.5 flex h-5 w-5 items-center justify-center rounded-full ring-4 ring-white ${
                            event.isInvalid
                              ? 'bg-rose-600 text-white'
                              : 'bg-blue-600 text-white'
                          }`}
                        >
                          {event.isInvalid ? (
                            <AlertCircle className="h-3 w-3" />
                          ) : (
                            <CheckCircle2 className="h-3 w-3" />
                          )}
                        </span>

                        <div
                          className={`rounded-xl border p-3.5 ${
                            event.isInvalid
                              ? 'border-rose-200 bg-rose-50/60'
                              : 'border-slate-200 bg-slate-50/50'
                          }`}
                        >
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <span className="text-[11px] font-semibold uppercase tracking-wider text-blue-700">
                              {event.stageType}
                            </span>
                            <div className="flex items-center gap-2">
                              <span className="text-[11px] text-slate-500">
                                {formatDateTime(event.timestamp)}
                              </span>
                              <Badge status={event.isInvalid ? 'Critical' : event.badge}>
                                {event.badge}
                              </Badge>
                            </div>
                          </div>
                          <p className="mt-1 text-sm font-semibold text-slate-900">
                            {event.title}
                          </p>
                          <p className="mt-0.5 text-xs text-slate-600">
                            {event.subtitle}
                          </p>
                        </div>
                      </li>
                    ))}
                  </ol>
                )}
              </CardContent>
            </Card>

            {/* Right Column: Attribution Credits + CRM Context */}
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <div>
                    <CardTitle>Attribution Credits</CardTitle>
                    <CardDescription>
                      Calculated under {MODELS.find((m) => m.value === modelId)?.label}
                    </CardDescription>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  {journey.attributionCredits.length === 0 ? (
                    <p className="text-xs text-slate-500">
                      No valid closed order yet for this contact, so revenue attribution credits have not been finalized.
                    </p>
                  ) : (
                    journey.attributionCredits.map((cr) => (
                      <div
                        key={cr.touchpointId}
                        className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-slate-900">
                            {cr.campaignName}
                          </span>
                          <span className="font-bold text-emerald-700 tabular-nums">
                            {formatCurrency(cr.creditAmount)}
                          </span>
                        </div>
                        <div className="mt-1 flex items-center justify-between text-[11px] text-slate-500">
                          <span>{cr.channelName}</span>
                          <span className="font-semibold text-blue-700">
                            {formatPercent(cr.weightPercent)} weight
                          </span>
                        </div>
                      </div>
                    ))
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <div className="flex items-center gap-2">
                    <Briefcase className="h-4 w-4 text-slate-500" />
                    <CardTitle>CRM Lead &amp; Deal Summary</CardTitle>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3 text-xs">
                  {journey.leads.map((l) => (
                    <div key={l.id} className="flex justify-between border-b border-slate-100 pb-2">
                      <span className="text-slate-600">
                        {l.id} (Score {l.score})
                      </span>
                      <Badge status={l.status}>{l.status}</Badge>
                    </div>
                  ))}
                  {journey.opportunities.map((o) => (
                    <div key={o.id} className="space-y-1 border-b border-slate-100 pb-2">
                      <div className="flex justify-between">
                        <span className="font-semibold text-slate-900">{o.id}</span>
                        <Badge status={o.stage}>{o.stage}</Badge>
                      </div>
                      <p className="text-slate-500">{o.name}</p>
                    </div>
                  ))}
                  {journey.orders.map((ord) => (
                    <div key={ord.id} className="flex justify-between">
                      <span className="font-semibold text-slate-900">
                        {ord.id} ({formatCurrency(ord.revenue)})
                      </span>
                      <Badge status={ord.verificationStatus}>
                        {ord.verificationStatus}
                      </Badge>
                    </div>
                  ))}
                </CardContent>
              </Card>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
