from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.db.models import ProtectedError


# Справочник видов продукции
class Nomenclature(models.Model):
    code = models.CharField("Код продукции", max_length=50, unique=True)
    name = models.CharField("Наименование", max_length=200)
    unit = models.CharField("Единица измерения", max_length=20)
    shelf_life_days = models.PositiveIntegerField("Срок годности (дни)")

    class Meta:
        verbose_name = _("Номенклатура")
        verbose_name_plural = _("Номенклатура")

    def __str__(self):
        return f"{self.code} - {self.name}"
    
    def delete(self, *args, **kwargs):
        """
        Запрещает удаление номенклатуры, если она используется в системе.
        Проверяет наличие связанных записей в партиях, операциях и на складе.
        """
        # Проверяем наличие связанных записей в партиях
        if self.batches.exists():
            raise ProtectedError(
                f'Невозможно удалить номенклатуру "{self.name}" (код: {self.code}). '
                f'Существуют связанные партии продукции.',
                self
            )
        
        # Проверяем наличие связанных записей в операциях
        if self.operations.exists():
            raise ProtectedError(
                f'Невозможно удалить номенклатуру "{self.name}" (код: {self.code}). '
                f'Существуют связанные операции.',
                self
            )
        
        # Проверяем наличие записи на складе
        if hasattr(self, 'warehouse_item'):
            raise ProtectedError(
                f'Невозможно удалить номенклатуру "{self.name}" (код: {self.code}). '
                f'Существует запись на складе.',
                self
            )
        
        # Если связанных записей нет - удаляем
        super().delete(*args, **kwargs)


# Партия продукции
class ProductBatch(models.Model):
    nomenclature = models.ForeignKey(
        Nomenclature, 
        on_delete=models.PROTECT,  # Изменено с CASCADE на PROTECT
        related_name="batches"
    )
    batch_number = models.CharField("Номер партии", max_length=100)
    quantity = models.FloatField("Количество")
    production_date = models.DateField("Дата производства")
    reception_date = models.DateTimeField("Дата приёмки", default=None, blank=True, null=True)
    expiration_date = models.DateField("Срок годности")

    class Meta:
        verbose_name = _("Партия товара")
        verbose_name_plural = _("Партии товара")

    def __str__(self):
        return f"{self.nomenclature.code} - {self.nomenclature.name} | {self.batch_number}"

    def receive(self, note="Приёмка через интерфейс/скрипт"):
        """
        Метод приёмки партии: создаёт операцию и увеличивает склад.
        Не выполняется, если партия уже принята.
        """
        if self.reception_date is not None:
            return f"Партия {self.batch_number} уже принята {self.reception_date}"

        from warehouse_app.models import Operation, Warehouse  # импорт внутри, чтобы избежать циклов

        # создаём операцию приёмки
        Operation.objects.create(
            batch=self,
            operation_type="reception",
            quantity=self.quantity,
            note=note
        )

        # обновляем склад
        warehouse, created = Warehouse.objects.get_or_create(
            nomenclature=self.nomenclature,
            defaults={'current_quantity': 0}
        )
        warehouse.current_quantity += self.quantity
        warehouse.save()

        # создаём запись LiveBatch для новой активной партии
        LiveBatch.objects.create(
            product_batch=self,
            current_quantity=self.quantity)

        # помечаем партию как принятую
        self.reception_date = timezone.now()
        self.save(update_fields=['reception_date'])

        return f"Партия {self.batch_number} принята, склад обновлён"

    @property
    def status(self):
        """Возвращает статус партии на основе reception_date"""
        return "Принята" if self.reception_date else "Оформлена"


class Operation(models.Model):
    OPERATION_CHOICES = [
        ("reception", "Приёмка"),
        ("deduction", "Списание"),
    ]

    class Meta:
        verbose_name = "Операция"
        verbose_name_plural = "Операции"
        ordering = ['-operation_date']

    batch = models.ForeignKey(
        ProductBatch,
        on_delete=models.SET_NULL,
        related_name="operations",
        blank=True,
        null=True,
        verbose_name="Партия"
    )
    # Добавляем прямую связь с номенклатурой для списаний
    nomenclature = models.ForeignKey(
        Nomenclature,
        on_delete=models.PROTECT,  # Защищаем удаление номенклатуры
        related_name="operations",
        blank=True,
        null=True,
        verbose_name="Номенклатура"
    )
    operation_type = models.CharField(
        "Тип операции",
        max_length=50,
        choices=OPERATION_CHOICES,
        default="reception"
    )
    operation_date = models.DateTimeField(
        "Дата операции",
        default=timezone.now
    )
    quantity = models.FloatField("Количество")
    reason = models.CharField("Причина списания", max_length=200, blank=True, null=True)
    document = models.CharField("Документ", max_length=100, blank=True, null=True)
    note = models.CharField("Примечание", max_length=500, blank=True, null=True)

    def __str__(self):
        type_display = self.get_operation_type_display()
        batch_number = self.batch.batch_number if self.batch else "—"
        nomenclature_name = self.nomenclature.name if self.nomenclature else (self.batch.nomenclature.name if self.batch else "—")
        return f"{type_display} | {nomenclature_name} | {batch_number} | {self.quantity} кг"
    
    def save(self, *args, **kwargs):
        """Автоматически заполняем nomenclature для операций списания"""
        if self.operation_type == "deduction" and not self.nomenclature:
            raise ValueError("Для операций списания необходимо указать номенклатуру")
        super().save(*args, **kwargs)


class Warehouse(models.Model):
    nomenclature = models.OneToOneField(
        Nomenclature,
        on_delete=models.PROTECT,  # Изменено с CASCADE на PROTECT
        related_name="warehouse_item"
    )
    current_quantity = models.FloatField("Текущий остаток", default=0)

    class Meta:
        verbose_name = _("Склад")
        verbose_name_plural = _("Склад")

    def __str__(self):
        return f"{self.nomenclature.name} | {self.current_quantity} кг"

    
from django.core.validators import MinValueValidator
class LiveBatch(models.Model):
    """Оперативный индекс активных партий с ненулевым остатком"""
    product_batch = models.OneToOneField(
        ProductBatch, 
        on_delete=models.CASCADE,
        related_name="live_batch"
    )
    current_quantity = models.FloatField(
        "Текущий остаток", 
        default=0,
        validators=[MinValueValidator(0)]  # проверка на >= 0
    )
    
    class Meta:
        verbose_name = "Активная партия"
        verbose_name_plural = "Активные партии"
    
    def __str__(self):
        return f"{self.product_batch.batch_number} | {self.current_quantity} {self.product_batch.nomenclature.unit}"