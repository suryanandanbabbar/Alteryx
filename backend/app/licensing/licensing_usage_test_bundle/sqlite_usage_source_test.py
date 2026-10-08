"""Test-only SQLite usage source for licensing add-on validation.

This helper is intentionally outside the production licensing package.
It implements the existing UsageDataSource protocol without changing
production licensing architecture.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


class SQLiteUsageDataSource:
    def __init__(self, db_path: str | Path, table: str) -> None:
        if table not in {"volume_usage", "token_usage"}:
            raise ValueError("table must be volume_usage or token_usage")
        self.db_path = str(db_path)
        self.table = table

    def get_current_usage(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                f"SELECT current_usage FROM {self.table} WHERE id = 1"
            ).fetchone()

        if row is None:
            raise RuntimeError(f"No current usage row found in {self.table}")

        value = row[0]
        if type(value) is not int or value < 0:
            raise ValueError(f"Invalid usage value in {self.table}: {value!r}")

        return value
