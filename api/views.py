from django.contrib.auth.models import User
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.models import Profile
from healthcare.models import (
    FamilyMember,
    MedicalAppointment,
    MedicalProcedure,
    Medication,
)
from maintenance.models import (
    Equipment,
    EquipmentAttachment,
    MaintenanceImage,
    MaintenanceOrder,
)

from .serializers import (
    EquipmentAttachmentSerializer,
    EquipmentSerializer,
    FamilyMemberSerializer,
    MaintenanceImageSerializer,
    MaintenanceOrderSerializer,
    MedicalAppointmentSerializer,
    MedicalProcedureSerializer,
    MedicationSerializer,
    ProfileSerializer,
    UserSerializer,
)

@extend_schema_view(
    list=extend_schema(summary='Listar membros da família'),
    retrieve=extend_schema(summary='Detalhe do membro'),
    create=extend_schema(summary='Criar membro'),
    update=extend_schema(summary='Atualizar membro'),
    partial_update=extend_schema(summary='Atualizar parcialmente membro'),
    destroy=extend_schema(summary='Excluir membro'),
)
class FamilyMemberViewSet(viewsets.ModelViewSet):
    queryset = FamilyMember.objects.all()
    serializer_class = FamilyMemberSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['gender', 'user', 'blood_type']
    search_fields = ['name', 'relationship', 'allergies']
    ordering_fields = ['name', 'birth_date', 'created_at']


@extend_schema_view(
    list=extend_schema(summary='Listar consultas'),
    retrieve=extend_schema(summary='Detalhe da consulta'),
    create=extend_schema(summary='Criar consulta'),
    update=extend_schema(summary='Atualizar consulta'),
    partial_update=extend_schema(summary='Atualizar parcialmente consulta'),
    destroy=extend_schema(summary='Excluir consulta'),
)
class MedicalAppointmentViewSet(viewsets.ModelViewSet):
    queryset = MedicalAppointment.objects.select_related('family_member')
    serializer_class = MedicalAppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['family_member', 'specialty']
    search_fields = ['doctor_name', 'specialty', 'reason', 'diagnosis']
    ordering_fields = ['appointment_date', 'created_at']


@extend_schema_view(
    list=extend_schema(summary='Listar procedimentos'),
    retrieve=extend_schema(summary='Detalhe do procedimento'),
    create=extend_schema(summary='Criar procedimento'),
    update=extend_schema(summary='Atualizar procedimento'),
    partial_update=extend_schema(summary='Atualizar parcialmente procedimento'),
    destroy=extend_schema(summary='Excluir procedimento'),
)
class MedicalProcedureViewSet(viewsets.ModelViewSet):
    queryset = MedicalProcedure.objects.select_related('family_member')
    serializer_class = MedicalProcedureSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['family_member']
    search_fields = ['procedure_name', 'doctor_name', 'location']
    ordering_fields = ['procedure_date', 'created_at']


@extend_schema_view(
    list=extend_schema(summary='Listar medicamentos'),
    retrieve=extend_schema(summary='Detalhe do medicamento'),
    create=extend_schema(summary='Criar medicamento'),
    update=extend_schema(summary='Atualizar medicamento'),
    partial_update=extend_schema(summary='Atualizar parcialmente medicamento'),
    destroy=extend_schema(summary='Excluir medicamento'),
)
class MedicationViewSet(viewsets.ModelViewSet):
    queryset = Medication.objects.select_related('family_member')
    serializer_class = MedicationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['family_member', 'frequency']
    search_fields = ['name', 'prescribed_by', 'instructions']
    ordering_fields = ['start_date', 'name', 'created_at']


@extend_schema_view(
    list=extend_schema(summary='Listar equipamentos'),
    retrieve=extend_schema(summary='Detalhe do equipamento'),
    create=extend_schema(summary='Criar equipamento'),
    update=extend_schema(summary='Atualizar equipamento'),
    partial_update=extend_schema(summary='Atualizar parcialmente equipamento'),
    destroy=extend_schema(summary='Excluir equipamento'),
)
class EquipmentViewSet(viewsets.ModelViewSet):
    queryset = Equipment.objects.select_related('owner').prefetch_related('attachments')
    serializer_class = EquipmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['type', 'owner', 'brand']
    search_fields = ['name', 'brand', 'model', 'serial_number']
    ordering_fields = ['name', 'created_at', 'purchase_date']


@extend_schema_view(
    list=extend_schema(summary='Listar anexos de equipamento'),
    retrieve=extend_schema(summary='Detalhe do anexo'),
    create=extend_schema(summary='Criar anexo'),
    update=extend_schema(summary='Atualizar anexo'),
    partial_update=extend_schema(summary='Atualizar parcialmente anexo'),
    destroy=extend_schema(summary='Excluir anexo'),
)
class EquipmentAttachmentViewSet(viewsets.ModelViewSet):
    queryset = EquipmentAttachment.objects.select_related('equipment', 'uploaded_by')
    serializer_class = EquipmentAttachmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['equipment']

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)


@extend_schema_view(
    list=extend_schema(summary='Listar ordens de manutenção'),
    retrieve=extend_schema(summary='Detalhe da ordem'),
    create=extend_schema(summary='Criar ordem'),
    update=extend_schema(summary='Atualizar ordem'),
    partial_update=extend_schema(summary='Atualizar parcialmente ordem'),
    destroy=extend_schema(summary='Excluir ordem'),
)
class MaintenanceOrderViewSet(viewsets.ModelViewSet):
    queryset = (
        MaintenanceOrder.objects
        .select_related('equipment', 'created_by')
        .prefetch_related('images')
    )
    serializer_class = MaintenanceOrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['status', 'priority', 'equipment', 'created_by']
    search_fields = ['title', 'description', 'service_provider', 'invoice_number']
    ordering_fields = ['completion_date', 'created_at', 'cost', 'priority']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


@extend_schema_view(
    list=extend_schema(summary='Listar imagens de manutenção'),
    retrieve=extend_schema(summary='Detalhe da imagem'),
    create=extend_schema(summary='Criar imagem'),
    update=extend_schema(summary='Atualizar imagem'),
    partial_update=extend_schema(summary='Atualizar parcialmente imagem'),
    destroy=extend_schema(summary='Excluir imagem'),
)
class MaintenanceImageViewSet(viewsets.ModelViewSet):
    queryset = MaintenanceImage.objects.select_related('order')
    serializer_class = MaintenanceImageSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['order']


@extend_schema_view(
    list=extend_schema(summary='Listar perfis'),
    retrieve=extend_schema(summary='Detalhe do perfil'),
    update=extend_schema(summary='Atualizar perfil'),
    partial_update=extend_schema(summary='Atualizar parcialmente perfil'),
)
class ProfileViewSet(viewsets.ModelViewSet):
    queryset = Profile.objects.select_related('user')
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'put', 'patch', 'head', 'options']

    @extend_schema(summary='Perfil do usuário autenticado')
    @action(detail=False, methods=['get'])
    def me(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        serializer = self.get_serializer(profile)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(summary='Listar usuários'),
    retrieve=extend_schema(summary='Detalhe do usuário'),
)
class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all().order_by('username')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ['username', 'first_name', 'last_name', 'email']
