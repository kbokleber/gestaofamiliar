from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'users', views.UserViewSet, basename='user')
router.register(r'profiles', views.ProfileViewSet, basename='profile')
router.register(r'family-members', views.FamilyMemberViewSet, basename='family-member')
router.register(r'appointments', views.MedicalAppointmentViewSet, basename='appointment')
router.register(r'procedures', views.MedicalProcedureViewSet, basename='procedure')
router.register(r'medications', views.MedicationViewSet, basename='medication')
router.register(r'equipment', views.EquipmentViewSet, basename='equipment')
router.register(
    r'equipment-attachments',
    views.EquipmentAttachmentViewSet,
    basename='equipment-attachment',
)
router.register(r'maintenance-orders', views.MaintenanceOrderViewSet, basename='maintenance-order')
router.register(r'maintenance-images', views.MaintenanceImageViewSet, basename='maintenance-image')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/token/', obtain_auth_token, name='api_token_auth'),
    path('schema/', SpectacularAPIView.as_view(), name='api-schema'),
    path(
        'docs/',
        SpectacularSwaggerView.as_view(url_name='api-schema'),
        name='api-swagger',
    ),
    path(
        'redoc/',
        SpectacularRedocView.as_view(url_name='api-schema'),
        name='api-redoc',
    ),
]
