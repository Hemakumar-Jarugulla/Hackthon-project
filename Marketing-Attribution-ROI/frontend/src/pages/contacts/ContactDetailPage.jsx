import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Mail, Phone, Route } from 'lucide-react'
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  EmptyState,
  LoadingState,
  PageHeader,
} from '../../components/common'
import { contactService } from '../../services/contactService'
import { formatCurrency, formatDate, formatDateTime } from '../../utils/formatters'

export function ContactDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [journey, setJourney] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true
    contactService.getContactJourney(id).then((data) => {
      if (!active) return
      setJourney(data)
      setLoading(false)
    })
    return () => {
      active = false
    }
  }, [id])

  if (loading) return <LoadingState message="Loading contact profile..." />
  if (!journey?.contact) {
    return (
      <EmptyState
        title="Contact not found"
        description={`No contact record exists for ID "${id}".`}
        actionLabel="Back to Contacts"
        onAction={() => navigate('/contacts')}
      />
    )
  }

  const { contact, touchpoints, sessions, orders } = journey

  return (
    <div className="space-y-6">
      <PageHeader
        title={contact.name}
        description={`${contact.company} · Acquired via ${contact.source}`}
        badge={
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs text-slate-500">{contact.id}</span>
            <Badge status={contact.lifecycleStatus} dot>
              {contact.lifecycleStatus}
            </Badge>
          </div>
        }
        actions={
          <>
            <Button
              variant="outline"
              icon={ArrowLeft}
              onClick={() => navigate('/contacts')}
            >
              Back
            </Button>
            <Button
              icon={Route}
              onClick={() => navigate(`/customer-journey?contactId=${contact.id}`)}
            >
              Open Journey Explorer
            </Button>
          </>
        }
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Contact Profile</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            <div className="flex items-center gap-2 text-slate-700">
              <Mail className="h-4 w-4 text-slate-400" />
              <span>{contact.email}</span>
            </div>
            <div className="flex items-center gap-2 text-slate-700">
              <Phone className="h-4 w-4 text-slate-400" />
              <span>{contact.phone}</span>
            </div>
            <div className="flex justify-between border-t border-slate-100 pt-3">
              <span className="text-slate-500">Created Date</span>
              <span className="font-semibold">{formatDate(contact.createdDate)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Touchpoints</span>
              <span className="font-semibold">{touchpoints.length}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Web Sessions</span>
              <span className="font-semibold">{sessions.length}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Valid Closed Revenue</span>
              <span className="font-bold text-emerald-700">
                {formatCurrency(
                  orders
                    .filter((o) => o.verificationStatus === 'Valid')
                    .reduce((s, o) => s + o.revenue, 0)
                )}
              </span>
            </div>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <div>
              <CardTitle>Activity History ({touchpoints.length})</CardTitle>
              <CardDescription>Recorded campaign touchpoints for {contact.name}</CardDescription>
            </div>
          </CardHeader>
          <CardContent className="divide-y divide-slate-100 p-0">
            {touchpoints.length === 0 ? (
              <p className="p-6 text-center text-xs text-slate-500">
                No touchpoints recorded for this contact.
              </p>
            ) : (
              touchpoints.map((tp) => (
                <div
                  key={tp.id}
                  className="flex flex-wrap items-center justify-between gap-2 px-5 py-3 text-xs"
                >
                  <div>
                    <p className="font-semibold text-slate-900">
                      {tp.interactionType} · {tp.channelName}
                    </p>
                    <p className="text-slate-500">
                      {tp.campaignName} ({tp.id})
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-slate-500">{formatDateTime(tp.timestamp)}</span>
                    <Badge status={tp.isPostConversion ? 'Invalid' : 'Valid'}>
                      {tp.isPostConversion ? 'Post-Conversion' : 'Valid'}
                    </Badge>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
