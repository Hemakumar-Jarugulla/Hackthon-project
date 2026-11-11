import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import {
  Bell,
  Calendar,
  ChevronDown,
  ChevronRight,
  LogOut,
  Menu,
  Search,
  Settings,
  User,
} from 'lucide-react'
import { useApp } from '../../hooks/useApp'
import { useAuth } from '../../hooks/useAuth'
import { useToast } from '../../hooks/useToast'
import { ALL_NAV_ITEMS, resolveRouteMeta } from '../../routes/navigation'
import { cn } from '../../utils/formatters'

/**
 * Top application bar featuring breadcrumbs, global module search,
 * reporting date range selector, notification center, settings link, and user menu.
 */
export function Topbar({ onOpenMobileSidebar }) {
  const location = useLocation()
  const navigate = useNavigate()
  const { showToast } = useToast()
  const { user, logout } = useAuth()
  const {
    dateRange,
    setDateRange,
    dateRangeOptions,
    globalSearch,
    setGlobalSearch,
    notifications,
    unreadCount,
    markNotificationRead,
    markAllNotificationsRead,
  } = useApp()

  const [searchFocused, setSearchFocused] = useState(false)
  const [notifOpen, setNotifOpen] = useState(false)
  const [profileOpen, setProfileOpen] = useState(false)

  const searchRef = useRef(null)
  const notifRef = useRef(null)
  const profileRef = useRef(null)

  const routeMeta = useMemo(
    () => resolveRouteMeta(location.pathname),
    [location.pathname]
  )

  const quickSearchResults = useMemo(() => {
    const query = globalSearch.trim().toLowerCase()
    if (!query) return ALL_NAV_ITEMS.slice(0, 6)
    return ALL_NAV_ITEMS.filter(
      (item) =>
        item.label.toLowerCase().includes(query) ||
        item.section.toLowerCase().includes(query) ||
        item.description.toLowerCase().includes(query)
    ).slice(0, 7)
  }, [globalSearch])

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (searchRef.current && !searchRef.current.contains(event.target)) {
        setSearchFocused(false)
      }
      if (notifRef.current && !notifRef.current.contains(event.target)) {
        setNotifOpen(false)
      }
      if (profileRef.current && !profileRef.current.contains(event.target)) {
        setProfileOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const initials = useMemo(() => {
    const parts = (user?.name || 'AM').split(' ')
    return parts
      .slice(0, 2)
      .map((p) => p[0])
      .join('')
      .toUpperCase()
  }, [user])

  const handleLogout = () => {
    setProfileOpen(false)
    logout()
    showToast({
      type: 'info',
      title: 'Signed Out',
      message: 'You have been signed out of AttributionIQ.',
    })
    navigate('/login')
  }

  return (
    <header className="sticky top-0 z-30 flex h-16 shrink-0 items-center justify-between gap-4 border-b border-slate-200 bg-white px-4 sm:px-6 no-print">
      {/* Left: Mobile drawer trigger + Breadcrumbs */}
      <div className="flex min-w-0 items-center gap-3">
        <button
          type="button"
          onClick={onOpenMobileSidebar}
          aria-label="Open navigation menu"
          className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 lg:hidden cursor-pointer"
        >
          <Menu className="h-5 w-5" />
        </button>

        <nav aria-label="Breadcrumb" className="hidden sm:flex items-center gap-1.5 text-xs">
          <Link
            to="/dashboard"
            className="font-medium text-slate-500 hover:text-slate-900"
          >
            AttributionIQ
          </Link>
          <ChevronRight className="h-3.5 w-3.5 text-slate-400" />
          <span className="font-medium text-slate-500">
            {routeMeta.section}
          </span>
          <ChevronRight className="h-3.5 w-3.5 text-slate-400" />
          {routeMeta.parentPath ? (
            <>
              <Link
                to={routeMeta.parentPath}
                className="font-medium text-slate-500 hover:text-slate-900"
              >
                {routeMeta.label}
              </Link>
              <ChevronRight className="h-3.5 w-3.5 text-slate-400" />
              <span className="font-semibold text-slate-900">
                {routeMeta.detailLabel}
              </span>
            </>
          ) : (
            <span className="font-semibold text-slate-900">
              {routeMeta.label}
            </span>
          )}
        </nav>

        <span className="text-sm font-semibold text-slate-900 sm:hidden truncate">
          {routeMeta.detailLabel || routeMeta.label}
        </span>
      </div>

      {/* Right: Search, Date Range, Notifications, Settings, Profile */}
      <div className="flex items-center gap-2 sm:gap-3">
        {/* Global search */}
        <div ref={searchRef} className="relative hidden md:block w-64 lg:w-72">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            type="search"
            value={globalSearch}
            onFocus={() => setSearchFocused(true)}
            onChange={(e) => {
              setGlobalSearch(e.target.value)
              setSearchFocused(true)
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && quickSearchResults.length > 0) {
                navigate(quickSearchResults[0].path)
                setSearchFocused(false)
              }
            }}
            placeholder="Jump to module, reports, ROI..."
            className="h-9 w-full rounded-lg border border-slate-200 bg-slate-50 pl-9 pr-3 text-xs text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20"
          />

          {searchFocused && (
            <div className="absolute left-0 right-0 top-11 z-40 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl">
              <div className="border-b border-slate-100 px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                Quick Navigation
              </div>
              {quickSearchResults.length === 0 ? (
                <div className="px-3 py-4 text-center text-xs text-slate-500">
                  No matching modules for &ldquo;{globalSearch}&rdquo;
                </div>
              ) : (
                <ul className="max-h-64 overflow-y-auto divide-y divide-slate-100">
                  {quickSearchResults.map((item) => {
                    const Icon = item.icon
                    return (
                      <li key={item.path}>
                        <button
                          type="button"
                          onClick={() => {
                            navigate(item.path)
                            setSearchFocused(false)
                          }}
                          className="flex w-full items-center gap-2.5 px-3 py-2.5 text-left hover:bg-slate-50 cursor-pointer"
                        >
                          <Icon className="h-4 w-4 shrink-0 text-blue-600" />
                          <div className="min-w-0 flex-1">
                            <p className="truncate text-xs font-semibold text-slate-900">
                              {item.label}
                            </p>
                            <p className="truncate text-[11px] text-slate-500">
                              {item.section}
                            </p>
                          </div>
                        </button>
                      </li>
                    )
                  })}
                </ul>
              )}
            </div>
          )}
        </div>

        {/* Date range selector */}
        <div className="hidden sm:flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50/70 px-2.5 h-9">
          <Calendar className="h-3.5 w-3.5 text-slate-500 shrink-0" />
          <select
            aria-label="Global reporting date range"
            value={dateRange}
            onChange={(e) => {
              setDateRange(e.target.value)
              showToast({
                type: 'info',
                title: 'Reporting Period Updated',
                message: `Switched global window to ${
                  dateRangeOptions.find((o) => o.value === e.target.value)?.label
                }.`,
              })
            }}
            className="bg-transparent text-xs font-medium text-slate-700 focus:outline-none cursor-pointer"
          >
            {dateRangeOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Notifications */}
        <div ref={notifRef} className="relative">
          <button
            type="button"
            onClick={() => setNotifOpen((prev) => !prev)}
            aria-label="Notifications"
            className="relative flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 hover:text-slate-900 cursor-pointer"
          >
            <Bell className="h-4 w-4" />
            {unreadCount > 0 && (
              <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-rose-600 px-1 text-[10px] font-bold text-white">
                {unreadCount}
              </span>
            )}
          </button>

          {notifOpen && (
            <div className="absolute right-0 top-11 z-40 w-80 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl">
              <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
                <span className="text-xs font-semibold text-slate-900">
                  Notifications ({unreadCount} unread)
                </span>
                {unreadCount > 0 && (
                  <button
                    type="button"
                    onClick={markAllNotificationsRead}
                    className="text-[11px] font-semibold text-blue-600 hover:text-blue-700 cursor-pointer"
                  >
                    Mark all read
                  </button>
                )}
              </div>

              <ul className="max-h-72 overflow-y-auto divide-y divide-slate-100">
                {notifications.map((item) => (
                  <li key={item.id}>
                    <button
                      type="button"
                      onClick={() => {
                        markNotificationRead(item.id)
                        setNotifOpen(false)
                        navigate(item.route)
                      }}
                      className={cn(
                        'flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-slate-50 cursor-pointer',
                        !item.read && 'bg-blue-50/40'
                      )}
                    >
                      <span
                        className={cn(
                          'mt-1.5 h-2 w-2 shrink-0 rounded-full',
                          item.severity === 'critical'
                            ? 'bg-rose-500'
                            : item.severity === 'warning'
                              ? 'bg-amber-500'
                              : 'bg-blue-500'
                        )}
                      />
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between gap-2">
                          <p className="truncate text-xs font-semibold text-slate-900">
                            {item.title}
                          </p>
                          <span className="shrink-0 text-[10px] text-slate-400">
                            {item.time}
                          </span>
                        </div>
                        <p className="mt-0.5 text-xs text-slate-600 leading-snug">
                          {item.message}
                        </p>
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Settings quick action */}
        <button
          type="button"
          onClick={() => navigate('/settings')}
          aria-label="Settings"
          title="Settings"
          className="hidden sm:flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 hover:text-slate-900 cursor-pointer"
        >
          <Settings className="h-4 w-4" />
        </button>

        {/* User profile dropdown */}
        <div ref={profileRef} className="relative">
          <button
            type="button"
            onClick={() => setProfileOpen((prev) => !prev)}
            className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white py-1 pl-1.5 pr-2.5 hover:bg-slate-50 cursor-pointer"
          >
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-slate-900 text-xs font-semibold text-white">
              {initials}
            </div>
            <div className="hidden lg:block text-left leading-tight">
              <p className="text-xs font-semibold text-slate-900">
                {user?.name || 'Alex Morgan'}
              </p>
              <p className="text-[10px] text-slate-500">
                {user?.role || 'Marketing Ops'}
              </p>
            </div>
            <ChevronDown className="h-3.5 w-3.5 text-slate-400" />
          </button>

          {profileOpen && (
            <div className="absolute right-0 top-11 z-40 w-56 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl">
              <div className="border-b border-slate-100 px-4 py-3">
                <p className="text-xs font-semibold text-slate-900">
                  {user?.name}
                </p>
                <p className="truncate text-[11px] text-slate-500">
                  {user?.email}
                </p>
              </div>
              <div className="p-1.5 space-y-0.5">
                <button
                  type="button"
                  onClick={() => {
                    setProfileOpen(false)
                    navigate('/profile')
                  }}
                  className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 cursor-pointer"
                >
                  <User className="h-3.5 w-3.5 text-slate-400" />
                  User Profile
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setProfileOpen(false)
                    navigate('/settings')
                  }}
                  className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 cursor-pointer"
                >
                  <Settings className="h-3.5 w-3.5 text-slate-400" />
                  Workspace Settings
                </button>
              </div>
              <div className="border-t border-slate-100 p-1.5">
                <button
                  type="button"
                  onClick={handleLogout}
                  className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-xs font-semibold text-rose-600 hover:bg-rose-50 cursor-pointer"
                >
                  <LogOut className="h-3.5 w-3.5" />
                  Sign Out
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
