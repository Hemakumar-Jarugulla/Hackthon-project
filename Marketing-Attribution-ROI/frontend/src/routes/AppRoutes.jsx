import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { AuthLayout } from '../layouts/AuthLayout'
import { MainLayout } from '../layouts/MainLayout'
import {
  ForgotPasswordPage,
  LoginPage,
  RegisterPage,
  ResetPasswordPage,
} from '../pages/auth/AuthPages'
import { ProfilePage } from '../pages/auth/ProfilePage'
import { AttributionComparisonPage } from '../pages/attribution/AttributionComparisonPage'
import { AttributionModelsPage } from '../pages/attribution/AttributionModelsPage'
import { AudiencesPage } from '../pages/audiences/AudiencesPage'
import { CampaignDetailPage } from '../pages/campaigns/CampaignDetailPage'
import { CampaignsPage } from '../pages/campaigns/CampaignsPage'
import { ChannelsPage } from '../pages/channels/ChannelsPage'
import { NotFoundPage } from '../pages/common/NotFoundPage'
import { ContactDetailPage } from '../pages/contacts/ContactDetailPage'
import { ContactsPage } from '../pages/contacts/ContactsPage'
import { CostsPage } from '../pages/costs/CostsPage'
import { CreativesPage } from '../pages/creatives/CreativesPage'
import { CustomerJourneyPage } from '../pages/customer-journey/CustomerJourneyPage'
import { DashboardPage } from '../pages/dashboard/DashboardPage'
import { ExceptionsPage } from '../pages/exceptions/ExceptionsPage'
import { LeadsPage } from '../pages/leads/LeadsPage'
import { OpportunitiesPage } from '../pages/opportunities/OpportunitiesPage'
import { OrdersPage } from '../pages/orders/OrdersPage'
import { ExportCenterPage } from '../pages/reports/ExportCenterPage'
import { ReportsPage } from '../pages/reports/ReportsPage'
import { RevenueAnalyticsPage } from '../pages/roi/RevenueAnalyticsPage'
import { RoiAnalyticsPage } from '../pages/roi/RoiAnalyticsPage'
import { SessionsPage } from '../pages/sessions/SessionsPage'
import { SettingsPage } from '../pages/settings/SettingsPage'
import { UserManagementPage } from '../pages/settings/UserManagementPage'
import { TouchpointsPage } from '../pages/touchpoints/TouchpointsPage'
import { ValidationPage } from '../pages/validation/ValidationPage'

function ProtectedRoute({ children }) {
  const { isAuthenticated } = useAuth()
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }
  return children
}

export function AppRoutes() {
  return (
    <Routes>
      {/* Authentication routes */}
      <Route element={<AuthLayout />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
      </Route>

      {/* Main application routes */}
      <Route
        element={
          <ProtectedRoute>
            <MainLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<Navigate to="/dashboard" replace />} />

        {/* Overview */}
        <Route path="/dashboard" element={<DashboardPage />} />

        {/* Marketing Management */}
        <Route path="/campaigns" element={<CampaignsPage />} />
        <Route path="/campaigns/:id" element={<CampaignDetailPage />} />
        <Route path="/channels" element={<ChannelsPage />} />
        <Route path="/creatives" element={<CreativesPage />} />
        <Route path="/audiences" element={<AudiencesPage />} />

        {/* Customer Management */}
        <Route path="/contacts" element={<ContactsPage />} />
        <Route path="/contacts/:id" element={<ContactDetailPage />} />
        <Route path="/touchpoints" element={<TouchpointsPage />} />
        <Route path="/sessions" element={<SessionsPage />} />
        <Route path="/customer-journey" element={<CustomerJourneyPage />} />

        {/* Sales Management */}
        <Route path="/leads" element={<LeadsPage />} />
        <Route path="/opportunities" element={<OpportunitiesPage />} />
        <Route path="/orders" element={<OrdersPage />} />

        {/* Financial Management */}
        <Route path="/costs" element={<CostsPage />} />
        <Route path="/revenue-analytics" element={<RevenueAnalyticsPage />} />
        <Route path="/roi" element={<RoiAnalyticsPage />} />

        {/* Attribution Analytics */}
        <Route path="/attribution" element={<AttributionModelsPage />} />
        <Route
          path="/attribution/comparison"
          element={<AttributionComparisonPage />}
        />

        {/* Data Quality */}
        <Route path="/exceptions" element={<ExceptionsPage />} />
        <Route path="/validation" element={<ValidationPage />} />

        {/* Reporting */}
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/exports" element={<ExportCenterPage />} />

        {/* Administration */}
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/users" element={<UserManagementPage />} />
        <Route path="/profile" element={<ProfilePage />} />

        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
