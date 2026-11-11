import { useEffect, useMemo, useState } from 'react'
import { AlertCircle, Globe, WifiOff } from 'lucide-react'
import {
  Badge,
  FilterBar,
  PageHeader,
} from '../../components/common'
import { DataTable } from '../../components/tables/DataTable'
import { campaignService } from '../../services/campaignService'
import { contactService } from '../../services/contactService'
import { formatDateTime } from '../../utils/formatters'

export function TouchpointsPage() {
  const [touchpoints, setTouchpoints] = useState([])
  const [campaigns, setCampaigns] = useState([])
  const [channels, setChannels] = useState([])
  const [contacts, setContacts] = useState([])
  const [loading, setLoading] = useState(true)

  const [search, setSearch] = useState('')
  const [contactFilter, setContactFilter] = useState('all')
  const [campaignFilter, setCampaignFilter] = useState('all')
  const [channelFilter, setChannelFilter] = useState('all')
  const [dateFrom, setDateFrom] = useState('')

  useEffect(() => {
    Promise.all([
      contactService.listTouchpoints(),
      campaignService.listCampaigns(),
      campaignService.listChannels(),
      contactService.listContacts(),
    ]).then(([tps, cmps, chs, cons]) => {
      setTouchpoints(tps)
      setCampaigns(cmps)
      setChannels(chs)
      setContacts(cons)
      setLoading(false)
    })
  }, [])

  const filtered = useMemo(() => {
    return touchpoints.filter((tp) => {
      const q = search.toLowerCase()
      const matchesSearch =
        !q ||
        tp.id.toLowerCase().includes(q) ||
        tp.contactName.toLowerCase().includes(q) ||
        tp.interactionType.toLowerCase().includes(q)
      const matchesContact = contactFilter === 'all' || tp.contactId === contactFilter
      const matchesCampaign = campaignFilter === 'all' || tp.campaignId === campaignFilter
      const matchesChannel = channelFilter === 'all' || tp.channelId === channelFilter
      const matchesDate = !dateFrom || tp.timestamp.slice(0, 10) >= dateFrom
      return (
        matchesSearch &&
        matchesContact &&
        matchesCampaign &&
        matchesChannel &&
        matchesDate
      )
    })
  }, [touchpoints, search, contactFilter, campaignFilter, channelFilter, dateFrom])

  const invalidCount = touchpoints.filter((t) => t.isPostConversion || !t.isValid).length

  const columns = [
    {
      key: 'id',
      label: 'Touchpoint ID',
      sortable: true,
      render: (r) => <span className="font-mono text-xs font-semibold text-blue-700">{r.id}</span>,
    },
    {
      key: 'contactId',
      label: 'Contact',
      sortable: true,
      render: (r) => (
        <div>
          <p className="font-medium text-slate-900">{r.contactName}</p>
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
    { key: 'channelName', label: 'Channel', sortable: true },
    {
      key: 'creativeId',
      label: 'Creative ID',
      render: (r) => <span className="font-mono text-xs text-slate-600">{r.creativeId}</span>,
    },
    {
      key: 'interactionType',
      label: 'Interaction Type',
      sortable: true,
      render: (r) => (
        <div>
          <p className="font-medium text-slate-900">{r.interactionType}</p>
          {r.isPostConversion && (
            <span className="mt-0.5 inline-flex items-center gap-1 text-[11px] font-semibold text-rose-700">
              <AlertCircle className="h-3 w-3" />
              Post-conversion (excluded)
            </span>
          )}
        </div>
      ),
    },
    {
      key: 'timestamp',
      label: 'Timestamp',
      sortable: true,
      render: (r) => formatDateTime(r.timestamp),
    },
    { key: 'device', label: 'Device', sortable: true },
    {
      key: 'isOnline',
      label: 'Mode',
      render: (r) => (
        <span className="inline-flex items-center gap-1 text-xs text-slate-700">
          {r.isOnline ? (
            <>
              <Globe className="h-3.5 w-3.5 text-blue-600" />
              Online
            </>
          ) : (
            <>
              <WifiOff className="h-3.5 w-3.5 text-violet-600" />
              Offline
            </>
          )}
        </span>
      ),
    },
    { key: 'source', label: 'Source', sortable: true },
    {
      key: 'isValid',
      label: 'Validity',
      render: (r) => (
        <Badge status={r.isPostConversion || !r.isValid ? 'Invalid' : 'Valid'} dot>
          {r.isPostConversion ? 'Post-Conv Invalid' : r.isValid ? 'Valid' : 'Invalid'}
        </Badge>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title="Touchpoint Management"
        description="Chronological marketing interactions across online and offline channels with post-conversion governance."
        badge={
          <div className="flex items-center gap-2">
            <Badge variant="primary">{touchpoints.length} Touchpoints</Badge>
            {invalidCount > 0 && (
              <Badge variant="danger">{invalidCount} Post-Conversion Flagged</Badge>
            )}
          </div>
        }
      />

      <FilterBar
        searchValue={search}
        onSearchChange={setSearch}
        searchPlaceholder="Search touchpoint ID, contact, or interaction..."
        filters={[
          {
            id: 'tp-contact',
            label: 'Contact',
            value: contactFilter,
            onChange: setContactFilter,
            options: [
              { value: 'all', label: 'All Contacts' },
              ...contacts.map((c) => ({ value: c.id, label: `${c.id} · ${c.name}` })),
            ],
          },
          {
            id: 'tp-campaign',
            label: 'Campaign',
            value: campaignFilter,
            onChange: setCampaignFilter,
            options: [
              { value: 'all', label: 'All Campaigns' },
              ...campaigns.map((c) => ({ value: c.id, label: c.name })),
            ],
          },
          {
            id: 'tp-channel',
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
          <input
            type="date"
            aria-label="Filter touchpoints from date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="h-9 rounded-lg border border-slate-200 bg-white px-2.5 text-xs text-slate-700"
          />
        }
        onReset={() => {
          setSearch('')
          setContactFilter('all')
          setCampaignFilter('all')
          setChannelFilter('all')
          setDateFrom('')
        }}
      />

      <DataTable
        columns={columns}
        data={filtered}
        loading={loading}
        pageSize={10}
        rowClassName={(row) =>
          row.isPostConversion || !row.isValid ? 'bg-rose-50/70 hover:bg-rose-50' : ''
        }
      />
    </div>
  )
}

