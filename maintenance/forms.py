from django import forms
from .models import Equipment

class EquipmentForm(forms.ModelForm):
    attachment = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'}),
        label='Anexo'
    )
    attachment_description = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Descrição do anexo (opcional)'}),
        label='Descrição do Anexo'
    )

    class Meta:
        model = Equipment
        fields = ['name', 'type', 'brand', 'model', 'serial_number', 'purchase_date', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'type': forms.Select(attrs={'class': 'form-select'}),
            'brand': forms.TextInput(attrs={'class': 'form-control'}),
            'model': forms.TextInput(attrs={'class': 'form-control'}),
            'serial_number': forms.TextInput(attrs={'class': 'form-control'}),
            'purchase_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        } 