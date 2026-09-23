from __future__ import annotations

from typing import Literal

import pandas as pd

MODALITY_COLUMNS = ["mri", "ct", "xray"]
REQUIRED_COLUMNS = {"date", *MODALITY_COLUMNS}
Modality = Literal["all", "mri", "ct", "xray"]
MODALITY_LABELS = {
    "all": "Усі обстеження",
    "mri": "МРТ",
    "ct": "КТ",
    "xray": "Рентген",
}


def load_visits(path) -> pd.DataFrame:
    """Завантажити та перевірити щоденні кількості МРТ, КТ і рентгену."""
    df = pd.read_csv(path)
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            "CSV повинен містити колонки: date, mri, ct, xray. "
            f"Відсутні: {', '.join(sorted(missing))}."
        )

    df = df[["date", *MODALITY_COLUMNS]].copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for column in MODALITY_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df = df.dropna(subset=["date", *MODALITY_COLUMNS])
    for column in MODALITY_COLUMNS:
        df[column] = df[column].round().astype(int)
        df = df[df[column] >= 0]

    df["date"] = df["date"].dt.normalize()
    df = (
        df.groupby("date", as_index=False)[MODALITY_COLUMNS]
        .sum()
        .sort_values("date")
        .reset_index(drop=True)
    )
    df["total"] = df[MODALITY_COLUMNS].sum(axis=1)
    return df


def select_modality(df: pd.DataFrame, modality: Modality) -> pd.DataFrame:
    column = "total" if modality == "all" else modality
    return df[["date", column]].rename(columns={column: "patients"}).copy()


def add_calendar_columns(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result["year"] = result["date"].dt.year
    result["month"] = result["date"].dt.month
    result["day_of_week"] = result["date"].dt.dayofweek
    result["week_of_year"] = result["date"].dt.isocalendar().week.astype(int)
    result["quarter"] = result["date"].dt.quarter
    result["is_weekend"] = result["day_of_week"].isin([5, 6]).astype(int)
    return result
