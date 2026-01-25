from django import forms
from .models import Nomenclature
from django.utils import timezone
import json

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

from .models import ProductBatch, Nomenclature
from django.utils import timezone
import json

import json
from django import forms
from django.utils import timezone
from .models import ProductBatch, Nomenclature

class ProductBatchForm(forms.ModelForm):
    shelf_life_days = forms.IntegerField(
        label="Срок годности (дни)",
        min_value=0,        
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = ProductBatch
        fields = [
            'batch_number',
            'nomenclature',
            'quantity',
            'production_date',
        ]
        widgets = {
            'batch_number': forms.TextInput(attrs={'class': 'form-control'}),
            'nomenclature': forms.Select(attrs={'class': 'form-select', 'id': 'id_nomenclature'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'production_date': forms.DateInput(
                attrs={
                    'class': 'form-control', 
                    'type': 'date'
                },
                format='%Y-%m-%d'
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Заполняем shelf_life_days при редактировании
        if self.instance and self.instance.pk:
            if self.instance.production_date and self.instance.expiration_date:
                delta = self.instance.expiration_date - self.instance.production_date
                self.fields['shelf_life_days'].initial = delta.days
        
        # Сохраняем queryset для JavaScript
        if 'nomenclature' in self.fields:
            queryset = self.fields['nomenclature'].queryset
            
            # Создаем словари для units и стандартных сроков годности
            units_dict = {}
            shelf_life_dict = {}
            
            for item in queryset:
                item_id = str(item.id)
                units_dict[item_id] = item.unit
                # Используем поле standard_shelf_life_days из модели Nomenclature
                shelf_life_dict[item_id] = item.standard_shelf_life_days if hasattr(item, 'standard_shelf_life_days') else 0
            
            # Добавляем data-атрибуты к виджету
            self.fields['nomenclature'].widget.attrs['data-units'] = json.dumps(units_dict)
            self.fields['nomenclature'].widget.attrs['data-shelf-life'] = json.dumps(shelf_life_dict)
    
    def save(self, commit=True):
        batch = super().save(commit=False)
        days = self.cleaned_data['shelf_life_days']
        batch.expiration_date = batch.production_date + timezone.timedelta(days=days)
        if commit:
            batch.save()
        return batch

class WarehouseDeductionForm(forms.Form):
    # Убираем поле quantity
    reason = forms.CharField(
        label="Причина списания",
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Например: брак, порча, внутренние нужды'
        })
    )
    document = forms.CharField(
        label="Документ-основание",
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Номер акта, накладной, приказа'
        })
    )
    note = forms.CharField(
        label="Примечание",
        required=False,
        max_length=500,
        widget=forms.Textarea(attrs={
            'class': 'form-control', 
            'rows': 3,
            'placeholder': 'Дополнительная информация'
        })
    )