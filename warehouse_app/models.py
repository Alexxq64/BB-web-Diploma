from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

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


# Партия продукции
class ProductBatch(models.Model):
    nomenclature = models.ForeignKey(
        Nomenclature, on_delete=models.CASCADE, related_name="batches"
    )
    batch_number = models.CharField("Номер партии", max_length=100)
    weight_kg = models.FloatField("Вес партии (кг)")
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
            quantity=self.weight_kg,
            note=note
        )

        # обновляем склад
        warehouse, created = Warehouse.objects.get_or_create(
            nomenclature=self.nomenclature,
            defaults={'current_weight_kg': 0}
        )
        warehouse.current_weight_kg += self.weight_kg
        warehouse.save()

        # помечаем партию как принятую
        self.reception_date = timezone.now()
        self.save(update_fields=['reception_date'])

        return f"Партия {self.batch_number} принята, склад обновлён"


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
    quantity = models.FloatField("Количество (кг)")
    reason = models.CharField("Причина списания", max_length=200, blank=True, null=True)
    document = models.CharField("Документ", max_length=100, blank=True, null=True)
    note = models.CharField("Примечание", max_length=500, blank=True, null=True)

    def __str__(self):
        type_display = self.get_operation_type_display()
        batch_number = self.batch.batch_number if self.batch else "—"
        return f"{type_display} | {batch_number} | {self.quantity} кг"

    
class Warehouse(models.Model):
    nomenclature = models.OneToOneField(
        Nomenclature,
        on_delete=models.CASCADE,
        related_name="warehouse_item"
    )
    current_weight_kg = models.FloatField("Текущий остаток (кг)", default=0)

    class Meta:
        verbose_name = _("Склад")
        verbose_name_plural = _("Склад")

    def __str__(self):
        return f"{self.nomenclature.name} | {self.current_weight_kg} кг"

