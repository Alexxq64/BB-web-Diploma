from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group

class Command(BaseCommand):
    help = 'Создаёт тестовых пользователей и назначает их в группы'

    def handle(self, *args, **kwargs):
        users = [
            {"username": "admin", "password": "admin123", "group": "Admin"},
            {"username": "operator", "password": "operator123", "group": "Operator"},
            {"username": "user", "password": "user123", "group": "User"},
        ]

        for u in users:
            user, created = User.objects.get_or_create(username=u["username"])
            if created:
                user.set_password(u["password"])
                user.save()
                self.stdout.write(self.style.SUCCESS(f'Пользователь {u["username"]} создан'))
            else:
                self.stdout.write(self.style.WARNING(f'Пользователь {u["username"]} уже существует'))

            # Назначаем в группу
            group = Group.objects.get(name=u["group"])
            user.groups.add(group)
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Пользователь {u["username"]} добавлен в группу {u["group"]}'))
