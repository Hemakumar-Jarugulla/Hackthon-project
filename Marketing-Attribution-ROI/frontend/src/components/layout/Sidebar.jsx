import { useEffect } from 'react'
import { NavLink } from 'react-router-dom'
import { PanelLeftClose, PanelLeftOpen, X } from 'lucide-react'
import { SIDEBAR_SECTIONS } from '../../routes/navigation'
import { cn } from '../../utils/formatters'

function SidebarContent({ collapsed, onToggleCollapse, onNavigate, isMobile = false }) {
  return (
    <div className="flex h-full flex-col bg-slate-900 text-slate-300 select-none">
      {/* Brand header */}
      <div
        className={cn(
          'flex h-16 shrink-0 items-center border-b border-slate-800/90 px-4',
          collapsed && !isMobile ? 'justify-center' : 'justify-between'
        )}
      >
        <NavLink
          to="/dashboard"
          onClick={onNavigate}
          className="flex items-center gap-2.5 overflow-hidden"
        >
          <img
            src="/logo.svg"
            alt="AttributionIQ"
            className="h-8 w-8 shrink-0 rounded-lg"
          />
          {(!collapsed || isMobile) && (
            <div className="min-w-0">
              <p className="truncate text-sm font-bold tracking-tight text-white">
                AttributionIQ
              </p>
              <p className="truncate text-[10px] font-medium uppercase tracking-wider text-slate-400">
                ROI Intelligence
              </p>
            </div>
          )}
        </NavLink>

        {isMobile ? (
          <button
            type="button"
            onClick={onNavigate}
            aria-label="Close navigation drawer"
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white cursor-pointer"
          >
            <X className="h-5 w-5" />
          </button>
        ) : (
          !collapsed && (
            <button
              type="button"
              onClick={onToggleCollapse}
              title="Collapse sidebar"
              aria-label="Collapse sidebar"
              className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white cursor-pointer"
            >
              <PanelLeftClose className="h-4 w-4" />
            </button>
          )
        )}
      </div>

      {/* Expand button when collapsed on desktop */}
      {collapsed && !isMobile && (
        <div className="flex justify-center border-b border-slate-800/70 py-2">
          <button
            type="button"
            onClick={onToggleCollapse}
            title="Expand sidebar"
            aria-label="Expand sidebar"
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white cursor-pointer"
          >
            <PanelLeftOpen className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Navigation sections */}
      <nav
        aria-label="Primary navigation"
        className="flex-1 overflow-y-auto px-3 py-4 space-y-5"
      >
        {SIDEBAR_SECTIONS.map((section) => (
          <div key={section.id}>
            {(!collapsed || isMobile) ? (
              <p className="px-2.5 pb-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                {section.label}
              </p>
            ) : (
              <div className="mx-2 mb-2 border-t border-slate-800" />
            )}

            <ul className="space-y-0.5">
              {section.items.map((item) => {
                const Icon = item.icon
                return (
                  <li key={item.path} className="relative group">
                    <NavLink
                      to={item.path}
                      end={item.path === '/attribution'}
                      onClick={onNavigate}
                      title={collapsed && !isMobile ? item.label : undefined}
                      className={({ isActive }) =>
                        cn(
                          'flex items-center gap-3 rounded-lg px-2.5 py-2 text-xs font-medium transition-all',
                          collapsed && !isMobile && 'justify-center px-2',
                          isActive
                            ? 'bg-blue-600 text-white shadow-xs'
                            : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                        )
                      }
                    >
                      <Icon className="h-4 w-4 shrink-0" />
                      {(!collapsed || isMobile) && (
                        <span className="truncate">{item.label}</span>
                      )}
                    </NavLink>

                    {/* Tooltip shown when desktop sidebar is collapsed */}
                    {collapsed && !isMobile && (
                      <div className="pointer-events-none fixed left-[76px] z-50 hidden -translate-y-8 whitespace-nowrap rounded-md bg-slate-950 px-2.5 py-1 text-xs font-medium text-white shadow-lg border border-slate-700 group-hover:block">
                        {item.label}
                      </div>
                    )}
                  </li>
                )
              })}
            </ul>
          </div>
        ))}
      </nav>

      {/* Sidebar footer */}
      <div className="shrink-0 border-t border-slate-800/90 p-3">
        {(!collapsed || isMobile) ? (
          <div className="rounded-lg bg-slate-950/70 border border-slate-800 px-3 py-2.5">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-slate-200">
                Mock Data Mode
              </span>
              <span className="h-2 w-2 rounded-full bg-emerald-400" />
            </div>
            <p className="mt-0.5 text-[10px] text-slate-400">
              Django API target configured
            </p>
          </div>
        ) : (
          <div
            title="Mock Data Mode Active"
            className="flex justify-center py-1"
          >
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-400" />
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * Responsive enterprise dark-navy sidebar with desktop collapse, tooltips, and mobile drawer.
 */
export function Sidebar({
  collapsed,
  onToggleCollapse,
  mobileOpen,
  onCloseMobile,
}) {
  useEffect(() => {
    if (!mobileOpen) return undefined
    const handleEsc = (e) => {
      if (e.key === 'Escape') onCloseMobile()
    }
    window.addEventListener('keydown', handleEsc)
    return () => window.removeEventListener('keydown', handleEsc)
  }, [mobileOpen, onCloseMobile])

  return (
    <>
      {/* Desktop persistent sidebar */}
      <aside
        className={cn(
          'hidden lg:flex lg:flex-col lg:shrink-0 border-r border-slate-800 transition-all duration-200 no-print',
          collapsed ? 'lg:w-[68px]' : 'lg:w-64'
        )}
      >
        <SidebarContent
          collapsed={collapsed}
          onToggleCollapse={onToggleCollapse}
        />
      </aside>

      {/* Mobile slide-over drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 flex lg:hidden no-print">
          <div
            onClick={onCloseMobile}
            className="fixed inset-0 bg-slate-950/60 backdrop-blur-[1px]"
            aria-hidden="true"
          />
          <aside className="relative z-10 flex w-72 max-w-[85vw] flex-col shadow-2xl">
            <SidebarContent
              collapsed={false}
              isMobile
              onNavigate={onCloseMobile}
            />
          </aside>
        </div>
      )}
    </>
  )
}
