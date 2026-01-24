from django.contrib import admin
from django.db.models import ProtectedError
from django.contrib import messages
from .models import Nomenclature, ProductBatch, Operation, Warehouse


@admin.register(Nomenclature)
class NomenclatureAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "unit", "shelf_life_days")
    search_fields = ("code", "name")
    
    def delete_model(self, request, obj):
        """
        Переопределяем удаление для защиты целостности данных.
        """
        try:
            obj.delete()
            self.message_user(request, f'Номенклатура "{obj.name}" успешно удалена', messages.SUCCESS)
        except ProtectedError as e:
            self.message_user(request, str(e), messages.ERROR)
    
    def delete_queryset(self, request, queryset):
        """
        Переопределяем массовое удаление.
        """
        success_count = 0
        error_messages = []
        
        for obj in queryset:
            try:
                obj.delete()
                success_count += 1
            except ProtectedError as e:
                error_messages.append(str(e))
        
        if success_count:
            self.message_user(request, f'Успешно удалено номенклатур: {success_count}', messages.SUCCESS)
        
        if error_messages:
            for error in error_messages[:5]:  # Показываем первые 5 ошибок
                self.message_user(request, error, messages.ERROR)


@admin.register(ProductBatch)
class ProductBatchAdmin(admin.ModelAdmin):
    list_display = ("batch_number", "nomenclature", "quantity", "production_date", "reception_date", "expiration_date", "status_display")
    list_filter = ("nomenclature", "production_date", "expiration_date", "reception_date")
    search_fields = ("batch_number", "nomenclature__name")
    
    def status_display(self, obj):
        """Отображаем статус партии в админке"""
        return obj.status
    status_display.short_description = "Статус"


@admin.register(Operation)
class OperationAdmin(admin.ModelAdmin):
    list_display = ("operation_type_display", "nomenclature_display", "batch_display", "quantity", "operation_date", "document", "reason")
    list_filter = ("operation_type", "operation_date")
    search_fields = ("batch__batch_number", "nomenclature__name", "document")
    
    def operation_type_display(self, obj):
        """Отображаем тип операции"""
        return obj.get_operation_type_display()
    operation_type_display.short_description = "Тип операции"
    
    def nomenclature_display(self, obj):
        """Отображаем номенклатуру (для списаний)"""
        if obj.nomenclature:
            return obj.nomenclature.name
        elif obj.batch:
            return obj.batch.nomenclature.name
        return "—"
    nomenclature_display.short_description = "Номенклатура"
    
    def batch_display(self, obj):
        """Отображаем номер партии или прочерк для списаний"""
        return obj.batch.batch_number if obj.batch else "—"
    batch_display.short_description = "Партия"


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ("nomenclature", "current_quantity", "get_unit")
    search_fields = ("nomenclature__name", "nomenclature__code")
    
    def get_unit(self, obj):
        """Отображаем единицу измерения"""
        return obj.nomenclature.unit
    get_unit.short_description = "Ед. изм."


from .models import LiveBatch

@admin.register(LiveBatch)
class LiveBatchAdmin(admin.ModelAdmin):
    list_display = ('product_batch', 'current_quantity', 'nomenclature', 'batch_number', 'expiration_date')
    list_filter = ('product_batch__nomenclature',)
    search_fields = ('product_batch__batch_number', 'product_batch__nomenclature__name')
    
    # Вычисляемые поля для отображения
    def nomenclature(self, obj):
        return obj.product_batch.nomenclature
    nomenclature.short_description = "Номенклатура"
    
    def batch_number(self, obj):
        return obj.product_batch.batch_number
    batch_number.short_description = "Номер партии"
    
    def expiration_date(self, obj):
        return obj.product_batch.expiration_date
    expiration_date.short_description = "Срок годности"