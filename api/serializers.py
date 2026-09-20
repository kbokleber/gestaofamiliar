from django.contrib.auth.models import User
from rest_framework import serializers

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


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']
        read_only_fields = fields


class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Profile
        fields = [
            'id', 'user', 'phone', 'address', 'city', 'state',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class FamilyMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = FamilyMember
        fields = [
            'id', 'user', 'name', 'photo', 'birth_date', 'gender',
            'relationship', 'blood_type', 'allergies', 'chronic_conditions',
            'emergency_contact', 'emergency_phone', 'notes',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class MedicalAppointmentSerializer(serializers.ModelSerializer):
    family_member_name = serializers.CharField(
        source='family_member.name', read_only=True
    )

    class Meta:
        model = MedicalAppointment
        fields = [
            'id', 'family_member', 'family_member_name', 'doctor_name',
            'specialty', 'appointment_date', 'location', 'reason',
            'diagnosis', 'prescription', 'next_appointment', 'notes',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class MedicalProcedureSerializer(serializers.ModelSerializer):
    family_member_name = serializers.CharField(
        source='family_member.name', read_only=True
    )

    class Meta:
        model = MedicalProcedure
        fields = [
            'id', 'family_member', 'family_member_name', 'procedure_name',
            'procedure_date', 'doctor_name', 'location', 'description',
            'results', 'follow_up_notes', 'next_procedure_date',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class MedicationSerializer(serializers.ModelSerializer):
    family_member_name = serializers.CharField(
        source='family_member.name', read_only=True
    )
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = Medication
        fields = [
            'id', 'family_member', 'family_member_name', 'name', 'dosage',
            'frequency', 'start_date', 'end_date', 'prescribed_by',
            'prescription_number', 'instructions', 'side_effects', 'notes',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'is_active', 'created_at', 'updated_at']


class EquipmentAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = EquipmentAttachment
        fields = [
            'id', 'equipment', 'file', 'description',
            'uploaded_at', 'uploaded_by',
        ]
        read_only_fields = ['id', 'uploaded_at', 'uploaded_by']


class EquipmentSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(
        source='owner.username', read_only=True, allow_null=True
    )
    attachments = EquipmentAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Equipment
        fields = [
            'id', 'name', 'type', 'brand', 'model', 'serial_number',
            'purchase_date', 'owner', 'owner_username', 'notes',
            'attachments', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class MaintenanceImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceImage
        fields = ['id', 'order', 'image', 'description', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']


class MaintenanceOrderSerializer(serializers.ModelSerializer):
    equipment_name = serializers.CharField(
        source='equipment.name', read_only=True
    )
    created_by_username = serializers.CharField(
        source='created_by.username', read_only=True
    )
    images = MaintenanceImageSerializer(many=True, read_only=True)

    class Meta:
        model = MaintenanceOrder
        fields = [
            'id', 'equipment', 'equipment_name', 'title', 'description',
            'status', 'priority', 'service_provider', 'completion_date',
            'cost', 'warranty_expiration', 'warranty_terms',
            'invoice_number', 'invoice_file', 'notes',
            'created_by', 'created_by_username', 'images',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'created_by', 'created_at', 'updated_at',
        ]
