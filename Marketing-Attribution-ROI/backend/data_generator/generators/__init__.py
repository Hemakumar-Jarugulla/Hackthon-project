"""Deterministic synthetic dataset generators."""

from data_generator.generators.marketing_generator import (
    DEFAULT_SEED,
    MODE_PRESETS,
    generate_marketing_dataset,
    reset_marketing_dataset,
)

__all__ = [
    'DEFAULT_SEED',
    'MODE_PRESETS',
    'generate_marketing_dataset',
    'reset_marketing_dataset',
]
