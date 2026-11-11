"""URL routes for CSV & JSON Report Export endpoints."""

from django.urls import path

from data_generator.exports.views import (
    ReportCsvExportView,
    ReportDatasetsListView,
    ReportJsonExportView,
)

urlpatterns = [
    path('datasets/', ReportDatasetsListView.as_view(), name='reports-datasets'),
    path('export/csv/', ReportCsvExportView.as_view(), name='reports-export-csv'),
    path('export/json/', ReportJsonExportView.as_view(), name='reports-export-json'),
]

