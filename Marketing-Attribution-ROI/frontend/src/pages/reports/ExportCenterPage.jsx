import { useEffect, useState } from 'react'
import { FileDown, FileJson } from 'lucide-react'
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  PageHeader,
} from '../../components/common'
import { useToast } from '../../hooks/useToast'
import { analyticsService } from '../../services/analyticsService'
import { campaignService } from '../../services/campaignService'
import { contactService } from '../../services/contactService'
import { exportToCsv, exportToJson } from '../../utils/exportUtils'

export function ExportCenterPage() {
  const { showToast } = useToast()
  const [datasets, setDatasets] = useState([])

  useEffect(() => {
    Promise.all([
      campaignService.listCampaigns(),
      campaignService.listChannels(),
      campaignService.listCreatives(),
      campaignService.listAudiences(),
      contactService.listContacts(),
      contactService.listTouchpoints(),
      contactService.listSessions(),
      contactService.listLeads(),
      contactService.listOpportunities(),
      contactService.listOrders(),
      contactService.listCosts(),
      analyticsService.listExceptions(),
      analyticsService.getValidationReport(),
    ]).then(
      ([
        campaigns,
        channels,
        creatives,
        audiences,
        contacts,
        touchpoints,
        sessions,
        leads,
        opportunities,
        orders,
        costs,
        exceptions,
        validation,
      ]) => {
        setDatasets([
          { id: 'campaigns', name: 'Campaigns', category: 'Marketing', rows: campaigns },
          { id: 'channels', name: 'Channels', category: 'Marketing', rows: channels },
          { id: 'creatives', name: 'Creatives', category: 'Marketing', rows: creatives },
          { id: 'audiences', name: 'Audiences', category: 'Marketing', rows: audiences },
          { id: 'contacts', name: 'Contacts', category: 'Customer', rows: contacts },
          { id: 'touchpoints', name: 'Touchpoints', category: 'Customer', rows: touchpoints },
          { id: 'sessions', name: 'Web Sessions', category: 'Customer', rows: sessions },
          { id: 'leads', name: 'Leads', category: 'Sales', rows: leads },
          { id: 'opportunities', name: 'Opportunities', category: 'Sales', rows: opportunities },
          { id: 'orders', name: 'Orders', category: 'Financial', rows: orders },
          { id: 'costs', name: 'Marketing Costs', category: 'Financial', rows: costs },
          { id: 'exceptions', name: 'Exceptions', category: 'Data Quality', rows: exceptions },
          {
            id: 'validation',
            name: 'Validation Checks',
            category: 'Data Quality',
            rows: validation.checks || [],
          },
        ])
      }
    )
  }, [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="Export Center"
        description="Download normalized CSV or JSON extracts for any AttributionIQ entity directly in your browser."
        badge={<Badge variant="primary">{datasets.length} Datasets Ready</Badge>}
      />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {datasets.map((ds) => (
          <Card key={ds.id}>
            <CardHeader>
              <div>
                <CardTitle>{ds.name}</CardTitle>
                <CardDescription>
                  {ds.category} · {ds.rows.length} record(s)
                </CardDescription>
              </div>
              <Badge variant="default">{ds.rows.length}</Badge>
            </CardHeader>
            <CardContent className="flex items-center gap-2 pt-4">
              <Button
                variant="outline"
                size="sm"
                icon={FileDown}
                className="flex-1"
                disabled={ds.rows.length === 0}
                onClick={() => {
                  exportToCsv(`${ds.id}.csv`, ds.rows)
                  showToast({
                    type: 'success',
                    title: 'CSV Downloaded',
                    message: `Exported ${ds.rows.length} rows to ${ds.id}.csv`,
                  })
                }}
              >
                CSV
              </Button>
              <Button
                variant="outline"
                size="sm"
                icon={FileJson}
                className="flex-1"
                disabled={ds.rows.length === 0}
                onClick={() => {
                  exportToJson(`${ds.id}.json`, ds.rows)
                  showToast({
                    type: 'success',
                    title: 'JSON Downloaded',
                    message: `Exported ${ds.rows.length} rows to ${ds.id}.json`,
                  })
                }}
              >
                JSON
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}

