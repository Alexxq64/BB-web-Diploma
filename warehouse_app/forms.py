from django import forms
from .models import Nomenclature
from django.utils import timezone

class NomenclatureForm(forms.ModelForm):
    class Meta:
        model = Nomenclature
        fields = ['code', 'name', 'unit', 'shelf_life_days']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'unit': forms.TextInput(attrs={'class': 'form-control'}),
            'shelf_life_days': forms.NumberInput(attrs={'class': 'form-control'}),
        }

from .models import ProductBatch


from django import forms
from .models import ProductBatch

class ProductBatchForm(forms.ModelForm):
    shelf_life_days = forms.IntegerField(
        label="Срок годности (дни)",
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = ProductBatch
        fields = [
            'batch_number',
            'nomenclature',
            'weight_kg',
            'production_date',
        ]
        widgets = {
            'batch_number': forms.TextInput(attrs={'class': 'form-control'}),
            'nomenclature': forms.Select(attrs={'class': 'form-select'}),
            'weight_kg': forms.NumberInput(attrs={'class': 'form-control'}),
            'production_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def save(self, commit=True):
        batch = super().save(commit=False)
        days = self.cleaned_data['shelf_life_days']
        batch.expiration_date = batch.production_date + timezone.timedelta(days=days)
        if commit:
            batch.save()
        return batch
    

class WarehouseDeductionForm(forms.Form):
    quantity = forms.FloatField(
        label="Количество (кг)",
        min_value=0.01,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    reason = forms.CharField(
        label="Причина списания",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    document = forms.CharField(
        label="Документ",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    note = forms.CharField(
        label="Примечание",
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
    )
