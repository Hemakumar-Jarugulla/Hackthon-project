"""
Root URL configuration for AttributionIQ backend.

Versioned REST endpoints are mounted under `/api/v1/`.
OpenAPI schema and interactive Swagger documentation live under `/api/schema/` and `/api/docs/`.
"""

from django.contrib import admin
from django.urls import include, path, reverse_lazy
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.accounts.urls import auth_urlpatterns, users_urlpatterns
from common.utils import HealthCheckView

urlpatterns = [
    path('', RedirectView.as_view(url=reverse_lazy('swagger-ui'), permanent=False), name='home'),
    path('admin/', admin.site.urls),
    path('api/v1/health/', HealthCheckView.as_view(), name='api-health'),
    path('api/v1/auth/', include(auth_urlpatterns)),
    path('api/v1/users/', include(users_urlpatterns)),
    path('api/v1/channels/', include('apps.channels.urls')),
    path('api/v1/campaigns/', include('apps.campaigns.urls')),
    path('api/v1/creatives/', include('apps.creatives.urls')),
    path('api/v1/audiences/', include('apps.audiences.urls')),
    path('api/v1/contacts/', include('apps.contacts.urls')),
    path('api/v1/sessions/', include('apps.web_sessions.urls')),
    path('api/v1/touchpoints/', include('apps.touchpoints.urls')),
    path('api/v1/leads/', include('apps.leads.urls')),
    path('api/v1/opportunities/', include('apps.opportunities.urls')),
    path('api/v1/orders/', include('apps.orders.urls')),
    path('api/v1/costs/', include('apps.costs.urls')),
    path('api/v1/attribution/', include('apps.attribution.urls')),
    path('api/v1/analytics/', include('apps.analytics.urls')),
    path('api/v1/exceptions/', include('apps.exceptions.urls')),
    path('api/v1/validation/', include('apps.validation.urls')),
    path('api/v1/audit/', include('apps.audit.urls')),
    path('api/v1/reports/', include('data_generator.urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path(
        'api/docs/',
        SpectacularSwaggerView.as_view(url_name='schema'),
        name='swagger-ui',
    ),
]
