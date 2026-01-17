from django.contrib import admin
from .models import Nomenclature, ProductBatch, Operation
from .models import Warehouse


@admin.register(Nomenclature)
class NomenclatureAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "unit", "shelf_life_days")
    search_fields = ("code", "name")


@admin.register(ProductBatch)
class ProductBatchAdmin(admin.ModelAdmin):
    list_display = ("batch_number", "nomenclature", "weight_kg", "production_date", "reception_date", "expiration_date")
    list_filter = ("nomenclature", "production_date", "expiration_date")
    search_fields = ("batch_number", "nomenclature__name")


@admin.register(Operation)
class OperationAdmin(admin.ModelAdmin):
    list_display = ("batch", "operation_type", "operation_date", "quantity", "note")
    list_filter = ("operation_type", "operation_date")
    search_fields = ("batch__batch_number", "batch__nomenclature__name")


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ("nomenclature", "current_weight_kg")
    search_fields = ("nomenclature__name",)
