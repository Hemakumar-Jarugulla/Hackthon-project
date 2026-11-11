import {
  calculateAov,
  calculateConversionRate,
  calculateCpl,
  calculateRoas,
  calculateRoi,
  compareAllModels,
  isWithinDateRange,
  runAttributionModel,
} from '../utils/attributionEngine'
import {
  apiClient,
  fetchAllPaginated,
  unwrapApiData,
  USE_MOCK_DATA,
} from './api'
import {
  adaptComparisonResponse,
  adaptDashboardAnalytics,
  adaptException,
  adaptOrder,
  adaptRoiAnalytics,
  adaptUserAccount,
  adaptValidationReport,
  toCamelCaseDeep,
} from './apiAdapters'
import { getEnrichedCampaigns } from './campaignService'
import { generateEntityId, getCollection, resetAllMockData, saveCollection } from './mockStorage'

const MONTH_LABELS = [
  { key: '2026-01', month: 'Jan' },
  { key: '2026-02', month: 'Feb' },
  { key: '2026-03', month: 'Mar' },
  { key: '2026-04', month: 'Apr' },
  { key: '2026-05', month: 'May' },
  { key: '2026-06', month: 'Jun' },
  { key: '2026-07', month: 'Jul' },
  { key: '2026-08', month: 'Aug' },
  { key: '2026-09', month: 'Sep' },
  { key: '2026-10', month: 'Oct' },
]

export const analyticsService = {
  /**
   * Computes complete Dashboard KPIs, 8 visualizations, and operational widgets
   * from the shared mock database with optional campaign/channel/date filters.
   */
  async getDashboardSummary({
    dateRange = 'all_time',
    campaignId = 'all',
    channelId = 'all',
  } = {}) {
    if (!USE_MOCK_DATA) {
      const res = await apiClient.get('/analytics/dashboard/', {
        params: {
          date_range: dateRange,
          campaign_id: campaignId !== 'all' ? campaignId : undefined,
          channel_id: channelId !== 'all' ? channelId : undefined,
        },
      })
      return adaptDashboardAnalytics(unwrapApiData(res.data))
    }
    const allCampaigns = getEnrichedCampaigns(dateRange)
    const channels = getCollection('channels')
    const contacts = getCollection('contacts')
    const touchpoints = getCollection('touchpoints')
    const leads = getCollection('leads')
    const opportunities = getCollection('opportunities')
    const orders = getCollection('orders')
    const costs = getCollection('costs')
    const exceptions = getCollection('exceptions')
    const attributionData = getCollection('attribution')

    const filteredCampaigns = allCampaigns.filter((c) => {
      if (campaignId !== 'all' && c.id !== campaignId) return false
      if (channelId !== 'all' && c.channelId !== channelId) return false
      return true
    })
    const activeCampaignIds = new Set(filteredCampaigns.map((c) => c.id))

    const filteredTouchpoints = touchpoints.filter(
      (t) =>
        activeCampaignIds.has(t.campaignId) &&
        isWithinDateRange(t.timestamp, dateRange)
    )
    const filteredLeads = leads.filter(
      (l) =>
        activeCampaignIds.has(l.campaignId) &&
        isWithinDateRange(l.createdDate, dateRange)
    )
    const leadIds = new Set(filteredLeads.map((l) => l.id))
    const filteredOpps = opportunities.filter((o) =>
      campaignId === 'all' && channelId === 'all' ? true : leadIds.has(o.leadId)
    )
    const oppIds = new Set(filteredOpps.map((o) => o.id))

    const validOrders = orders.filter(
      (o) =>
        o.verificationStatus === 'Valid' &&
        o.paymentStatus === 'Paid' &&
        isWithinDateRange(o.orderDate, dateRange) &&
        (campaignId === 'all' && channelId === 'all' ? true : oppIds.has(o.opportunityId))
    )

    const validCosts = costs.filter(
      (cost) =>
        activeCampaignIds.has(cost.campaignId) &&
        cost.currency === 'USD' &&
        isWithinDateRange(cost.date, dateRange)
    )

    const totalSpend = validCosts.reduce((sum, c) => sum + Number(c.amount || 0), 0)
    const closedRevenue = validOrders.reduce((sum, o) => sum + Number(o.revenue || 0), 0)

    const attrRun = runAttributionModel({
      orders,
      touchpoints,
      campaigns: filteredCampaigns,
      channels,
      modelId: 'position_based',
      conversionWindowDays: 90,
      dateRange,
    })

    const attributedRevenue = attrRun.totalAttributedRevenue
    const blendedRoi = calculateRoi(attributedRevenue || closedRevenue, totalSpend)

    // 1 & 5. Monthly Revenue vs Spend series
    const monthlySeries = MONTH_LABELS.map(({ key, month }) => {
      const monthSpend = validCosts
        .filter((c) => c.date.startsWith(key))
        .reduce((s, c) => s + Number(c.amount || 0), 0)
      const monthRevenue = validOrders
        .filter((o) => o.orderDate.startsWith(key))
        .reduce((s, o) => s + Number(o.revenue || 0), 0)
      return {
        month,
        spend: monthSpend,
        revenue: monthRevenue,
      }
    })

    // 2. Campaign ROI Ranking
    const campaignRoiRanking = filteredCampaigns
      .filter((c) => c.roi !== null)
      .sort((a, b) => (b.roi ?? 0) - (a.roi ?? 0))
      .map((c) => ({
        name: c.name.length > 22 ? `${c.name.slice(0, 22)}...` : c.name,
        fullName: c.name,
        roi: c.roi,
        spend: c.spend,
        revenue: c.attributedRevenue,
      }))

    // 3. Channel Performance
    const channelPerformance = channels
      .filter((ch) => channelId === 'all' || ch.id === channelId)
      .map((ch) => {
        const chCampaigns = filteredCampaigns.filter((c) => c.channelId === ch.id)
        const chSpend = chCampaigns.reduce((s, c) => s + c.spend, 0)
        const chRevenue = chCampaigns.reduce((s, c) => s + c.attributedRevenue, 0)
        return {
          channel: ch.name,
          spend: chSpend,
          revenue: Number(chRevenue.toFixed(0)),
          leads: chCampaigns.reduce((s, c) => s + c.leads, 0),
        }
      })

    // 4. Lead Conversion Funnel
    const funnelData = [
      { stage: 'Touchpoints', count: filteredTouchpoints.length },
      { stage: 'Contacts', count: contacts.length },
      { stage: 'Leads', count: filteredLeads.length },
      { stage: 'Opportunities', count: filteredOpps.length },
      { stage: 'Closed Orders', count: validOrders.length },
    ]

    // 6. Attribution Model Distribution (Channel share under Position Based)
    const modelDistribution = attrRun.channelResults
      .filter((r) => r.attributedRevenue > 0)
      .map((r) => ({
        name: r.channelName,
        value: r.attributedRevenue,
      }))

    // 7. Customer Journey Distribution (Touchpoints per contact)
    const touchesPerContact = contacts.map((con) => ({
      id: con.id,
      count: touchpoints.filter((t) => t.contactId === con.id && t.isValid !== false).length,
    }))
    const journeyDistribution = [
      { bucket: '1 Touch', contacts: touchesPerContact.filter((c) => c.count <= 1).length },
      { bucket: '2 Touches', contacts: touchesPerContact.filter((c) => c.count === 2).length },
      { bucket: '3 Touches', contacts: touchesPerContact.filter((c) => c.count === 3).length },
      { bucket: '4+ Touches', contacts: touchesPerContact.filter((c) => c.count >= 4).length },
    ]

    // 8. Exception Distribution by Severity
    const severities = ['Critical', 'High', 'Medium', 'Low']
    const exceptionDistribution = severities.map((sev) => ({
      severity: sev,
      count: exceptions.filter((e) => e.severity === sev).length,
    }))

    return {
      kpis: {
        totalCampaigns: filteredCampaigns.length,
        totalSpend,
        totalContacts: contacts.length,
        totalTouchpoints: filteredTouchpoints.length,
        totalLeads: filteredLeads.length,
        totalOpportunities: filteredOpps.length,
        closedRevenue,
        blendedRoi: blendedRoi ?? 0,
      },
      charts: {
        monthlySeries,
        campaignRoiRanking,
        channelPerformance,
        funnelData,
        modelDistribution,
        journeyDistribution,
        exceptionDistribution,
      },
      widgets: {
        topCampaigns: [...filteredCampaigns]
          .sort((a, b) => b.attributedRevenue - a.attributedRevenue)
          .slice(0, 5),
        recentLeads: filteredLeads.slice(0, 5).map((l) => ({
          ...l,
          contactName: contacts.find((c) => c.id === l.contactId)?.name || l.contactId,
        })),
        recentOpportunities: filteredOpps.slice(0, 5),
        dataQualityAlerts: exceptions.slice(0, 5),
        recentAttributionRuns: (attributionData.calculationHistory || []).slice(0, 4),
        recentTouchpoints: [...filteredTouchpoints]
          .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
          .slice(0, 5),
      },
    }
  },

  /**
   * Computes advanced ROI, ROAS, CPL, Conversion Rate, and AOV metrics (Section 22).
   */
  async getRoiAnalytics({ dateRange = 'all_time', modelId = 'position_based' } = {}) {
    if (!USE_MOCK_DATA) {
      const [roiRes, trendsRes] = await Promise.all([
        apiClient.get('/analytics/roi/', {
          params: { date_range: dateRange, model_id: modelId },
        }),
        apiClient.get('/analytics/trends/', {
          params: { date_range: dateRange, model_id: modelId },
        }),
      ])
      return adaptRoiAnalytics(unwrapApiData(roiRes.data), unwrapApiData(trendsRes.data))
    }
    const campaigns = getEnrichedCampaigns(dateRange, modelId)
    const channels = getCollection('channels')
    const leads = getCollection('leads')
    const orders = getCollection('orders')
    const costs = getCollection('costs')

    const validOrders = orders.filter(
      (o) =>
        o.verificationStatus === 'Valid' &&
        o.paymentStatus === 'Paid' &&
        isWithinDateRange(o.orderDate, dateRange)
    )
    const actualClosedRevenue = validOrders.reduce((s, o) => s + Number(o.revenue || 0), 0)
    const attributedRevenue = campaigns.reduce((s, c) => s + c.attributedRevenue, 0)
    const totalSpend = costs
      .filter((c) => c.currency === 'USD' && isWithinDateRange(c.date, dateRange))
      .reduce((s, c) => s + Number(c.amount || 0), 0)

    const convertedLeads = leads.filter((l) => l.status === 'Converted').length
    const totalLeads = leads.length

    const campaignRows = campaigns.map((c) => ({
      ...c,
      roas: calculateRoas(c.attributedRevenue, c.spend),
      cpl: calculateCpl(c.spend, c.leads),
    }))

    const channelRows = channels.map((ch) => {
      const chCampaigns = campaignRows.filter((c) => c.channelId === ch.id)
      const spend = chCampaigns.reduce((s, c) => s + c.spend, 0)
      const attrRev = chCampaigns.reduce((s, c) => s + c.attributedRevenue, 0)
      const chLeads = chCampaigns.reduce((s, c) => s + c.leads, 0)
      return {
        ...ch,
        spend,
        attributedRevenue: Number(attrRev.toFixed(2)),
        leads: chLeads,
        roi: calculateRoi(attrRev, spend),
        roas: calculateRoas(attrRev, spend),
        cpl: calculateCpl(spend, chLeads),
      }
    })

    const monthlyRoi = MONTH_LABELS.map(({ key, month }) => {
      const mSpend = costs
        .filter((c) => c.currency === 'USD' && c.date.startsWith(key))
        .reduce((s, c) => s + Number(c.amount || 0), 0)
      const mRev = validOrders
        .filter((o) => o.orderDate.startsWith(key))
        .reduce((s, o) => s + Number(o.revenue || 0), 0)
      return {
        month,
        spend: mSpend,
        revenue: mRev,
        roi: mSpend > 0 ? Number((((mRev - mSpend) / mSpend) * 100).toFixed(1)) : 0,
      }
    })

    const rankedWithSpend = campaignRows
      .filter((c) => c.roi !== null)
      .sort((a, b) => b.roi - a.roi)

    return {
      summary: {
        totalSpend,
        attributedRevenue: Number(attributedRevenue.toFixed(2)),
        actualClosedRevenue,
        roi: calculateRoi(attributedRevenue, totalSpend),
        roas: calculateRoas(attributedRevenue, totalSpend),
        cpl: calculateCpl(totalSpend, totalLeads),
        conversionRate: calculateConversionRate(convertedLeads, totalLeads),
        aov: calculateAov(actualClosedRevenue, validOrders.length),
        validOrderCount: validOrders.length,
        totalLeads,
        convertedLeads,
      },
      campaignRows,
      channelRows,
      monthlyRoi,
      bestCampaigns: rankedWithSpend.slice(0, 3),
      lowestCampaigns: [...rankedWithSpend].reverse().slice(0, 3),
    }
  },

  // Exception Management
  async listExceptions() {
    if (!USE_MOCK_DATA) {
      const rows = await fetchAllPaginated('/exceptions/')
      return rows.map(adaptException)
    }
    return getCollection('exceptions')
  },

  async updateExceptionStatus(id, resolutionStatus, notes) {
    if (!USE_MOCK_DATA) {
      const action = resolutionStatus === 'Open' ? 'reopen' : 'resolve'
      const res = await apiClient.post(`/exceptions/${id}/${action}/`, {
        resolution_status: resolutionStatus,
        resolution_notes: notes ?? '',
      })
      return adaptException(unwrapApiData(res.data))
    }
    const items = getCollection('exceptions')
    const updated = items.map((item) =>
      item.id === id
        ? {
            ...item,
            resolutionStatus,
            notes: notes !== undefined ? notes : item.notes,
          }
        : item
    )
    saveCollection('exceptions', updated)
    return updated.find((i) => i.id === id)
  },

  // Data Validation
  async getValidationReport() {
    if (!USE_MOCK_DATA) {
      const res = await apiClient.get('/validation/report/')
      return adaptValidationReport(unwrapApiData(res.data))
    }
    return getCollection('validation')
  },

  async runValidationSuite() {
    if (!USE_MOCK_DATA) {
      const res = await apiClient.post('/validation/run/', {
        triggered_by: 'React Workspace Validation Trigger',
        sync_exceptions: true,
      })
      return adaptValidationReport(unwrapApiData(res.data))
    }
    const current = getCollection('validation')
    const nowIso = new Date().toISOString()
    const updatedChecks = current.checks.map((chk) => ({
      ...chk,
      lastRun: nowIso,
    }))
    const passed = updatedChecks.filter((c) => c.status === 'Passed').length
    const failed = updatedChecks.filter((c) => c.status === 'Failed').length
    const warnings = updatedChecks.filter((c) => c.status === 'Warning').length

    const nextHistory = {
      runId: `VAL-RUN-2026-${String(43 + current.history.length).padStart(3, '0')}`,
      timestamp: nowIso,
      totalChecks: updatedChecks.length,
      passed,
      failed,
      warnings,
      durationMs: 384,
      triggeredBy: 'Manual Validation Trigger',
    }

    const updated = {
      checks: updatedChecks,
      history: [nextHistory, ...current.history],
    }
    saveCollection('validation', updated)
    return updated
  },

  // Reports dataset builders
  async buildReportDataset(reportType, { dateRange = 'all_time', campaignId = 'all' } = {}) {
    if (!USE_MOCK_DATA) {
      if (reportType === 'attribution_comparison') {
        const res = await apiClient.get('/attribution/compare/', {
          params: { date_range: dateRange },
        })
        return adaptComparisonResponse(unwrapApiData(res.data)).campaignComparison || []
      }
      if (reportType === 'exception_report') {
        return analyticsService.listExceptions()
      }
      if (reportType === 'validation_report') {
        const rep = await analyticsService.getValidationReport()
        return rep.checks || []
      }
      if (reportType === 'revenue_analysis') {
        const rows = await fetchAllPaginated('/orders/')
        return rows.map(adaptOrder)
      }
      if (reportType === 'customer_journey') {
        const res = await apiClient.get('/reports/export/json/', { params: { entity: 'contacts' } })
        const raw = unwrapApiData(res.data)
        return Array.isArray(raw) ? raw.map(toCamelCaseDeep) : []
      }
      if (reportType === 'channel_performance') {
        const roiData = await analyticsService.getRoiAnalytics({ dateRange })
        return roiData.channelRows || []
      }
      const roiData = await analyticsService.getRoiAnalytics({ dateRange })
      const cmpRows = roiData.campaignRows || []
      return campaignId === 'all' ? cmpRows : cmpRows.filter((c) => c.id === campaignId || c.campaignId === campaignId)
    }

    const campaigns = getEnrichedCampaigns(dateRange)
    const filteredCampaigns =
      campaignId === 'all' ? campaigns : campaigns.filter((c) => c.id === campaignId)

    switch (reportType) {
      case 'campaign_performance':
        return filteredCampaigns
      case 'channel_performance': {
        const channels = getCollection('channels')
        return channels.map((ch) => {
          const list = filteredCampaigns.filter((c) => c.channelId === ch.id)
          const spend = list.reduce((s, c) => s + c.spend, 0)
          const revenue = list.reduce((s, c) => s + c.attributedRevenue, 0)
          return {
            channelId: ch.id,
            channelName: ch.name,
            channelType: ch.type,
            campaigns: list.length,
            spend,
            attributedRevenue: Number(revenue.toFixed(2)),
            roi: calculateRoi(revenue, spend) ?? 'N/A',
          }
        })
      }
      case 'roi_analysis':
        return filteredCampaigns.map((c) => ({
          campaignId: c.id,
          campaignName: c.name,
          spend: c.spend,
          attributedRevenue: c.attributedRevenue,
          roiPercent: c.roi ?? 'N/A',
          roas: calculateRoas(c.attributedRevenue, c.spend) ?? 'N/A',
          cpl: calculateCpl(c.spend, c.leads) ?? 'N/A',
        }))
      case 'attribution_comparison': {
        const comp = compareAllModels({
          orders: getCollection('orders'),
          touchpoints: getCollection('touchpoints'),
          campaigns: filteredCampaigns,
          channels: getCollection('channels'),
          conversionWindowDays: 90,
          dateRange,
        })
        return comp.campaignComparison
      }
      case 'customer_journey': {
        const contacts = getCollection('contacts')
        const touchpoints = getCollection('touchpoints')
        const orders = getCollection('orders')
        return contacts.map((con) => ({
          contactId: con.id,
          name: con.name,
          company: con.company,
          lifecycleStatus: con.lifecycleStatus,
          touchpoints: touchpoints.filter((t) => t.contactId === con.id).length,
          validOrders: orders.filter(
            (o) => o.contactId === con.id && o.verificationStatus === 'Valid'
          ).length,
        }))
      }
      case 'revenue_analysis':
        return getCollection('orders')
      case 'exception_report':
        return getCollection('exceptions')
      case 'validation_report':
        return getCollection('validation').checks
      default:
        return filteredCampaigns
    }
  },

  // Settings & Users
  async getSettings() {
    return getCollection('settings')
  },

  async saveSettings(settings) {
    return saveCollection('settings', settings)
  },

  async resetDemoWorkspace() {
    resetAllMockData()
    return getCollection('settings')
  },

  async listUsers() {
    if (!USE_MOCK_DATA) {
      const rows = await fetchAllPaginated('/users/')
      return rows.map(adaptUserAccount)
    }
    return getCollection('users')
  },

  async saveUser(payload, id = null) {
    if (!USE_MOCK_DATA) {
      const targetId = payload?.backendId || id
      const body = {
        name: payload.name,
        email: payload.email,
        role: payload.role,
        department: payload.department,
        status: payload.status,
      }
      const res = targetId
        ? await apiClient.patch(`/users/${targetId}/`, body)
        : await apiClient.post('/users/', body)
      return adaptUserAccount(unwrapApiData(res.data))
    }
    const items = getCollection('users')
    if (id) {
      const updated = items.map((item) => (item.id === id ? { ...item, ...payload } : item))
      saveCollection('users', updated)
      return updated.find((i) => i.id === id)
    }
    const newItem = {
      ...payload,
      id: generateEntityId('USR', items),
      lastActive: new Date().toISOString(),
    }
    saveCollection('users', [newItem, ...items])
    return newItem
  },
}

