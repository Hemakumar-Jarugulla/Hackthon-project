"""URL routes for Customer Contacts API."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.contacts.views import ContactViewSet

router = DefaultRouter()
router.register(r'', ContactViewSet, basename='contacts')

urlpatterns = [
    path('', include(router.urls)),
]

