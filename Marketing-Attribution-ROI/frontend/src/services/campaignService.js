import {
  calculateRoi,
  runAttributionModel,
} from '../utils/attributionEngine'
import {
  apiClient,
  fetchAllPaginated,
  unwrapApiData,
  USE_MOCK_DATA,
} from './api'
import {
  adaptAudience,
  adaptCampaign,
  adaptChannel,
  adaptCreative,
  toBackendAudiencePayload,
  toBackendCampaignPayload,
  toBackendChannelPayload,
  toBackendCreativePayload,
} from './apiAdapters'
import { generateEntityId, getCollection, saveCollection } from './mockStorage'

/**
 * Enriches mock campaign records with live spend, attributed revenue, leads, and ROI.
 */
export function getEnrichedCampaigns(dateRange = 'all_time', modelId = 'position_based') {
  const campaigns = getCollection('campaigns')
  const channels = getCollection('channels')
  const creatives = getCollection('creatives')
  const audiences = getCollection('audiences')
  const costs = getCollection('costs')
  const leads = getCollection('leads')
  const orders = getCollection('orders')
  const touchpoints = getCollection('touchpoints')

  const attribution = runAttributionModel({
    orders,
    touchpoints,
    campaigns,
    channels,
    modelId,
    conversionWindowDays: 90,
    dateRange,
  })

  const channelMap = Object.fromEntries(channels.map((c) => [c.id, c]))
  const creativeMap = Object.fromEntries(creatives.map((c) => [c.id, c]))
  const audienceMap = Object.fromEntries(audiences.map((a) => [a.id, a]))

  return campaigns.map((cmp) => {
    const cmpCosts = costs.filter(
      (cost) => cost.campaignId === cmp.id && cost.currency === cmp.currency
    )
    const spend = cmpCosts.reduce((sum, cost) => sum + Number(cost.amount || 0), 0)
    const hasCurrencyMismatch = costs.some(
      (cost) => cost.campaignId === cmp.id && cost.currency !== cmp.currency
    )
    const missingCostAlert =
      cmp.budget > 0 && spend === 0 && touchpoints.some((tp) => tp.campaignId === cmp.id)

    const attrRow = attribution.campaignResults.find((r) => r.campaignId === cmp.id)
    const attributedRevenue = attrRow ? attrRow.attributedRevenue : 0
    const leadCount = leads.filter((l) => l.campaignId === cmp.id).length
    const roi = calculateRoi(attributedRevenue, spend)

    return {
      ...cmp,
      channelName: channelMap[cmp.channelId]?.name || 'Unassigned',
      channelType: channelMap[cmp.channelId]?.type || 'Other',
      creativeName: creativeMap[cmp.creativeId]?.name || '—',
      audienceName: audienceMap[cmp.audienceId]?.name || '—',
      spend,
      attributedRevenue,
      leads: leadCount,
      conversions: attrRow ? attrRow.conversions : 0,
      roi,
      hasCurrencyMismatch,
      missingCostAlert,
    }
  })
}

export const campaignService = {
  async listCampaigns({ dateRange = 'all_time', modelId = 'position_based' } = {}) {
    if (!USE_MOCK_DATA) {
      const rows = await fetchAllPaginated('/campaigns/', { date_range: dateRange, model_id: modelId })
      return rows.map(adaptCampaign)
    }
    return getEnrichedCampaigns(dateRange, modelId)
  },

  async getCampaignById(id, dateRange = 'all_time') {
    if (!USE_MOCK_DATA) {
      const res = await apiClient.get(`/campaigns/${id}/`)
      return adaptCampaign(unwrapApiData(res.data))
    }
    const all = getEnrichedCampaigns(dateRange)
    return all.find((c) => c.id === id) || null
  },

  async createCampaign(payload) {
    if (!USE_MOCK_DATA) {
      const res = await apiClient.post('/campaigns/', toBackendCampaignPayload(payload))
      return adaptCampaign(unwrapApiData(res.data))
    }
    const items = getCollection('campaigns')
    const newItem = {
      ...payload,
      id: generateEntityId('CMP', items),
      budget: Number(payload.budget || 0),
    }
    saveCollection('campaigns', [newItem, ...items])
    return newItem
  },

  async updateCampaign(id, payload) {
    if (!USE_MOCK_DATA) {
      const res = await apiClient.put(`/campaigns/${id}/`, toBackendCampaignPayload(payload))
      return adaptCampaign(unwrapApiData(res.data))
    }
    const items = getCollection('campaigns')
    const updated = items.map((item) =>
      item.id === id
        ? { ...item, ...payload, budget: Number(payload.budget ?? item.budget) }
        : item
    )
    saveCollection('campaigns', updated)
    return updated.find((i) => i.id === id)
  },

  async archiveCampaign(id) {
    if (!USE_MOCK_DATA) {
      const res = await apiClient.patch(`/campaigns/${id}/`, { status: 'Archived' })
      return adaptCampaign(unwrapApiData(res.data))
    }
    const items = getCollection('campaigns')
    const updated = items.map((item) =>
      item.id === id ? { ...item, status: 'Archived' } : item
    )
    saveCollection('campaigns', updated)
    return updated.find((i) => i.id === id)
  },

  // Channels
  async listChannels(dateRange = 'all_time') {
    if (!USE_MOCK_DATA) {
      const rows = await fetchAllPaginated('/channels/')
      return rows.map(adaptChannel)
    }
    const channels = getCollection('channels')
    const enrichedCampaigns = getEnrichedCampaigns(dateRange)

    return channels.map((ch) => {
      const chCampaigns = enrichedCampaigns.filter((c) => c.channelId === ch.id)
      const totalSpend = chCampaigns.reduce((s, c) => s + c.spend, 0)
      const totalRevenue = chCampaigns.reduce((s, c) => s + c.attributedRevenue, 0)
      const totalLeads = chCampaigns.reduce((s, c) => s + c.leads, 0)
      return {
        ...ch,
        totalCampaigns: chCampaigns.length,
        totalSpend,
        totalLeads,
        revenue: Number(totalRevenue.toFixed(2)),
        roi: calculateRoi(totalRevenue, totalSpend),
      }
    })
  },

  async saveChannel(payload, id = null) {
    if (!USE_MOCK_DATA) {
      const body = toBackendChannelPayload(payload)
      const res = id
        ? await apiClient.put(`/channels/${id}/`, body)
        : await apiClient.post('/channels/', body)
      return adaptChannel(unwrapApiData(res.data))
    }
    const items = getCollection('channels')
    if (id) {
      const updated = items.map((item) => (item.id === id ? { ...item, ...payload } : item))
      saveCollection('channels', updated)
      return updated.find((i) => i.id === id)
    }
    const newItem = { ...payload, id: generateEntityId('CHN', items) }
    saveCollection('channels', [newItem, ...items])
    return newItem
  },

  async deleteChannel(id) {
    if (!USE_MOCK_DATA) {
      await apiClient.delete(`/channels/${id}/`)
      return
    }
    const items = getCollection('channels')
    saveCollection('channels', items.filter((item) => item.id !== id))
  },

  // Creatives
  async listCreatives() {
    if (!USE_MOCK_DATA) {
      const rows = await fetchAllPaginated('/creatives/')
      return rows.map(adaptCreative)
    }
    const creatives = getCollection('creatives')
    const campaigns = getCollection('campaigns')
    const cmpMap = Object.fromEntries(campaigns.map((c) => [c.id, c.name]))
    return creatives.map((crt) => ({
      ...crt,
      campaignName: cmpMap[crt.campaignId] || crt.campaignId,
    }))
  },

  async saveCreative(payload, id = null) {
    if (!USE_MOCK_DATA) {
      const body = toBackendCreativePayload(payload)
      const res = id
        ? await apiClient.put(`/creatives/${id}/`, body)
        : await apiClient.post('/creatives/', body)
      return adaptCreative(unwrapApiData(res.data))
    }
    const items = getCollection('creatives')
    if (id) {
      const updated = items.map((item) => (item.id === id ? { ...item, ...payload } : item))
      saveCollection('creatives', updated)
      return updated.find((i) => i.id === id)
    }
    const newItem = { ...payload, id: generateEntityId('CRT', items) }
    saveCollection('creatives', [newItem, ...items])
    return newItem
  },

  // Audiences
  async listAudiences() {
    if (!USE_MOCK_DATA) {
      const rows = await fetchAllPaginated('/audiences/')
      return rows.map(adaptAudience)
    }
    const audiences = getCollection('audiences')
    const campaigns = getCollection('campaigns')
    const cmpMap = Object.fromEntries(campaigns.map((c) => [c.id, c.name]))
    return audiences.map((aud) => ({
      ...aud,
      campaignName: cmpMap[aud.campaignId] || aud.campaignId,
    }))
  },

  async saveAudience(payload, id = null) {
    if (!USE_MOCK_DATA) {
      const body = toBackendAudiencePayload(payload)
      const res = id
        ? await apiClient.put(`/audiences/${id}/`, body)
        : await apiClient.post('/audiences/', body)
      return adaptAudience(unwrapApiData(res.data))
    }
    const items = getCollection('audiences')
    const normalized = { ...payload, size: Number(payload.size || 0) }
    if (id) {
      const updated = items.map((item) => (item.id === id ? { ...item, ...normalized } : item))
      saveCollection('audiences', updated)
      return updated.find((i) => i.id === id)
    }
    const newItem = { ...normalized, id: generateEntityId('AUD', items) }
    saveCollection('audiences', [newItem, ...items])
    return newItem
  },
}
