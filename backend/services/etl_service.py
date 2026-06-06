"""
ETL service.
Wraps database seeding / ETL logic for startup use.
"""
from __future__ import annotations

from typing import Callable

from scripts.etl_seeder import run_etl


def ensure_database_seeded(prov_count: int, metrics_count: int) -> None:
    """Run ETL seeding if the database appears empty."""
    if prov_count == 0 or metrics_count == 0:
        print("[INFO] Database tables are empty. Seeding database...")
        run_etl()
    else:
        print(
            f"[INFO] Database populated with {prov_count} provinces and {metrics_count} records."
        )
