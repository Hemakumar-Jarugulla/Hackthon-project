"""Management command to verify database connectivity, engine, and registered apps."""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from common.db import get_database_status


class Command(BaseCommand):
    help = 'Verify active database connection, engine settings, and registered Django apps.'

    def handle(self, *args, **options):
        status = get_database_status()
        self.stdout.write(f"Engine:           {status['engine']}")
        self.stdout.write(f"Database:         {status['database']}")
        self.stdout.write(f"Host:             {status['host']}:{status['port'] or 'local'}")
        self.stdout.write(f"Registered apps:  {len(settings.LOCAL_APPS)} local apps")

        if not status['connected']:
            raise CommandError(
                f"Database connection failed: {status['error']}\n"
                "Verify DB_ENGINE, DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, and DB_PORT in backend/.env."
            )

        self.stdout.write(f"Server version:   {status['server_version']}")
        self.stdout.write(self.style.SUCCESS('Database connection verified successfully.'))

