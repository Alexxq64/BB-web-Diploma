from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from warehouse_app.models import Nomenclature, ProductBatch, Operation
from django.contrib.contenttypes.models import ContentType

class Command(BaseCommand):
    help = 'Создаёт группы пользователей и назначает права'

    def handle(self, *args, **kwargs):
        # 1. Создаём группы
        groups = ['Admin', 'Operator', 'User']
        for group_name in groups:
            group, created = Group.objects.get_or_create(name=group_name)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Группа {group_name} создана'))
            else:
                self.stdout.write(self.style.WARNING(f'Группа {group_name} уже существует'))

        # 2. Назначаем права на модели
        # Получаем content_type для каждой модели
        nomenclature_ct = ContentType.objects.get_for_model(Nomenclature)
        batch_ct = ContentType.objects.get_for_model(ProductBatch)
        operation_ct = ContentType.objects.get_for_model(Operation)

        # Права для Admin — полный доступ
        admin_perms = Permission.objects.filter(content_type__in=[nomenclature_ct, batch_ct, operation_ct])
        Group.objects.get(name='Admin').permissions.set(admin_perms)

        # Права для Operator — просмотр и добавление номенклатуры и партий
        operator_perms = Permission.objects.filter(
            content_type__in=[nomenclature_ct, batch_ct],
            codename__in=['add_nomenclature', 'view_nomenclature', 'add_productbatch', 'view_productbatch']
        )
        Group.objects.get(name='Operator').permissions.set(operator_perms)

        # Права для User — только просмотр
        user_perms = Permission.objects.filter(
            content_type__in=[nomenclature_ct, batch_ct, operation_ct],
            codename__in=[
                'view_nomenclature', 'view_productbatch', 'view_operation'
            ]
        )
        Group.objects.get(name='User').permissions.set(user_perms)

        self.stdout.write(self.style.SUCCESS('Группы и права успешно созданы'))
