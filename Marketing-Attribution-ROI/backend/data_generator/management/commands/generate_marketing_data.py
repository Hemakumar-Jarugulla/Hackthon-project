"""
Django management command to deterministically generate starter or full-scale
marketing datasets, inject isolated anomalies, run validation, and export bundles.
"""

from django.core.management.base import BaseCommand, CommandError

from apps.validation.services import run_validation_suite
from data_generator.exports.exporter import export_marketing_bundle
from data_generator.generators.marketing_generator import (
    DEFAULT_SEED,
    generate_marketing_dataset,
)
from data_generator.validators.reproducibility import compute_dataset_fingerprint


class Command(BaseCommand):
    """Generate deterministic marketing attribution datasets cleanly in starter or full mode."""

    help = 'Generate deterministic marketing data (--mode starter|full --seed 20261022).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--mode',
            choices=['starter', 'full'],
            default='starter',
            help='Dataset size preset: starter (fast dev/testing) or full (500/50k/200k/10k).',
        )
        parser.add_argument(
            '--seed',
            type=int,
            default=DEFAULT_SEED,
            help='Fixed PRNG seed for deterministic reproducibility (default: 20261022).',
        )
        parser.add_argument(
            '--no-reset',
            action='store_true',
            help='Skip wiping existing marketing tables before insertion.',
        )
        parser.add_argument(
            '--export',
            action='store_true',
            help='Export CSV, JSON, SQL, manifest, dictionary, and validation summary to exports/.',
        )
        parser.add_argument(
            '--export-dir',
            type=str,
            default='',
            help='Optional custom output directory for exported artifacts.',
        )
        parser.add_argument(
            '--with-attribution',
            action='store_true',
            help='Execute and persist a Position-Based AttributionRun after data generation.',
        )
        parser.add_argument(
            '--verify-reproducibility',
            action='store_true',
            help='Run generator twice with identical seed/mode and verify matching SHA-256 checksums.',
        )

    def handle(self, *args, **options):
        mode = options['mode']
        seed = options['seed']
        reset = not options['no_reset']

        summary = generate_marketing_dataset(
            mode=mode,
            seed=seed,
            reset=reset,
            with_attribution=options['with_attribution'],
        )
        fingerprint_a = compute_dataset_fingerprint()

        if options['verify_reproducibility']:
            generate_marketing_dataset(
                mode=mode,
                seed=seed,
                reset=True,
                with_attribution=options['with_attribution'],
            )
            fingerprint_b = compute_dataset_fingerprint()
            if (
                fingerprint_a['overall_checksum'] != fingerprint_b['overall_checksum']
                or fingerprint_a['row_counts'] != fingerprint_b['row_counts']
            ):
                raise CommandError(
                    'Reproducibility verification failed: generated checksums diverged across runs!'
                )
            self.stdout.write(
                f"Reproducibility PASSED: identical SHA-256 {fingerprint_a['overall_checksum']}"
            )

        validation_report = run_validation_suite(
            triggered_by=f'Generator ({mode}, seed={seed})',
            sync_exceptions=True,
        )

        self.stdout.write(
            f"Generated {mode} dataset (seed={seed}) | Counts={summary['counts']} "
            f"| Checksum={fingerprint_a['overall_checksum']} | Validation Errors={validation_report['errors']}"
        )

        if options['export']:
            exp_info = export_marketing_bundle(
                output_dir=options['export_dir'] or None,
                mode=mode,
                seed=seed,
                anomaly_manifest=summary['anomaly_manifest'],
                validation_report=validation_report,
            )
            self.stdout.write(
                f"Exported {exp_info['files_count']} artifacts to {exp_info['output_dir']}"
            )

