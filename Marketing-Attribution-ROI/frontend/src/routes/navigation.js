import {
  Activity,
  AlertOctagon,
  BarChart3,
  Briefcase,
  CheckSquare,
  Coins,
  CreditCard,
  FileBarChart2,
  FileDown,
  GitBranch,
  Globe,
  Image,
  LayoutDashboard,
  Megaphone,
  Radio,
  Route,
  Scale,
  Settings,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  UserCheck,
  UserCog,
  Users,
} from 'lucide-react'

export const SIDEBAR_SECTIONS = [
  {
    id: 'overview',
    label: 'OVERVIEW',
    items: [
      {
        label: 'Dashboard',
        path: '/dashboard',
        icon: LayoutDashboard,
        description: 'Executive KPIs, revenue trends, and data quality alerts',
      },
    ],
  },
  {
    id: 'marketing',
    label: 'MARKETING MANAGEMENT',
    items: [
      {
        label: 'Campaigns',
        path: '/campaigns',
        icon: Megaphone,
        description: 'Create, monitor, and optimize marketing campaigns',
      },
      {
        label: 'Channels',
        path: '/channels',
        icon: Radio,
        description: 'Channel mix performance, spend, and attribution ROI',
      },
      {
        label: 'Creatives',
        path: '/creatives',
        icon: Image,
        description: 'Ad creatives, formats, active flight dates, and statuses',
      },
      {
        label: 'Audiences',
        path: '/audiences',
        icon: Users,
        description: 'Target audience segments and campaign associations',
      },
    ],
  },
  {
    id: 'customer',
    label: 'CUSTOMER MANAGEMENT',
    items: [
      {
        label: 'Contacts',
        path: '/contacts',
        icon: UserCheck,
        description: 'Unified contact directory and lifecycle stages',
      },
      {
        label: 'Touchpoints',
        path: '/touchpoints',
        icon: Activity,
        description: 'Chronological multi-channel interactions and validity flags',
      },
      {
        label: 'Web Sessions',
        path: '/sessions',
        icon: Globe,
        description: 'Identified vs anonymous sessions and landing pages',
      },
      {
        label: 'Customer Journey',
        path: '/customer-journey',
        icon: Route,
        description: 'End-to-end timeline from ad impression to closed order',
      },
    ],
  },
  {
    id: 'sales',
    label: 'SALES MANAGEMENT',
    items: [
      {
        label: 'Leads',
        path: '/leads',
        icon: Sparkles,
        description: 'Lead scoring, source tracking, and conversion funnel',
      },
      {
        label: 'Opportunities',
        path: '/opportunities',
        icon: Briefcase,
        description: 'Sales pipeline stages from qualification to closed won',
      },
      {
        label: 'Orders',
        path: '/orders',
        icon: CreditCard,
        description: 'Closed orders, payment status, and duplicate revenue checks',
      },
    ],
  },
  {
    id: 'financial',
    label: 'FINANCIAL MANAGEMENT',
    items: [
      {
        label: 'Marketing Costs',
        path: '/costs',
        icon: Coins,
        description: 'Campaign cost ledger, currencies, and missing-cost alerts',
      },
      {
        label: 'Revenue Analytics',
        path: '/revenue-analytics',
        icon: BarChart3,
        description: 'Attributed vs verified closed revenue breakdown',
      },
      {
        label: 'Campaign ROI',
        path: '/roi',
        icon: TrendingUp,
        description: 'ROI, ROAS, CPL, Conversion Rate, and AOV intelligence',
      },
    ],
  },
  {
    id: 'attribution',
    label: 'ATTRIBUTION ANALYTICS',
    items: [
      {
        label: 'Attribution Models',
        path: '/attribution',
        icon: GitBranch,
        description: 'First Touch, Last Touch, Linear, Time Decay & Position Based',
      },
      {
        label: 'Attribution Comparison',
        path: '/attribution/comparison',
        icon: Scale,
        description: 'Side-by-side model comparison across campaigns and channels',
      },
    ],
  },
  {
    id: 'data-quality',
    label: 'DATA QUALITY',
    items: [
      {
        label: 'Exception Management',
        path: '/exceptions',
        icon: AlertOctagon,
        description: 'Resolve attribution, duplicate revenue, and currency exceptions',
      },
      {
        label: 'Data Validation',
        path: '/validation',
        icon: CheckSquare,
        description: 'Integrity checks across keys, dates, totals, and lifecycles',
      },
    ],
  },
  {
    id: 'reporting',
    label: 'REPORTING',
    items: [
      {
        label: 'Reports',
        path: '/reports',
        icon: FileBarChart2,
        description: 'Printable executive and operational analytics reports',
      },
      {
        label: 'Export Center',
        path: '/exports',
        icon: FileDown,
        description: 'Download CSV and JSON datasets with custom filters',
      },
    ],
  },
  {
    id: 'administration',
    label: 'ADMINISTRATION',
    items: [
      {
        label: 'Settings',
        path: '/settings',
        icon: Settings,
        description: 'Workspace currency, reporting period, and notification rules',
      },
      {
        label: 'User Management',
        path: '/users',
        icon: UserCog,
        description: 'Team members, role access control, and permissions',
      },
    ],
  },
]

export const EXTRA_ROUTE_META = [
  {
    label: 'User Profile',
    path: '/profile',
    section: 'ACCOUNT',
    icon: ShieldCheck,
    description: 'Manage your personal profile, security, and preferences',
  },
]

/**
 * Flattened list of all navigation items for quick search & route resolution.
 */
export const ALL_NAV_ITEMS = [
  ...SIDEBAR_SECTIONS.flatMap((section) =>
    section.items.map((item) => ({
      ...item,
      section: section.label,
    }))
  ),
  ...EXTRA_ROUTE_META,
]

/**
 * Resolves breadcrumb trail for a given pathname.
 * @param {string} pathname
 * @returns {{ section: string, label: string, description: string, detailLabel?: string }}
 */
export function resolveRouteMeta(pathname) {
  const exactMatch = ALL_NAV_ITEMS.find((item) => item.path === pathname)
  if (exactMatch) return exactMatch

  if (pathname.startsWith('/campaigns/')) {
    const id = pathname.replace('/campaigns/', '')
    return {
      section: 'MARKETING MANAGEMENT',
      label: 'Campaigns',
      parentPath: '/campaigns',
      detailLabel: id,
      description: `Detailed performance and attribution metrics for ${id}`,
    }
  }

  if (pathname.startsWith('/contacts/')) {
    const id = pathname.replace('/contacts/', '')
    return {
      section: 'CUSTOMER MANAGEMENT',
      label: 'Contacts',
      parentPath: '/contacts',
      detailLabel: id,
      description: `Activity history and journey profile for ${id}`,
    }
  }

  return {
    section: 'PLATFORM',
    label: 'AttributionIQ',
    description: 'Marketing Attribution & ROI Intelligence Platform',
  }
}

