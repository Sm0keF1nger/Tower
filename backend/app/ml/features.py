from __future__ import annotations

import numpy as np
import pandas as pd

from app.ml.calendar_features import add_holiday_features

BASE_FEATURE_COLUMNS = [
    "day_of_week",
    "month",
    "week_of_year",
    "is_weekend",
    "day_of_year_sin",
    "day_of_year_cos",
    "lag_1",
    "lag_7",
    "lag_14",
    "rolling_7",
    "rolling_14",
    "rolling_30",
]
HOLIDAY_FEATURE_COLUMNS = [
    "is_holiday",
    "day_before_holiday",
    "day_after_holiday",
    "days_to_holiday",
    "days_since_holiday",
]
FEATURE_COLUMNS = BASE_FEATURE_COLUMNS + HOLIDAY_FEATURE_COLUMNS


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Створити leakage-safe часові ознаки для одного типу обстеження."""
    out = (
        df.copy()
        .sort_values("date")
        .drop_duplicates(subset=["date"], keep="last")
        .set_index("date")
        .asfreq("D")
        .rename_axis("date")
        .reset_index()
    )
    out["day_of_week"] = out["date"].dt.dayofweek
    out["month"] = out["date"].dt.month
    out["week_of_year"] = out["date"].dt.isocalendar().week.astype(int)
    out["is_weekend"] = out["day_of_week"].isin([5, 6]).astype(int)

    day_of_year = out["date"].dt.dayofyear
    out["day_of_year_sin"] = np.sin(2 * np.pi * day_of_year / 365.25)
    out["day_of_year_cos"] = np.cos(2 * np.pi * day_of_year / 365.25)
    out = add_holiday_features(out)

    out["lag_1"] = out["patients"].shift(1)
    out["lag_7"] = out["patients"].shift(7)
    out["lag_14"] = out["patients"].shift(14)
    out["rolling_7"] = out["patients"].shift(1).rolling(7).mean()
    out["rolling_14"] = out["patients"].shift(1).rolling(14).mean()
    out["rolling_30"] = out["patients"].shift(1).rolling(30).mean()
    return out


def model_frame(df: pd.DataFrame) -> pd.DataFrame:
    return build_features(df).dropna(subset=FEATURE_COLUMNS + ["patients"]).copy()
