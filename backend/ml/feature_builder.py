"""
Feature builder module.
Constructs and updates forecast feature rows from history.
"""
from __future__ import annotations

from typing import Any

import pandas as pd


class ForecastFeatureBuilder:
    @staticmethod
    def build_next_row(
        history: pd.DataFrame, next_date: pd.Timestamp
    ) -> dict[str, Any]:
        last_row = history.iloc[-1].to_dict()
        last_row["date"] = next_date
        last_row["month"] = next_date.month
        last_row["day"] = next_date.day
        last_row["dekad_id"] = next_date.day // 10 + 1
        last_row["year_extracted"] = next_date.year
        last_row["month_extracted"] = next_date.month
        last_row["quarter_extracted"] = (next_date.month - 1) // 3 + 1
        last_row["semester_extracted"] = 1 if next_date.month <= 6 else 2
        last_row["dayofyear"] = next_date.dayofyear
        last_row["weekofyear"] = next_date.isocalendar()[1]
        return last_row
