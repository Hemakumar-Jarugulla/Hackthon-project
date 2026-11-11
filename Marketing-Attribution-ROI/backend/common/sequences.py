"""Concurrency-safe deterministic ID generator backed by row-level DB locking."""

import re

from django.apps import apps
from django.db import transaction


def _extract_existing_max_sequence(model_cls, scope_prefix: str, id_field: str = 'pk') -> int:
    """
    Find the highest numeric suffix currently stored for a given prefix so
    seeded records and generated records never collide.
    """
    pattern = re.compile(rf'^{re.escape(scope_prefix)}-(\d+)$')
    existing_ids = model_cls.objects.filter(
        **{f'{id_field}__startswith': f'{scope_prefix}-'}
    ).values_list(id_field, flat=True)
    max_seq = 0
    for val in existing_ids:
        match = pattern.match(str(val))
        if match:
            max_seq = max(max_seq, int(match.group(1)))
    return max_seq


def _allocate_sequence_range(
    *,
    scope_prefix: str,
    model_cls,
    count: int = 1,
    id_field: str = 'pk',
) -> int:
    """
    Atomically reserve a contiguous block of `count` ID sequence numbers under a row lock
    and return the first integer sequence number in the allocated block.
    """
    if count < 1:
        raise ValueError('count must be >= 1')
    IdSequence = apps.get_model('audit', 'IdSequence')
    with transaction.atomic():
        sequence_row, _ = IdSequence.objects.select_for_update().get_or_create(
            scope_key=scope_prefix,
            defaults={'last_value': 0},
        )
        existing_max = _extract_existing_max_sequence(
            model_cls, scope_prefix, id_field=id_field
        )
        start_val = max(sequence_row.last_value, existing_max) + 1
        sequence_row.last_value = start_val + count - 1
        sequence_row.save(update_fields=['last_value', 'updated_at'])
    return start_val


def generate_deterministic_id(
    *,
    prefix: str,
    model_cls,
    year: int = 2026,
    width: int = 6,
    separator: str = '-',
    id_field: str = 'pk',
) -> str:
    """
    Generate unique sequential IDs such as CMP-2026-000001 safely under concurrency.

    Acquires an exclusive row lock (`SELECT ... FOR UPDATE`) on `audit.IdSequence`
    inside an atomic transaction before incrementing the sequence value.
    """
    scope_prefix = f'{prefix}{separator}{year}'
    next_val = _allocate_sequence_range(
        scope_prefix=scope_prefix,
        model_cls=model_cls,
        count=1,
        id_field=id_field,
    )
    return f'{scope_prefix}-{next_val:0{width}d}'


def generate_deterministic_id_batch(
    *,
    prefix: str,
    model_cls,
    count: int,
    year: int = 2026,
    width: int = 6,
    separator: str = '-',
    id_field: str = 'pk',
) -> list[str]:
    """Reserve a batch of contiguous deterministic IDs safely under one row lock."""
    if count == 0:
        return []
    scope_prefix = f'{prefix}{separator}{year}'
    start_val = _allocate_sequence_range(
        scope_prefix=scope_prefix,
        model_cls=model_cls,
        count=count,
        id_field=id_field,
    )
    return [f'{scope_prefix}-{seq:0{width}d}' for seq in range(start_val, start_val + count)]


def generate_touchpoint_id(*, contact_id: str, model_cls, width: int = 6) -> str:
    """
    Generate contact-scoped deterministic touchpoint IDs:
    TOUCH-<contact-id>-000001 (e.g., TOUCH-CON-2026-000001-000001).
    """
    scope_prefix = f'TOUCH-{contact_id}'
    next_val = _allocate_sequence_range(
        scope_prefix=scope_prefix,
        model_cls=model_cls,
        count=1,
    )
    return f'{scope_prefix}-{next_val:0{width}d}'
