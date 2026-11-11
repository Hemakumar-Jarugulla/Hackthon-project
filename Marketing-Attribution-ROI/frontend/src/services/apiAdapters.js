const PRESERVED_MODEL_KEYS = new Set([
  'first_touch',
  'last_touch',
  'linear',
  'time_decay',
  'position_based',
])

function snakeToCamel(key) {
  if (PRESERVED_MODEL_KEYS.has(key)) return key
  return key.replace(/_([a-z0-9])/g, (_, ch) => ch.toUpperCase())
}

/**
 * Recursively converts backend snake_case JSON dictionaries into React camelCase objects
 * while keeping the 5 attribution methodology keys intact for comparison matrices.
 */
export function toCamelCaseDeep(value) {
  if (Array.isArray(value)) {
    return value.map((item) => toCamelCaseDeep(item))
  }
  if (value && typeof value === 'object' && value.constructor === Object) {
    const out = {}
    for (const [k, v] of Object.entries(value)) {
      out[snakeToCamel(k)] = toCamelCaseDeep(v)
    }
    return out
  }
  return value
}

export function adaptCampaign(row) {
  const c = toCamelCaseDeep(row || {})
  return {
    ...c,
    channelId: c.channelId || c.channel || '',
    creativeId: c.creativeId || c.primaryCreativeId || '',
    audienceId: c.audienceId || c.primaryAudienceId || '',
    creativeName: c.creativeName || c.primaryCreativeName || '—',
    audienceName: c.audienceName || c.primaryAudienceName || '—',
    budget: Number(c.budget ?? 0),
    spend: Number(c.spend ?? 0),
    attributedRevenue: Number(c.attributedRevenue ?? 0),
    leads: Number(c.leads ?? c.leadsCount ?? 0),
    conversions: Number(c.conversions ?? c.conversionsCount ?? 0),
    roi: c.roi !== null && c.roi !== undefined ? Number(c.roi) : null,
    roas: c.roas !== null && c.roas !== undefined ? Number(c.roas) : null,
  }
}

export function toBackendCampaignPayload(payload = {}) {
  return {
    name: payload.name,
    description: payload.description ?? '',
    channel: payload.channelId ?? payload.channel,
    budget: Number(payload.budget ?? 0),
    currency: payload.currency || 'USD',
    start_date: payload.startDate ?? payload.start_date,
    end_date: payload.endDate ?? payload.end_date,
    objective: payload.objective || 'Lead Generation',
    status: payload.status || 'Draft',
    is_paid_campaign: payload.isPaidCampaign ?? payload.is_paid_campaign ?? true,
    creative_ids: payload.creativeIds ?? (payload.creativeId ? [payload.creativeId] : []),
    audience_ids: payload.audienceIds ?? (payload.audienceId ? [payload.audienceId] : []),
  }
}

export function adaptChannel(row) {
  const ch = toCamelCaseDeep(row || {})
  return {
    ...ch,
    type: ch.type || ch.channelType || 'Other',
    totalCampaigns: Number(ch.totalCampaigns ?? ch.campaignsCount ?? 0),
    totalSpend: Number(ch.totalSpend ?? 0),
    totalLeads: Number(ch.totalLeads ?? ch.leadsCount ?? 0),
    revenue: Number(ch.revenue ?? ch.attributedRevenue ?? 0),
    roi: ch.roi !== null && ch.roi !== undefined ? Number(ch.roi) : null,
  }
}

export function toBackendChannelPayload(payload = {}) {
  return {
    name: payload.name,
    channel_type: payload.type ?? payload.channelType ?? payload.channel_type,
    description: payload.description ?? '',
    status: payload.status || 'Active',
  }
}

export function adaptCreative(row) {
  const crt = toCamelCaseDeep(row || {})
  return {
    ...crt,
    type: crt.type || crt.creativeType || 'Responsive Search Ad',
    campaignId: crt.campaignId || crt.primaryCampaign || '',
    campaignName: crt.campaignName || crt.primaryCampaignName || '—',
  }
}

export function toBackendCreativePayload(payload = {}) {
  return {
    name: payload.name,
    creative_type: payload.type ?? payload.creativeType ?? payload.creative_type,
    primary_campaign: payload.campaignId || payload.primaryCampaign || null,
    description: payload.description ?? '',
    start_date: payload.startDate || payload.start_date || null,
    end_date: payload.endDate || payload.end_date || null,
    status: payload.status || 'Active',
  }
}

export function adaptAudience(row) {
  const aud = toCamelCaseDeep(row || {})
  return {
    ...aud,
    type: aud.type || aud.audienceType || 'Intent Keywords',
    size: Number(aud.size ?? aud.estimatedSize ?? 0),
    campaignName:
      aud.campaignName ||
      (Array.isArray(aud.linkedCampaigns) && aud.linkedCampaigns[0]?.name) ||
      'Multiple Campaigns',
  }
}

export function toBackendAudiencePayload(payload = {}) {
  return {
    name: payload.name,
    audience_type: payload.type ?? payload.audienceType ?? payload.audience_type,
    estimated_size: Number(payload.size ?? payload.estimatedSize ?? 0),
    criteria: payload.criteria ?? '',
    status: payload.status || 'Active',
    effective_from: payload.effectiveFrom || payload.effective_from || null,
    effective_to: payload.effectiveTo || payload.effective_to || null,
  }
}

export function adaptContact(row) {
  const con = toCamelCaseDeep(row || {})
  return {
    ...con,
    touchpointCount: Number(con.touchpointCount ?? 0),
    orderCount: Number(con.orderCount ?? 0),
    totalRevenue: Number(con.totalRevenue ?? 0),
  }
}

export function toBackendContactPayload(payload = {}) {
  return {
    name: payload.name,
    email: payload.email,
    phone: payload.phone ?? '',
    company: payload.company ?? '',
    source: payload.source || 'Organic',
    created_date: payload.createdDate ?? payload.created_date,
    lifecycle_status: payload.lifecycleStatus ?? payload.lifecycle_status ?? 'Subscriber',
  }
}

export function adaptTouchpoint(row) {
  const tp = toCamelCaseDeep(row || {})
  return {
    ...tp,
    contactId: tp.contactId || tp.contact || '',
    campaignId: tp.campaignId || tp.campaign || null,
    channelId: tp.channelId || tp.channel || null,
    creativeId: tp.creativeId || tp.creative || null,
    device: tp.device || (tp.isOnline ? 'Desktop' : 'Offline'),
  }
}

export function adaptSession(row) {
  const s = toCamelCaseDeep(row || {})
  return {
    ...s,
    contactId: s.contactId ?? s.contact ?? null,
    campaignSource: s.campaignSource || s.campaign || '',
    campaignName: s.campaignName || s.campaign || 'Direct',
    contactName: s.contactName || (s.contact ? s.contact : 'Anonymous Visitor'),
  }
}

export function adaptLead(row) {
  const l = toCamelCaseDeep(row || {})
  return {
    ...l,
    contactId: l.contactId || l.contact || '',
    campaignId: l.campaignId || l.campaign || '',
    score: Number(l.score ?? 0),
  }
}

export function toBackendLeadPayload(payload = {}) {
  return {
    contact: payload.contactId ?? payload.contact,
    campaign: payload.campaignId || payload.campaign || null,
    source: payload.source || 'Direct',
    score: Number(payload.score ?? 50),
    created_date: payload.createdDate ?? payload.created_date,
    status: payload.status || 'New',
  }
}

export function adaptOpportunity(row) {
  const opp = toCamelCaseDeep(row || {})
  return {
    ...opp,
    contactId: opp.contactId || opp.contact || '',
    leadId: opp.leadId || opp.lead || '',
    expectedRevenue: Number(opp.expectedRevenue ?? 0),
    actualRevenue: Number(opp.actualRevenue ?? 0),
  }
}

export function toBackendOpportunityPayload(payload = {}) {
  return {
    lead: payload.leadId ?? payload.lead,
    contact: payload.contactId ?? payload.contact,
    name: payload.name,
    stage: payload.stage || 'New',
    expected_revenue: Number(payload.expectedRevenue ?? payload.expected_revenue ?? 0),
    actual_revenue: Number(payload.actualRevenue ?? payload.actual_revenue ?? 0),
    closing_date: payload.closingDate ?? payload.closing_date,
    status: payload.status || 'Open',
  }
}

export function adaptOrder(row) {
  const ord = toCamelCaseDeep(row || {})
  return {
    ...ord,
    contactId: ord.contactId || ord.contact || '',
    opportunityId: ord.opportunityId || ord.opportunity || '',
    revenue: Number(ord.revenue ?? 0),
  }
}

export function toBackendOrderPayload(payload = {}) {
  return {
    opportunity: payload.opportunityId ?? payload.opportunity,
    contact: payload.contactId ?? payload.contact,
    order_date: payload.orderDate ?? payload.order_date,
    revenue: Number(payload.revenue ?? 0),
    currency: payload.currency || 'USD',
    payment_status: payload.paymentStatus ?? payload.payment_status ?? 'Paid',
    verification_status: payload.verificationStatus ?? payload.verification_status ?? 'Valid',
    notes: payload.notes ?? '',
  }
}

export function adaptCost(row) {
  const cost = toCamelCaseDeep(row || {})
  return {
    ...cost,
    campaignId: cost.campaignId || cost.campaign || '',
    channelId: cost.channelId || cost.channel || '',
    amount: Number(cost.amount ?? 0),
    campaignCurrency: cost.campaignCurrency || 'USD',
    currencyMismatch: Boolean(cost.currencyMismatch ?? cost.hasCurrencyMismatch),
  }
}

export function toBackendCostPayload(payload = {}) {
  return {
    campaign: payload.campaignId ?? payload.campaign,
    channel: payload.channelId ?? payload.channel ?? null,
    category: payload.category || 'Media Spend',
    amount: Number(payload.amount ?? 0),
    currency: payload.currency || 'USD',
    spend_date: payload.spendDate ?? payload.spend_date,
    description: payload.description ?? '',
  }
}

export function adaptContactJourney(payload) {
  const j = toCamelCaseDeep(payload || {})
  const creditsSource = j.attributionCredits || j.attributionResults || []
  return {
    ...j,
    contact: j.contact ? adaptContact(j.contact) : null,
    touchpoints: (j.touchpoints || []).map(adaptTouchpoint),
    sessions: (j.sessions || []).map(adaptSession),
    leads: (j.leads || []).map(adaptLead),
    opportunities: (j.opportunities || []).map(adaptOpportunity),
    orders: (j.orders || []).map(adaptOrder),
    attributionCredits: creditsSource.map((c) => ({
      ...c,
      weightPercent: Number(c.weightPercent ?? 0),
      creditAmount: Number(c.creditAmount ?? c.attributedRevenue ?? 0),
    })),
    timeline: (j.timeline || []).map((ev) => ({
      ...ev,
      isInvalid: Boolean(ev.isInvalid),
    })),
  }
}

export function adaptAttributionRunResult(payload) {
  const res = toCamelCaseDeep(payload || {})
  return {
    ...res,
    totalAttributedRevenue: Number(res.totalAttributedRevenue ?? 0),
    totalClosedValidRevenue: Number(res.totalClosedValidRevenue ?? 0),
    campaignResults: (res.campaignResults || []).map((r) => ({
      ...r,
      attributedRevenue: Number(r.attributedRevenue ?? 0),
      conversions: Number(r.conversions ?? 0),
      sharePercent: Number(r.sharePercent ?? 0),
    })),
    channelResults: (res.channelResults || []).map((r) => ({
      ...r,
      attributedRevenue: Number(r.attributedRevenue ?? 0),
      conversions: Number(r.conversions ?? 0),
      sharePercent: Number(r.sharePercent ?? 0),
    })),
  }
}

export function adaptComparisonResponse(payload) {
  const res = toCamelCaseDeep(payload || {})
  const normalizeModelValues = (row) => ({
    ...row,
    first_touch: Number(row.first_touch ?? 0),
    last_touch: Number(row.last_touch ?? 0),
    linear: Number(row.linear ?? 0),
    time_decay: Number(row.time_decay ?? 0),
    position_based: Number(row.position_based ?? 0),
  })
  return {
    ...res,
    campaignComparison: (res.campaignComparison || []).map(normalizeModelValues),
    channelComparison: (res.channelComparison || []).map(normalizeModelValues),
  }
}

export function adaptAttributionRunHistoryRow(row) {
  const r = toCamelCaseDeep(row || {})
  return {
    ...r,
    runId: r.runId || r.id,
    period: r.period || r.periodLabel || 'All Time',
    conversionWindowDays: Number(r.conversionWindowDays ?? 90),
    validOrdersProcessed: Number(r.validOrdersProcessed ?? 0),
    totalAttributedRevenue: Number(r.totalAttributedRevenue ?? 0),
  }
}

export function adaptException(row) {
  return toCamelCaseDeep(row || {})
}

export function adaptValidationReport(payload) {
  const rep = toCamelCaseDeep(payload || {})
  return {
    ...rep,
    checks: (rep.checks || []).map((c) => ({
      ...c,
      recordsChecked: Number(c.recordsChecked ?? 0),
      failedRecords: Number(c.failedRecords ?? 0),
    })),
    history: (rep.history || []).map((h) => ({
      ...h,
      totalChecks: Number(h.totalChecks ?? 0),
      passedChecks: Number(h.passedChecks ?? 0),
      failedChecks: Number(h.failedChecks ?? 0),
      warningChecks: Number(h.warningChecks ?? 0),
    })),
  }
}

export function adaptDashboardAnalytics(payload) {
  const d = toCamelCaseDeep(payload || {})
  const k = d.kpis || {}
  const c = d.charts || {}
  const w = d.widgets || {}
  return {
    kpis: {
      ...k,
      totalCampaigns: Number(k.totalCampaigns ?? 0),
      totalSpend: Number(k.totalSpend ?? k.marketingSpend ?? 0),
      totalContacts: Number(k.totalContacts ?? 0),
      totalTouchpoints: Number(k.totalTouchpoints ?? 0),
      totalLeads: Number(k.totalLeads ?? 0),
      totalOpportunities: Number(k.totalOpportunities ?? 0),
      closedRevenue: Number(k.closedRevenue ?? k.actualClosedRevenue ?? 0),
      attributedRevenue: Number(k.attributedRevenue ?? 0),
      blendedRoi: Number(k.blendedRoi ?? k.roi ?? 0),
      roas: k.roas !== null && k.roas !== undefined ? Number(k.roas) : 0,
    },
    charts: {
      monthlySeries: (c.monthlySeries || []).map((m) => ({
        ...m,
        spend: Number(m.spend ?? 0),
        revenue: Number(m.revenue ?? m.closedRevenue ?? 0),
        attributedRevenue: Number(m.attributedRevenue ?? 0),
      })),
      campaignRoiRanking: (c.campaignRoiRanking || []).map((r) => ({
        ...r,
        roi: Number(r.roi ?? 0),
        spend: Number(r.spend ?? 0),
        attributedRevenue: Number(r.attributedRevenue ?? 0),
      })),
      channelPerformance: (c.channelPerformance || []).map((ch) => ({
        ...ch,
        channel: ch.channel || ch.name || '',
        spend: Number(ch.spend ?? 0),
        revenue: Number(ch.revenue ?? ch.attributedRevenue ?? 0),
        attributedRevenue: Number(ch.attributedRevenue ?? 0),
        roi: ch.roi !== null && ch.roi !== undefined ? Number(ch.roi) : 0,
      })),
      funnelData: c.funnelData || [],
      modelDistribution: (c.modelDistribution || []).map((m) => ({
        ...m,
        value: Number(m.value ?? 0),
      })),
      journeyDistribution: c.journeyDistribution || [],
      exceptionDistribution: c.exceptionDistribution || [],
    },
    widgets: {
      topCampaigns: (w.topCampaigns || []).map((cmp) => ({
        ...cmp,
        id: cmp.id || cmp.campaignId,
        spend: Number(cmp.spend ?? cmp.marketingSpend ?? 0),
        attributedRevenue: Number(cmp.attributedRevenue ?? 0),
        roi: cmp.roi !== null && cmp.roi !== undefined ? Number(cmp.roi) : null,
      })),
      recentTouchpoints: w.recentTouchpoints || [],
      dataQualityAlerts: w.dataQualityAlerts || [],
      recentLeads: w.recentLeads || [],
      recentOpportunities: (w.recentOpportunities || []).map((opp) => ({
        ...opp,
        expectedRevenue: Number(opp.expectedRevenue ?? 0),
        actualRevenue: Number(opp.actualRevenue ?? 0),
      })),
      recentAttributionRuns: (w.recentAttributionRuns || []).map((run) => ({
        ...run,
        runId: run.runId || run.id,
        conversionWindowDays: Number(run.conversionWindowDays ?? 90),
        validOrdersProcessed: Number(run.validOrdersProcessed ?? 0),
        totalAttributedRevenue: Number(run.totalAttributedRevenue ?? 0),
      })),
    },
  }
}

export function adaptRoiAnalytics(payload, trendsPayload = null) {
  const d = toCamelCaseDeep(payload || {})
  const t = trendsPayload ? toCamelCaseDeep(trendsPayload) : null
  const s = d.summary || {}
  const adaptCmpRow = (r) => ({
    ...r,
    id: r.campaignId || r.id,
    spend: Number(r.marketingSpend ?? r.spend ?? 0),
    attributedRevenue: Number(r.attributedRevenue ?? 0),
    pipelineValue: Number(r.pipelineValue ?? 0),
    roi: r.roi !== null && r.roi !== undefined ? Number(r.roi) : null,
    roas: r.roas !== null && r.roas !== undefined ? Number(r.roas) : null,
    cpl: r.cpl !== null && r.cpl !== undefined ? Number(r.cpl) : null,
    leads: Number(r.leads ?? 0),
    conversions: Number(r.conversions ?? 0),
  })
  return {
    summary: {
      totalSpend: Number(s.marketingSpend ?? 0),
      attributedRevenue: Number(s.attributedRevenue ?? 0),
      actualClosedRevenue: Number(s.actualClosedRevenue ?? 0),
      pipelineValue: Number(s.pipelineValue ?? 0),
      roi: s.roi !== null && s.roi !== undefined ? Number(s.roi) : 0,
      roas: s.roas !== null && s.roas !== undefined ? Number(s.roas) : 0,
      cpl: s.cpl !== null && s.cpl !== undefined ? Number(s.cpl) : 0,
      conversionRate: Number(s.conversionRate ?? 0),
      aov: Number(s.aov ?? 0),
      validOrderCount: Number(s.validOrdersCount ?? 0),
      totalLeads: Number(s.totalLeads ?? 0),
      convertedLeads: Number(s.convertedLeads ?? 0),
      mismatchedSpendByCurrency: s.mismatchedSpendByCurrency || {},
      currencyMismatchesCount: Number(s.currencyMismatchesCount ?? 0),
    },
    campaignRows: (d.campaignRows || []).map(adaptCmpRow),
    channelRows: (d.channelRows || []).map((ch) => ({
      ...ch,
      id: ch.channelId || ch.id,
      spend: Number(ch.marketingSpend ?? ch.spend ?? 0),
      attributedRevenue: Number(ch.attributedRevenue ?? 0),
      leads: Number(ch.leads ?? 0),
      roi: ch.roi !== null && ch.roi !== undefined ? Number(ch.roi) : null,
      roas: ch.roas !== null && ch.roas !== undefined ? Number(ch.roas) : null,
      cpl: ch.cpl !== null && ch.cpl !== undefined ? Number(ch.cpl) : null,
    })),
    monthlyRoi: ((t && t.monthlySeries) || []).map((m) => ({
      month: m.month,
      spend: Number(m.spend ?? 0),
      revenue: Number(m.revenue ?? m.closedRevenue ?? 0),
      roi: m.roi !== null && m.roi !== undefined ? Number(m.roi) : 0,
    })),
    bestCampaigns: (d.bestCampaigns || []).map(adaptCmpRow),
    lowestCampaigns: (d.lowestCampaigns || []).map(adaptCmpRow),
  }
}

export function adaptUserAccount(row) {
  const u = toCamelCaseDeep(row || {})
  return {
    ...u,
    id: u.userCode || String(u.id || ''),
    backendId: u.id,
    lastActive: u.lastActiveAt || u.lastLogin || u.dateJoined,
  }
}
