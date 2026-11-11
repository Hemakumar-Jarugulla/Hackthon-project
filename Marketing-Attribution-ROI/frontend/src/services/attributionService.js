import {
  compareAllModels,
  runAttributionModel,
} from '../utils/attributionEngine'
import {
  apiClient,
  fetchAllPaginated,
  unwrapApiData,
  USE_MOCK_DATA,
} from './api'
import {
  adaptAttributionRunHistoryRow,
  adaptAttributionRunResult,
  adaptComparisonResponse,
  toCamelCaseDeep,
} from './apiAdapters'
import { getCollection, saveCollection } from './mockStorage'

export const attributionService = {
  async getModelsConfig() {
    if (!USE_MOCK_DATA) {
      const rows = await fetchAllPaginated('/attribution/models/')
      return rows.map(toCamelCaseDeep)
    }
    const data = getCollection('attribution')
    return data.models || []
  },

  async getCalculationHistory() {
    if (!USE_MOCK_DATA) {
      const rows = await fetchAllPaginated('/attribution/runs/')
      return rows.map(adaptAttributionRunHistoryRow)
    }
    const data = getCollection('attribution')
    return data.calculationHistory || []
  },

  async calculateAttribution({
    modelId = 'position_based',
    conversionWindowDays = 90,
    dateRange = 'all_time',
    persist = false,
  } = {}) {
    if (!USE_MOCK_DATA) {
      if (persist) {
        const res = await apiClient.post('/attribution/run/', {
          model_id: modelId,
          conversion_window_days: conversionWindowDays,
          date_range: dateRange,
          persist: true,
        })
        return adaptAttributionRunResult(unwrapApiData(res.data))
      }
      const res = await apiClient.get('/attribution/run/', {
        params: {
          model_id: modelId,
          conversion_window_days: conversionWindowDays,
          date_range: dateRange,
        },
      })
      return adaptAttributionRunResult(unwrapApiData(res.data))
    }

    const orders = getCollection('orders')
    const touchpoints = getCollection('touchpoints')
    const campaigns = getCollection('campaigns')
    const channels = getCollection('channels')

    return runAttributionModel({
      orders,
      touchpoints,
      campaigns,
      channels,
      modelId,
      conversionWindowDays,
      dateRange,
    })
  },

  async compareModels({
    conversionWindowDays = 90,
    dateRange = 'all_time',
  } = {}) {
    if (!USE_MOCK_DATA) {
      const res = await apiClient.get('/attribution/compare/', {
        params: {
          conversion_window_days: conversionWindowDays,
          date_range: dateRange,
        },
      })
      return adaptComparisonResponse(unwrapApiData(res.data))
    }

    return compareAllModels({
      orders: getCollection('orders'),
      touchpoints: getCollection('touchpoints'),
      campaigns: getCollection('campaigns'),
      channels: getCollection('channels'),
      conversionWindowDays,
      dateRange,
    })
  },

  async recordCalculationRun({
    modelId = 'position_based',
    period,
    conversionWindowDays,
    totalAttributedRevenue,
    validOrdersProcessed,
  }) {
    if (!USE_MOCK_DATA) {
      const res = await apiClient.post('/attribution/run/', {
        model_id: modelId,
        conversion_window_days: conversionWindowDays,
        period_label: period,
        persist: true,
      })
      return adaptAttributionRunHistoryRow(unwrapApiData(res.data))
    }

    const data = getCollection('attribution')
    const nextRunNumber = (data.calculationHistory?.length || 0) + 12
    const newEntry = {
      runId: `ATTR-RUN-2026-${String(nextRunNumber).padStart(3, '0')}`,
      executedAt: new Date().toISOString(),
      period,
      conversionWindowDays,
      validOrdersProcessed,
      excludedDuplicateOrders: getCollection('orders').filter(
        (o) => o.verificationStatus === 'Duplicate'
      ).length,
      excludedPostConversionTouches: getCollection('touchpoints').filter(
        (t) => t.isPostConversion
      ).length,
      totalAttributedRevenue,
      status: 'Completed',
      triggeredBy: 'Manual Recalculation',
    }
    const updated = {
      ...data,
      calculationHistory: [newEntry, ...(data.calculationHistory || [])],
    }
    saveCollection('attribution', updated)
    return newEntry
  },
}
