import { useCallback, useState } from 'react'
import { AppContext, DATE_RANGE_OPTIONS } from './appStore'

const INITIAL_NOTIFICATIONS = [
  {
    id: 'NOTIF-01',
    title: 'Duplicate Revenue Exception',
    message: 'Order ORD-2026-000014 flagged for duplicate attribution credit.',
    severity: 'critical',
    time: '12m ago',
    route: '/exceptions',
    read: false,
  },
  {
    id: 'NOTIF-02',
    title: 'Missing Campaign Cost Alert',
    message: 'CMP-2026-000004 has active spend without a verified cost ledger entry.',
    severity: 'warning',
    time: '1h ago',
    route: '/costs',
    read: false,
  },
  {
    id: 'NOTIF-03',
    title: 'Attribution Run Completed',
    message: 'Multi-touch models recalculated across 5 attribution methodologies.',
    severity: 'info',
    time: '3h ago',
    route: '/attribution/comparison',
    read: true,
  },
]

/**
 * Provides global workspace filters (dateRange, globalSearch), sidebar state,
 * and header notification state.
 */
export function AppProvider({ children }) {
  const [dateRange, setDateRange] = useState('ytd_2026')
  const [globalSearch, setGlobalSearch] = useState('')
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [notifications, setNotifications] = useState(INITIAL_NOTIFICATIONS)

  const toggleSidebar = useCallback(() => {
    setSidebarCollapsed((prev) => !prev)
  }, [])

  const markNotificationRead = useCallback((id) => {
    setNotifications((prev) =>
      prev.map((item) => (item.id === id ? { ...item, read: true } : item))
    )
  }, [])

  const markAllNotificationsRead = useCallback(() => {
    setNotifications((prev) => prev.map((item) => ({ ...item, read: true })))
  }, [])

  const unreadCount = notifications.filter((n) => !n.read).length

  return (
    <AppContext.Provider
      value={{
        dateRange,
        setDateRange,
        dateRangeOptions: DATE_RANGE_OPTIONS,
        globalSearch,
        setGlobalSearch,
        sidebarCollapsed,
        setSidebarCollapsed,
        toggleSidebar,
        notifications,
        unreadCount,
        markNotificationRead,
        markAllNotificationsRead,
      }}
    >
      {children}
    </AppContext.Provider>
  )
}
