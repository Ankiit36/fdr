"""API URL configuration for the AICTE FDR Management Portal."""

from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from apps.agent.api import AgentFindingViewSet
from apps.deposits.api import DepositViewSet
from apps.documents.api import DepositDocumentViewSet
from apps.institutions.api import InstitutionViewSet
from apps.notifications.api import NotificationViewSet

router = DefaultRouter()
router.register(r"institutions", InstitutionViewSet, basename="institution")
router.register(r"deposits", DepositViewSet, basename="deposit")
router.register(r"documents", DepositDocumentViewSet, basename="document")
router.register(r"notifications", NotificationViewSet, basename="notification")
router.register(r"agent/findings", AgentFindingViewSet, basename="agent-finding")

urlpatterns = [
    path("", include(router.urls)),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]