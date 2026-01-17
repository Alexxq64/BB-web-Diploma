# warehouse_app/management/commands/init_test_data_full.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from warehouse_app.models import Nomenclature, ProductBatch

class Command(BaseCommand):
    help = 'Полный цикл тестовых данных: номенклатура → партии → приёмка → склад'

    def handle(self, *args, **options):
        self.stdout.write("Проверка существующих данных...")
        existing = check_existing_data()
        action = prompt_user_action(existing)

        if action == 'nothing':
            self.stdout.write("Данные не изменены.")
            return

        # 1️⃣ Создаём номенклатуру
        nomenclature_items = create_test_nomenclature(action)

        # 2️⃣ Создаём партии для каждой номенклатуры
        batches = create_test_batches(nomenclature_items, action)

        # 3️⃣ Принимаем партии (через метод receive)
        receive_batches(batches)

        self.stdout.write(self.style.SUCCESS("Инициализация полного цикла тестовых данных завершена."))


# -----------------------------
# Процедуры
# -----------------------------

def check_existing_data():
    """
    Проверяет, есть ли записи в Nomenclature и ProductBatch.
    """
    nomenclature_count = Nomenclature.objects.count()
    batch_count = ProductBatch.objects.count()
    return {'nomenclature': nomenclature_count, 'batches': batch_count}


def prompt_user_action(existing):
    """
    Спрашивает пользователя, что делать, если записи уже есть.
    """
    if existing['nomenclature'] == 0 and existing['batches'] == 0:
        return 'overwrite'

    print(f"В базе уже есть данные:")
    print(f" - Nomenclature: {existing['nomenclature']} записей")
    print(f" - ProductBatch: {existing['batches']} записей")
    print("Выберите действие:")
    print("1 — Переписать данные тестовыми")
    print("2 — Дополнить тестовыми (только отсутствующие)")
    print("3 — Ничего не делать")

    while True:
        choice = input("Введите 1, 2 или 3: ").strip()
        if choice == '1':
            return 'overwrite'
        elif choice == '2':
            return 'append'
        elif choice == '3':
            return 'nothing'
        else:
            print("Неверный ввод, попробуйте ещё раз.")


def create_test_nomenclature(action):
    """
    Создаёт тестовые записи номенклатуры.
    """
    if action == 'overwrite':
        Nomenclature.objects.all().delete()

    test_items = [
        {'code': 'NOM001', 'name': 'Продукт А', 'unit': 'кг', 'shelf_life_days': 30},
        {'code': 'NOM002', 'name': 'Продукт Б', 'unit': 'кг', 'shelf_life_days': 60},
        {'code': 'NOM003', 'name': 'Продукт В', 'unit': 'л', 'shelf_life_days': 90},
    ]

    created_items = []
    for item in test_items:
        obj, created = Nomenclature.objects.get_or_create(
            code=item['code'],
            defaults={
                'name': item['name'],
                'unit': item['unit'],
                'shelf_life_days': item['shelf_life_days']
            }
        )
        created_items.append(obj)
    return created_items


from django.utils import timezone

def create_test_batches(nomenclature_items, action):
    """
    Создаёт по одной партии для каждой номенклатуры.
    """
    from warehouse_app.models import ProductBatch

    batches = []
    for nom in nomenclature_items:
        # Проверяем, есть ли уже партия для этой номенклатуры (если append)
        if action == 'append' and ProductBatch.objects.filter(nomenclature=nom).exists():
            batch = ProductBatch.objects.filter(nomenclature=nom).first()
            batches.append(batch)
            continue

        prod_date = timezone.now().date()
        exp_date = prod_date + timezone.timedelta(days=nom.shelf_life_days)

        batch = ProductBatch.objects.create(
            nomenclature=nom,
            batch_number=f"TEST-{nom.code}-001",
            weight_kg=100,               # пример веса
            production_date=prod_date,
            reception_date=None,         # ещё не принята
            expiration_date=exp_date     # обязательно для NOT NULL
        )
        batches.append(batch)
    return batches


def receive_batches(batches):
    """
    Принимает все партии через метод receive() и обновляет склад.
    """
    for batch in batches:
        result = batch.receive(note="Тестовая приёмка при инициализации")
        print(result)
