from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create the explicitly local demo admin; preserve any existing account unchanged."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Demo credentials are only allowed with DEBUG=True. Use createsuperuser for deployments.")
        User = get_user_model()
        if User.objects.filter(username="admin").exists():
            self.stdout.write("An admin username already exists; its password and permissions were not changed.")
            return
        User.objects.create_superuser("admin", "admin@example.com", "DemoAdmin123!")
        self.stdout.write(self.style.SUCCESS("Local demo admin created: admin / DemoAdmin123! — change before any public deployment."))
