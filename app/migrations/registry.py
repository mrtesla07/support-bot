from __future__ import annotations

from .manager import Migration
from .security import sanitize_existing_display_names

MIGRATIONS: tuple[Migration, ...] = (
    Migration(
        version=1,
        description="Санация сохранённых отображаемых имён и переименование существующих тем форума.",
        callback=sanitize_existing_display_names,
    ),
)
