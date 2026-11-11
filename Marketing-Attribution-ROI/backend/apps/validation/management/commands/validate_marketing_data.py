"""Django management command executing the 11-rule validation framework from CLI."""

import json

from django.core.management.base import BaseCommand, CommandError

from apps.validation.services import run_validation_suite


class Command(BaseCommand):
    """Run all data validation and exception detection checks against the database."""

    help = 'Execute all 11 data quality & attribution integrity checks and output a validation report.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-sync-exceptions',
            action='store_true',
            help='Do not create DataException rows during validation.',
        )
        parser.add_argument(
            '--json',
            action='store_true',
            dest='output_json',
            help='Print full validation report in JSON format.',
        )
        parser.add_argument(
            '--strict',
            action='store_true',
            help='Exit with CommandError if any validation check has status Failed.',
        )

    def handle(self, *args, **options):
        report = run_validation_suite(
            triggered_by='CLI validate_marketing_data',
            sync_exceptions=not options['no_sync_exceptions'],
        )
        if options['output_json']:
            self.stdout.write(json.dumps(report, indent=2, default=str))
        else:
            self.stdout.write(
                f"Validation Run {report['run_id']} | Checked={report['total_records_checked']} "
                f"| Passed={report['passed_checks']} | Warnings={report['warnings']} "
                f"| Errors={report['errors']} | Invalid/Flagged={report['invalid_records']}"
            )
            for chk in report['checks']:
                self.stdout.write(
                    f"  [{chk['status']:<7}] {chk['check_code']} {chk['check_name']} -> {chk['details']}"
                )

        if options['strict'] and report['errors'] > 0:
            raise CommandError(
                f"Validation failed in strict mode with {report['errors']} error rule(s)."
            )

