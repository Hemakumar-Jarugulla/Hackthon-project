import { useEffect, useState } from 'react'
import { RotateCcw, Save } from 'lucide-react'
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  LoadingState,
  PageHeader,
} from '../../components/common'
import {
  FormField,
  SelectInput,
  TextInput,
} from '../../components/forms/FormField'
import { ConfirmDialog } from '../../components/modals/ConfirmDialog'
import { useApp } from '../../hooks/useApp'
import { useToast } from '../../hooks/useToast'
import { analyticsService } from '../../services/analyticsService'

export function SettingsPage() {
  const { setDateRange, dateRangeOptions } = useApp()
  const { showToast } = useToast()
  const [settings, setSettings] = useState(null)
  const [loading, setLoading] = useState(true)
  const [resetOpen, setResetOpen] = useState(false)

  useEffect(() => {
    analyticsService.getSettings().then((data) => {
      setSettings(data)
      setLoading(false)
    })
  }, [])

  const handleSave = async (e) => {
    e.preventDefault()
    await analyticsService.saveSettings(settings)
    setDateRange(settings.defaultReportingPeriod)
    showToast({
      type: 'success',
      title: 'Settings Saved',
      message: 'Workspace preferences persisted to localStorage.',
    })
  }

  const handleResetDemo = async () => {
    const restored = await analyticsService.resetDemoWorkspace()
    setSettings(restored)
    setResetOpen(false)
    showToast({
      type: 'warning',
      title: 'Demo Data Reset',
      message: 'All campaigns, costs, orders, and exceptions restored to seed state.',
    })
  }

  if (loading || !settings) {
    return <LoadingState message="Loading workspace settings..." />
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Workspace Settings"
        description="Configure currency preferences, reporting periods, attribution defaults, and notification governance."
        badge={<Badge variant="primary">Administration</Badge>}
        actions={
          <Button
            variant="outline"
            icon={RotateCcw}
            onClick={() => setResetOpen(true)}
          >
            Reset Demo Data
          </Button>
        }
      />

      <form onSubmit={handleSave} className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Application &amp; Currency Preferences</CardTitle>
              <CardDescription>
                Default financial and reporting window settings
              </CardDescription>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <FormField label="Workspace Name" htmlFor="set-ws">
              <TextInput
                id="set-ws"
                value={settings.workspaceName}
                onChange={(e) =>
                  setSettings({ ...settings, workspaceName: e.target.value })
                }
              />
            </FormField>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <FormField label="Primary Currency" htmlFor="set-curr">
                <SelectInput
                  id="set-curr"
                  value={settings.defaultCurrency}
                  onChange={(e) =>
                    setSettings({ ...settings, defaultCurrency: e.target.value })
                  }
                  options={[
                    { value: 'USD', label: 'USD ($)' },
                    { value: 'EUR', label: 'EUR (€)' },
                    { value: 'GBP', label: 'GBP (£)' },
                  ]}
                />
              </FormField>

              <FormField label="Default Reporting Period" htmlFor="set-period">
                <SelectInput
                  id="set-period"
                  value={settings.defaultReportingPeriod}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      defaultReportingPeriod: e.target.value,
                    })
                  }
                  options={dateRangeOptions}
                />
              </FormField>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <FormField label="Default Attribution Model" htmlFor="set-model">
                <SelectInput
                  id="set-model"
                  value={settings.defaultAttributionModel}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      defaultAttributionModel: e.target.value,
                    })
                  }
                  options={[
                    { value: 'position_based', label: 'Position Based (40/20/40)' },
                    { value: 'first_touch', label: 'First Touch' },
                    { value: 'last_touch', label: 'Last Touch' },
                    { value: 'linear', label: 'Linear' },
                    { value: 'time_decay', label: 'Time Decay' },
                  ]}
                />
              </FormField>

              <FormField label="Conversion Window (Days)" htmlFor="set-win">
                <SelectInput
                  id="set-win"
                  value={settings.defaultConversionWindowDays}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      defaultConversionWindowDays: Number(e.target.value),
                    })
                  }
                  options={[
                    { value: 30, label: '30 Days' },
                    { value: 60, label: '60 Days' },
                    { value: 90, label: '90 Days' },
                    { value: 180, label: '180 Days' },
                  ]}
                />
              </FormField>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div>
              <CardTitle>Notification &amp; Data Quality Rules</CardTitle>
              <CardDescription>
                Control alert triggers and attribution exclusions
              </CardDescription>
            </div>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            {[
              {
                key: 'criticalExceptions',
                label: 'Notify on Critical / Duplicate Revenue Exceptions',
              },
              {
                key: 'missingCosts',
                label: 'Alert when Active Paid Campaigns Omit Cost Entries',
              },
              {
                key: 'currencyMismatch',
                label: 'Flag Spend Currency Mismatches Against Campaign Base',
              },
              {
                key: 'weeklyDigest',
                label: 'Send Weekly Executive ROI Summary Digest',
              },
            ].map((item) => (
              <label
                key={item.key}
                className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 cursor-pointer"
              >
                <span className="font-medium text-slate-800">{item.label}</span>
                <input
                  type="checkbox"
                  checked={Boolean(settings.notifications?.[item.key])}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      notifications: {
                        ...settings.notifications,
                        [item.key]: e.target.checked,
                      },
                    })
                  }
                  className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                />
              </label>
            ))}

            <div className="pt-3 flex justify-end">
              <Button type="submit" icon={Save}>
                Save Preferences
              </Button>
            </div>
          </CardContent>
        </Card>
      </form>

      <ConfirmDialog
        isOpen={resetOpen}
        onClose={() => setResetOpen(false)}
        onConfirm={handleResetDemo}
        title="Reset Demo Workspace Data?"
        message="This clears all localStorage edits and restores every mock dataset to its original deterministic seed."
        confirmLabel="Reset Data"
      />
    </div>
  )
}

