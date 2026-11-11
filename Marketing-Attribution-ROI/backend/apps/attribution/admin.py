from django.contrib import admin

from apps.attribution.models import AttributionModel, AttributionResult, AttributionRun

admin.site.register(AttributionModel)
admin.site.register(AttributionRun)
admin.site.register(AttributionResult)

