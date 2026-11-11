const MS_PER_DAY = 86_400_000

/**
 * Computes normalized attribution weights (summing to 1.0) for a chronologically sorted
 * list of eligible pre-conversion touchpoints.
 * @param {Array} touchpoints
 * @param {string} modelId
 * @param {number} orderTimeMs
 * @returns {number[]}
 */
export function computeTouchpointWeights(touchpoints, modelId, orderTimeMs) {
  const n = touchpoints.length
  if (n === 0) return []
  if (n === 1) return [1]

  switch (modelId) {
    case 'first_touch':
      return touchpoints.map((_, idx) => (idx === 0 ? 1 : 0))

    case 'last_touch':
      return touchpoints.map((_, idx) => (idx === n - 1 ? 1 : 0))

    case 'linear':
      return touchpoints.map(() => 1 / n)

    case 'time_decay': {
      const halfLifeMs = 7 * MS_PER_DAY
      const rawWeights = touchpoints.map((tp) => {
        const tpTime = new Date(tp.timestamp).getTime()
        const ageMs = Math.max(0, orderTimeMs - tpTime)
        return Math.pow(2, -ageMs / halfLifeMs)
      })
      const total = rawWeights.reduce((acc, val) => acc + val, 0)
      return total > 0 ? rawWeights.map((w) => w / total) : touchpoints.map(() => 1 / n)
    }

    case 'position_based': {
      if (n === 2) return [0.5, 0.5]
      const middleWeight = 0.2 / (n - 2)
      return touchpoints.map((_, idx) => {
        if (idx === 0 || idx === n - 1) return 0.4
        return middleWeight
      })
    }

    default:
      return touchpoints.map(() => 1 / n)
  }
}

/**
 * Checks whether an ISO date string falls inside the selected global date range.
 */
export function isWithinDateRange(dateStr, dateRange = 'all_time') {
  if (!dateStr || dateRange === 'all_time' || dateRange === 'ytd_2026') {
    return true
  }
  const referenceNow = new Date('2026-11-11T23:59:59Z').getTime()
  const target = new Date(dateStr).getTime()
  if (Number.isNaN(target)) return true

  const days = dateRange === 'last_30_days' ? 30 : 90
  return referenceNow - target <= days * MS_PER_DAY
}

/**
 * Runs multi-touch attribution across all valid paid orders for a given model & conversion window.
 */
export function runAttributionModel({
  orders = [],
  touchpoints = [],
  campaigns = [],
  channels = [],
  modelId = 'position_based',
  conversionWindowDays = 90,
  dateRange = 'all_time',
}) {
  const validOrders = orders.filter(
    (order) =>
      order.verificationStatus === 'Valid' &&
      order.paymentStatus === 'Paid' &&
      isWithinDateRange(order.orderDate, dateRange)
  )

  const campaignMap = Object.fromEntries(campaigns.map((c) => [c.id, c]))
  const channelMap = Object.fromEntries(channels.map((ch) => [ch.id, ch]))

  const byCampaign = Object.fromEntries(
    campaigns.map((c) => [
      c.id,
      {
        campaignId: c.id,
        campaignName: c.name,
        channelId: c.channelId,
        channelName: channelMap[c.channelId]?.name || 'Unknown',
        attributedRevenue: 0,
        conversions: 0,
        touchCreditCount: 0,
      },
    ])
  )

  const byChannel = Object.fromEntries(
    channels.map((ch) => [
      ch.id,
      {
        channelId: ch.id,
        channelName: ch.name,
        channelType: ch.type,
        attributedRevenue: 0,
        conversions: 0,
      },
    ])
  )

  const orderCredits = []
  let totalAttributedRevenue = 0
  const windowMs = conversionWindowDays * MS_PER_DAY

  validOrders.forEach((order) => {
    const orderTimeMs = new Date(`${order.orderDate}T23:59:59Z`).getTime()
    const eligibleTouches = touchpoints
      .filter((tp) => {
        if (tp.contactId !== order.contactId) return false
        if (tp.isPostConversion || tp.isValid === false) return false
        const tpTimeMs = new Date(tp.timestamp).getTime()
        return tpTimeMs <= orderTimeMs && orderTimeMs - tpTimeMs <= windowMs
      })
      .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))

    if (eligibleTouches.length === 0) return

    const weights = computeTouchpointWeights(eligibleTouches, modelId, orderTimeMs)
    const creditedCampaignsForOrder = new Set()
    const creditedChannelsForOrder = new Set()

    eligibleTouches.forEach((tp, idx) => {
      const weight = weights[idx]
      const credit = order.revenue * weight
      totalAttributedRevenue += credit

      if (byCampaign[tp.campaignId]) {
        byCampaign[tp.campaignId].attributedRevenue += credit
        byCampaign[tp.campaignId].touchCreditCount += weight
        if (weight > 0 && !creditedCampaignsForOrder.has(tp.campaignId)) {
          byCampaign[tp.campaignId].conversions += 1
          creditedCampaignsForOrder.add(tp.campaignId)
        }
      }

      if (byChannel[tp.channelId]) {
        byChannel[tp.channelId].attributedRevenue += credit
        if (weight > 0 && !creditedChannelsForOrder.has(tp.channelId)) {
          byChannel[tp.channelId].conversions += 1
          creditedChannelsForOrder.add(tp.channelId)
        }
      }

      orderCredits.push({
        orderId: order.id,
        contactId: order.contactId,
        orderDate: order.orderDate,
        orderRevenue: order.revenue,
        touchpointId: tp.id,
        campaignId: tp.campaignId,
        campaignName: campaignMap[tp.campaignId]?.name || tp.campaignId,
        channelName: channelMap[tp.channelId]?.name || tp.channelId,
        timestamp: tp.timestamp,
        weightPercent: Number((weight * 100).toFixed(2)),
        attributedCredit: Number(credit.toFixed(2)),
      })
    })
  })

  const campaignResults = Object.values(byCampaign).map((row) => ({
    ...row,
    attributedRevenue: Number(row.attributedRevenue.toFixed(2)),
    sharePercent:
      totalAttributedRevenue > 0
        ? Number(((row.attributedRevenue / totalAttributedRevenue) * 100).toFixed(1))
        : 0,
  }))

  const channelResults = Object.values(byChannel).map((row) => ({
    ...row,
    attributedRevenue: Number(row.attributedRevenue.toFixed(2)),
    sharePercent:
      totalAttributedRevenue > 0
        ? Number(((row.attributedRevenue / totalAttributedRevenue) * 100).toFixed(1))
        : 0,
  }))

  return {
    modelId,
    conversionWindowDays,
    validOrderCount: validOrders.length,
    totalAttributedRevenue: Number(totalAttributedRevenue.toFixed(2)),
    campaignResults,
    channelResults,
    orderCredits,
  }
}

/**
 * Generates side-by-side comparison rows across all 5 attribution models.
 */
export function compareAllModels(params) {
  const modelIds = [
    'first_touch',
    'last_touch',
    'linear',
    'time_decay',
    'position_based',
  ]

  const runs = Object.fromEntries(
    modelIds.map((modelId) => [
      modelId,
      runAttributionModel({ ...params, modelId }),
    ])
  )

  const campaignComparison = (params.campaigns || []).map((cmp) => {
    const row = {
      campaignId: cmp.id,
      campaignName: cmp.name,
      channelName:
        (params.channels || []).find((ch) => ch.id === cmp.channelId)?.name || 'Unknown',
    }
    modelIds.forEach((mId) => {
      const match = runs[mId].campaignResults.find((r) => r.campaignId === cmp.id)
      row[mId] = match ? match.attributedRevenue : 0
    })
    return row
  })

  const channelComparison = (params.channels || []).map((ch) => {
    const row = {
      channelId: ch.id,
      channelName: ch.name,
      channelType: ch.type,
    }
    modelIds.forEach((mId) => {
      const match = runs[mId].channelResults.find((r) => r.channelId === ch.id)
      row[mId] = match ? match.attributedRevenue : 0
    })
    return row
  })

  return {
    runs,
    campaignComparison,
    channelComparison,
  }
}

/**
 * Financial ROI formulas from Section 22 with safe zero-spend / missing-data guards.
 */
export function calculateRoi(attributedRevenue, marketingCost) {
  if (!marketingCost || marketingCost <= 0) return null
  return Number((((attributedRevenue - marketingCost) / marketingCost) * 100).toFixed(1))
}

export function calculateRoas(attributedRevenue, marketingCost) {
  if (!marketingCost || marketingCost <= 0) return null
  return Number((attributedRevenue / marketingCost).toFixed(2))
}

export function calculateCpl(marketingCost, totalLeads) {
  if (!totalLeads || totalLeads <= 0 || marketingCost === null || marketingCost === undefined) {
    return null
  }
  return Number((marketingCost / totalLeads).toFixed(2))
}

export function calculateConversionRate(convertedLeads, totalLeads) {
  if (!totalLeads || totalLeads <= 0) return 0
  return Number(((convertedLeads / totalLeads) * 100).toFixed(1))
}

export function calculateAov(totalClosedRevenue, validOrderCount) {
  if (!validOrderCount || validOrderCount <= 0) return 0
  return Number((totalClosedRevenue / validOrderCount).toFixed(2))
}

