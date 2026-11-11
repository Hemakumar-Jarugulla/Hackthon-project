import { computeTouchpointWeights } from '../utils/attributionEngine'
import {
  apiClient,
  fetchAllPaginated,
  unwrapApiData,
  USE_MOCK_DATA,
} from './api'
import {
  adaptContact,
  adaptContactJourney,
  adaptCost,
  adaptLead,
  adaptOpportunity,
  adaptOrder,
  adaptSession,
  adaptTouchpoint,
  toBackendCostPayload,
  toBackendLeadPayload,
  toBackendOpportunityPayload,
  toBackendOrderPayload,
} from './apiAdapters'
import { generateEntityId, getCollection, saveCollection } from './mockStorage'

export const contactService = {
  // Contacts
  async listContacts() {
    if (!USE_MOCK_DATA) {
      const rows = await fetchAllPaginated('/contacts/')
      return rows.map(adaptContact)
    }
    const contacts = getCollection('contacts')
    const touchpoints = getCollection('touchpoints')
    const orders = getCollection('orders')

    return contacts.map((contact) => {
      const contactTouches = touchpoints.filter((t) => t.contactId === contact.id)
      const contactOrders = orders.filter(
        (o) => o.contactId === contact.id && o.verificationStatus === 'Valid'
      )
      const totalRevenue = contactOrders.reduce((sum, o) => sum + Number(o.revenue || 0), 0)
      return {
        ...contact,
        touchpointCount: contactTouches.length,
        orderCount: contactOrders.length,
        totalRevenue,
      }
    })
  },

  async getContactJourney(contactId, modelId = 'position_based') {
    if (!USE_MOCK_DATA) {
      try {
        const res = await apiClient.get(`/contacts/${contactId}/journey/`, {
          params: { model_id: modelId },
        })
        return adaptContactJourney(unwrapApiData(res.data))
      } catch (err) {
        if (err?.response?.status === 404) return null
        throw err
      }
    }

    const contacts = getCollection('contacts')
    const contact = contacts.find((c) => c.id === contactId) || null
    if (!contact) return null

    const campaigns = getCollection('campaigns')
    const channels = getCollection('channels')
    const creatives = getCollection('creatives')
    const cmpMap = Object.fromEntries(campaigns.map((c) => [c.id, c.name]))
    const chMap = Object.fromEntries(channels.map((ch) => [ch.id, ch.name]))
    const crtMap = Object.fromEntries(creatives.map((cr) => [cr.id, cr.name]))

    const touchpoints = getCollection('touchpoints')
      .filter((t) => t.contactId === contactId)
      .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))
      .map((t) => ({
        ...t,
        campaignName: cmpMap[t.campaignId] || t.campaignId,
        channelName: chMap[t.channelId] || t.channelId,
        creativeName: crtMap[t.creativeId] || t.creativeId,
      }))

    const sessions = getCollection('sessions')
      .filter((s) => s.contactId === contactId)
      .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))

    const leads = getCollection('leads').filter((l) => l.contactId === contactId)
    const opportunities = getCollection('opportunities').filter(
      (o) => o.contactId === contactId
    )
    const orders = getCollection('orders').filter((o) => o.contactId === contactId)
    const validOrder = orders.find(
      (o) => o.verificationStatus === 'Valid' && o.paymentStatus === 'Paid'
    )

    let attributionCredits = []
    if (validOrder) {
      const orderMs = new Date(`${validOrder.orderDate}T23:59:59Z`).getTime()
      const eligible = touchpoints.filter(
        (t) =>
          !t.isPostConversion &&
          t.isValid !== false &&
          new Date(t.timestamp).getTime() <= orderMs
      )
      const weights = computeTouchpointWeights(eligible, modelId, orderMs)
      attributionCredits = eligible.map((t, idx) => ({
        touchpointId: t.id,
        campaignId: t.campaignId,
        campaignName: t.campaignName,
        channelName: t.channelName,
        timestamp: t.timestamp,
        weightPercent: Number((weights[idx] * 100).toFixed(1)),
        creditAmount: Number((validOrder.revenue * weights[idx]).toFixed(2)),
      }))
    }

    const timeline = [
      ...touchpoints.map((t) => ({
        id: `TL-${t.id}`,
        timestamp: t.timestamp,
        stageType: t.isOnline ? 'Campaign Touchpoint' : 'Offline Event',
        title: `${t.interactionType} · ${t.channelName}`,
        subtitle: `${t.campaignName} (${t.creativeName})`,
        meta: t.source,
        isInvalid: t.isPostConversion || t.isValid === false,
        badge: t.isPostConversion ? 'Post-Conversion' : t.isOnline ? 'Online' : 'Offline',
      })),
      ...sessions.map((s) => ({
        id: `TL-${s.id}`,
        timestamp: s.timestamp,
        stageType: 'Website Visit',
        title: `Visited ${s.landingPage}`,
        subtitle: `Session ${s.id} · Referrer: ${s.referrer}`,
        meta: s.deviceType,
        isInvalid: s.identityStatus === 'Unverified Link',
        badge: s.identityStatus,
      })),
      ...leads.map((l) => ({
        id: `TL-${l.id}`,
        timestamp: `${l.createdDate}T12:00:00Z`,
        stageType: 'Lead Created',
        title: `Lead ${l.id} Created (Score: ${l.score})`,
        subtitle: `Source: ${l.source} · Campaign: ${cmpMap[l.campaignId] || l.campaignId}`,
        meta: l.status,
        badge: l.status,
      })),
      ...opportunities.map((o) => ({
        id: `TL-${o.id}`,
        timestamp: `${o.closingDate}T15:00:00Z`,
        stageType: 'Opportunity',
        title: `${o.name}`,
        subtitle: `Stage: ${o.stage} · Expected $${Number(o.expectedRevenue).toLocaleString()}`,
        meta: o.status,
        badge: o.stage,
      })),
      ...orders.map((ord) => ({
        id: `TL-${ord.id}`,
        timestamp: `${ord.orderDate}T18:00:00Z`,
        stageType: 'Closed Order',
        title: `Order ${ord.id} · $${Number(ord.revenue).toLocaleString()} ${ord.currency}`,
        subtitle: `Payment: ${ord.paymentStatus} · Verification: ${ord.verificationStatus}`,
        meta: ord.verificationStatus,
        isInvalid: ord.verificationStatus === 'Duplicate',
        badge: ord.verificationStatus,
      })),
    ].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))

    return {
      contact,
      touchpoints,
      sessions,
      leads,
      opportunities,
      orders,
      attributionCredits,
      timeline,
    }
  },

  // Touchpoints
  async listTouchpoints() {
    if (!USE_MOCK_DATA) {
      const rows = await fetchAllPaginated('/touchpoints/')
      return rows.map(adaptTouchpoint)
    }
    const touchpoints = getCollection('touchpoints')
    const contacts = getCollection('contacts')
    const campaigns = getCollection('campaigns')
    const channels = getCollection('channels')
    const creatives = getCollection('creatives')

    const conMap = Object.fromEntries(contacts.map((c) => [c.id, c.name]))
    const cmpMap = Object.fromEntries(campaigns.map((c) => [c.id, c.name]))
    const chMap = Object.fromEntries(channels.map((ch) => [ch.id, ch.name]))
    const crtMap = Object.fromEntries(creatives.map((cr) => [cr.id, cr.name]))

    return [...touchpoints]
      .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
      .map((tp) => ({
        ...tp,
        contactName: conMap[tp.contactId] || tp.contactId,
        campaignName: cmpMap[tp.campaignId] || tp.campaignId,
        channelName: chMap[tp.channelId] || tp.channelId,
        creativeName: crtMap[tp.creativeId] || tp.creativeId,
      }))
  },

  // Sessions
  async listSessions() {
    if (!USE_MOCK_DATA) {
      const rows = await fetchAllPaginated('/sessions/')
      return rows.map(adaptSession)
    }
    const sessions = getCollection('sessions')
    const contacts = getCollection('contacts')
    const campaigns = getCollection('campaigns')
    const conMap = Object.fromEntries(contacts.map((c) => [c.id, c.name]))
    const cmpMap = Object.fromEntries(campaigns.map((c) => [c.id, c.name]))

    return [...sessions]
      .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
      .map((ses) => ({
        ...ses,
        contactName: ses.contactId ? conMap[ses.contactId] || ses.contactId : 'Anonymous Visitor',
        campaignName: cmpMap[ses.campaignSource] || ses.campaignSource,
      }))
  },

  // Leads
  async listLeads() {
    if (!USE_MOCK_DATA) {
      const rows = await fetchAllPaginated('/leads/')
      return rows.map(adaptLead)
    }
    const leads = getCollection('leads')
    const contacts = getCollection('contacts')
    const campaigns = getCollection('campaigns')
    const conMap = Object.fromEntries(contacts.map((c) => [c.id, c.name]))
    const cmpMap = Object.fromEntries(campaigns.map((c) => [c.id, c.name]))

    return leads.map((lead) => ({
      ...lead,
      contactName: conMap[lead.contactId] || lead.contactId,
      campaignName: cmpMap[lead.campaignId] || lead.campaignId,
    }))
  },

  async saveLead(payload, id = null) {
    if (!USE_MOCK_DATA) {
      const body = toBackendLeadPayload(payload)
      const res = id
        ? await apiClient.put(`/leads/${id}/`, body)
        : await apiClient.post('/leads/', body)
      return adaptLead(unwrapApiData(res.data))
    }
    const items = getCollection('leads')
    const normalized = { ...payload, score: Number(payload.score || 0) }
    if (id) {
      const updated = items.map((item) => (item.id === id ? { ...item, ...normalized } : item))
      saveCollection('leads', updated)
      return updated.find((i) => i.id === id)
    }
    const newItem = { ...normalized, id: generateEntityId('LEAD', items) }
    saveCollection('leads', [newItem, ...items])
    return newItem
  },

  // Opportunities
  async listOpportunities() {
    if (!USE_MOCK_DATA) {
      const rows = await fetchAllPaginated('/opportunities/')
      return rows.map(adaptOpportunity)
    }
    const opps = getCollection('opportunities')
    const contacts = getCollection('contacts')
    const conMap = Object.fromEntries(contacts.map((c) => [c.id, c.name]))
    return opps.map((opp) => ({
      ...opp,
      contactName: conMap[opp.contactId] || opp.contactId,
    }))
  },

  async saveOpportunity(payload, id = null) {
    if (!USE_MOCK_DATA) {
      const body = toBackendOpportunityPayload(payload)
      const res = id
        ? await apiClient.put(`/opportunities/${id}/`, body)
        : await apiClient.post('/opportunities/', body)
      return adaptOpportunity(unwrapApiData(res.data))
    }
    const items = getCollection('opportunities')
    const normalized = {
      ...payload,
      expectedRevenue: Number(payload.expectedRevenue || 0),
      actualRevenue: Number(payload.actualRevenue || 0),
    }
    if (id) {
      const updated = items.map((item) => (item.id === id ? { ...item, ...normalized } : item))
      saveCollection('opportunities', updated)
      return updated.find((i) => i.id === id)
    }
    const newItem = { ...normalized, id: generateEntityId('OPP', items) }
    saveCollection('opportunities', [newItem, ...items])
    return newItem
  },

  // Orders
  async listOrders() {
    if (!USE_MOCK_DATA) {
      const rows = await fetchAllPaginated('/orders/')
      return rows.map(adaptOrder)
    }
    const orders = getCollection('orders')
    const contacts = getCollection('contacts')
    const opps = getCollection('opportunities')
    const conMap = Object.fromEntries(contacts.map((c) => [c.id, c.name]))
    const oppMap = Object.fromEntries(opps.map((o) => [o.id, o.name]))

    return orders.map((ord) => ({
      ...ord,
      contactName: conMap[ord.contactId] || ord.contactId,
      opportunityName: oppMap[ord.opportunityId] || ord.opportunityId,
    }))
  },

  async saveOrder(payload, id = null) {
    if (!USE_MOCK_DATA) {
      const body = toBackendOrderPayload(payload)
      const res = id
        ? await apiClient.put(`/orders/${id}/`, body)
        : await apiClient.post('/orders/', body)
      return adaptOrder(unwrapApiData(res.data))
    }
    const items = getCollection('orders')
    const normalized = { ...payload, revenue: Number(payload.revenue || 0) }
    if (id) {
      const updated = items.map((item) => (item.id === id ? { ...item, ...normalized } : item))
      saveCollection('orders', updated)
      return updated.find((i) => i.id === id)
    }
    const newItem = { ...normalized, id: generateEntityId('ORD', items) }
    saveCollection('orders', [newItem, ...items])
    return newItem
  },

  // Marketing Costs
  async listCosts() {
    if (!USE_MOCK_DATA) {
      const rows = await fetchAllPaginated('/costs/')
      return rows.map(adaptCost)
    }
    const costs = getCollection('costs')
    const campaigns = getCollection('campaigns')
    const cmpMap = Object.fromEntries(campaigns.map((c) => [c.id, c]))

    return costs.map((cost) => {
      const cmp = cmpMap[cost.campaignId]
      return {
        ...cost,
        campaignName: cmp?.name || cost.campaignId,
        campaignCurrency: cmp?.currency || 'USD',
        currencyMismatch: Boolean(cmp && cmp.currency !== cost.currency),
      }
    })
  },

  async saveCost(payload, id = null) {
    if (!USE_MOCK_DATA) {
      const body = toBackendCostPayload(payload)
      const res = id
        ? await apiClient.put(`/costs/${id}/`, body)
        : await apiClient.post('/costs/', body)
      return adaptCost(unwrapApiData(res.data))
    }
    const items = getCollection('costs')
    const normalized = { ...payload, amount: Number(payload.amount || 0) }
    if (id) {
      const updated = items.map((item) => (item.id === id ? { ...item, ...normalized } : item))
      saveCollection('costs', updated)
      return updated.find((i) => i.id === id)
    }
    const newItem = { ...normalized, id: generateEntityId('COST', items) }
    saveCollection('costs', [newItem, ...items])
    return newItem
  },
}
