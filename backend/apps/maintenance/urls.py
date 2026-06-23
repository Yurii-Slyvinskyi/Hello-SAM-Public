from django.urls import path

from .views import RetellInboundCallView, VoiceMaintenanceRequestCreateView


urlpatterns = [
    path(
        "maintenance-requests/",
        VoiceMaintenanceRequestCreateView.as_view(),
        name="voice-maintenance-request-create",
    ),
    path(
        "retell/inbound-call/",
        RetellInboundCallView.as_view(),
        name="retell-inbound-call",
    ),
]
