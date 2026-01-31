from django.core.management.base import BaseCommand
from django.utils import timezone
from warehouse_app.models import Nomenclature, ProductBatch

class Command(BaseCommand):
    help = 'Создание тестовых данных: номенклатура → партии → приёмка'

    def handle(self, *args, **options):
        self.stdout.write("Создание тестовых данных...")
        
        # 1. Создаём номенклатуру
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
            self.stdout.write(f"  Создана номенклатура: {obj.code} - {obj.name}")
        
        # 2. Создаём партии
        batches = []
        for nom in created_items:
            prod_date = timezone.now().date()
            exp_date = prod_date + timezone.timedelta(days=nom.shelf_life_days)
            
            batch = ProductBatch.objects.create(
                nomenclature=nom,
                batch_number=f"TEST-{nom.code}-001",
                quantity=100.0,  
                production_date=prod_date,
                reception_date=None,
                expiration_date=exp_date
            )
            batches.append(batch)
            self.stdout.write(f"  Создана партия: {batch.batch_number} - {batch.quantity} {nom.unit}")
        
        # 3. Принимаем партии
        for batch in batches:
            result = batch.receive(note="Тестовая приёмка")
            self.stdout.write(f"  Принята партия: {batch.batch_number} - {result}")
        
        self.stdout.write(self.style.SUCCESS("Тестовые данные созданы успешно!"))