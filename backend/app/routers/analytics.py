from __future__ import annotations

from typing import Literal

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth.security import require_manager_or_admin
from app.config import DATA_FILE
from app.ml.calendar_features import add_holiday_features
from app.ml.data import MODALITY_LABELS, Modality, add_calendar_columns, load_visits, select_modality

router = APIRouter(
    prefix="/analytics",
    tags=["Аналітика"],
    dependencies=[Depends(require_manager_or_admin)],
)

WEEKDAY_NAMES = {0: "Понеділок", 1: "Вівторок", 2: "Середа", 3: "Четвер", 4: "П'ятниця", 5: "Субота", 6: "Неділя"}
MONTH_NAMES = {
    1: "Січень", 2: "Лютий", 3: "Березень", 4: "Квітень", 5: "Травень", 6: "Червень",
    7: "Липень", 8: "Серпень", 9: "Вересень", 10: "Жовтень", 11: "Листопад", 12: "Грудень",
}


def _series(modality: Modality):
    try:
        return select_modality(load_visits(DATA_FILE), modality)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/modalities-summary", summary="Коротка статистика за типами обстежень")
def modalities_summary():
    df = load_visits(DATA_FILE)
    result = []
    for modality in ["mri", "ct", "xray"]:
        result.append({
            "modality": modality,
            "label": MODALITY_LABELS[modality],
            "total": int(df[modality].sum()),
            "daily_average": round(float(df[modality].mean()), 2),
            "latest": int(df[modality].iloc[-1]),
        })
    result.append({
        "modality": "all",
        "label": MODALITY_LABELS["all"],
        "total": int(df["total"].sum()),
        "daily_average": round(float(df["total"].mean()), 2),
        "latest": int(df["total"].iloc[-1]),
    })
    return result


@router.get("/summary", summary="Загальна статистика")
def summary(modality: Modality = "all"):
    df = _series(modality)
    if df.empty:
        raise HTTPException(status_code=404, detail="Дані відсутні.")
    end_date = df["date"].max()
    last_7 = df[df["date"] >= end_date - np.timedelta64(6, "D")]
    last_30 = df[df["date"] >= end_date - np.timedelta64(29, "D")]
    return {
        "modality": modality,
        "modality_label": MODALITY_LABELS[modality],
        "start_date": df["date"].min().date().isoformat(),
        "end_date": end_date.date().isoformat(),
        "days": int(len(df)),
        "total_visits": int(df["patients"].sum()),
        "daily_average": round(float(df["patients"].mean()), 2),
        "median": round(float(df["patients"].median()), 2),
        "minimum": int(df["patients"].min()),
        "maximum": int(df["patients"].max()),
        "std_dev": round(float(df["patients"].std()), 2),
        "latest_7_day_average": round(float(last_7["patients"].mean()), 2),
        "latest_30_day_average": round(float(last_30["patients"].mean()), 2),
    }


@router.get("/daily", summary="Щоденні значення")
def daily(modality: Modality = "all"):
    df = _series(modality)
    return [{"date": row.date.date().isoformat(), "patients": int(row.patients)} for row in df.itertuples()]


@router.get("/monthly", summary="Статистика за місяцями")
def monthly(modality: Modality = "all"):
    df = _series(modality)
    df["month"] = df["date"].dt.to_period("M").astype(str)
    grouped = df.groupby("month")["patients"].agg(["sum", "mean", "max", "min"]).reset_index()
    return [
        {"month": row.month, "total": int(row.sum), "average": round(float(row.mean), 2), "maximum": int(row.max), "minimum": int(row.min)}
        for row in grouped.itertuples(index=False)
    ]


@router.get("/weekdays", summary="Середнє навантаження за днями тижня")
def weekdays(modality: Modality = "all"):
    df = add_calendar_columns(_series(modality))
    grouped = df.groupby("day_of_week")["patients"].mean().reset_index().sort_values("day_of_week")
    return [
        {"day": WEEKDAY_NAMES[int(row.day_of_week)], "day_number": int(row.day_of_week), "average_patients": round(float(row.patients), 2)}
        for row in grouped.itertuples(index=False)
    ]


@router.get("/trends", summary="Тренди та ковзні середні")
def trends(modality: Modality = "all", days: int = Query(default=180, ge=30, le=3650)):
    df = _series(modality).copy().sort_values("date")
    if df.empty:
        raise HTTPException(status_code=404, detail="Дані відсутні.")

    indexed = df.set_index("date")
    indexed["rolling_7"] = indexed["patients"].rolling("7D", min_periods=1).mean()
    indexed["rolling_30"] = indexed["patients"].rolling("30D", min_periods=1).mean()
    df = indexed.reset_index()

    end_date = df["date"].max()
    recent = df[(df["date"] > end_date - np.timedelta64(30, "D")) & (df["date"] <= end_date)]
    previous = df[(df["date"] > end_date - np.timedelta64(60, "D")) & (df["date"] <= end_date - np.timedelta64(30, "D"))]
    recent_30 = float(recent["patients"].mean()) if not recent.empty else float(df["patients"].mean())
    previous_30 = float(previous["patients"].mean()) if not previous.empty else recent_30
    change_percent = 0.0 if previous_30 == 0 else ((recent_30 - previous_30) / previous_30) * 100
    if change_percent > 3:
        direction, direction_label = "increasing", "Зростання"
    elif change_percent < -3:
        direction, direction_label = "decreasing", "Зниження"
    else:
        direction, direction_label = "stable", "Стабільно"

    window_start = end_date - np.timedelta64(days - 1, "D")
    view = df[df["date"] >= window_start]
    latest_7 = df[df["date"] >= end_date - np.timedelta64(6, "D")]
    return {
        "modality": modality,
        "window_days": int(days),
        "direction": direction,
        "direction_label": direction_label,
        "change_percent": round(change_percent, 2),
        "latest_7_day_average": round(float(latest_7["patients"].mean()), 2),
        "latest_30_day_average": round(recent_30, 2),
        "points": [
            {"date": row.date.date().isoformat(), "patients": int(row.patients), "rolling_7": round(float(row.rolling_7), 2), "rolling_30": round(float(row.rolling_30), 2)}
            for row in view.itertuples()
        ],
    }


@router.get("/seasonality", summary="Сезонність за календарними місяцями")
def seasonality(modality: Modality = "all"):
    df = add_calendar_columns(_series(modality))
    grouped = df.groupby("month")["patients"].agg(["mean", "count"]).reset_index()
    return [
        {"month_number": int(row.month), "month": MONTH_NAMES[int(row.month)], "average_patients": round(float(row.mean), 2), "observations": int(row.count)}
        for row in grouped.itertuples(index=False)
    ]


@router.get("/anomalies", summary="Аномально високі та низькі дні")
def anomalies(modality: Modality = "all", threshold: float = Query(default=2.5, ge=1.5, le=5.0)):
    df = add_calendar_columns(_series(modality)).copy()
    stats = df.groupby("day_of_week")["patients"].agg(["mean", "std"]).rename(columns={"mean": "weekday_mean", "std": "weekday_std"})
    df = df.join(stats, on="day_of_week")
    df["weekday_std"] = df["weekday_std"].replace(0, np.nan)
    df["z_score"] = (df["patients"] - df["weekday_mean"]) / df["weekday_std"]
    detected = df[df["z_score"].abs() >= threshold].copy()
    detected["absolute_z"] = detected["z_score"].abs()
    detected = detected.sort_values("absolute_z", ascending=False)
    return {
        "threshold": threshold,
        "count": int(len(detected)),
        "anomalies": [
            {
                "date": row.date.date().isoformat(), "patients": int(row.patients),
                "day": WEEKDAY_NAMES[int(row.day_of_week)], "expected_weekday_average": round(float(row.weekday_mean), 2),
                "z_score": round(float(row.z_score), 2), "type": "high" if row.z_score > 0 else "low",
                "type_label": "Високе" if row.z_score > 0 else "Низьке",
            }
            for row in detected.itertuples()
        ],
    }


@router.get("/holiday-impact", summary="Вплив свят і сусідніх днів")
def holiday_impact(modality: Modality = "all"):
    df = add_holiday_features(_series(modality)).copy()
    regular = df[(df["is_holiday"] == 0) & (df["day_before_holiday"] == 0) & (df["day_after_holiday"] == 0)]
    holiday = df[df["is_holiday"] == 1]
    before = df[df["day_before_holiday"] == 1]
    after = df[df["day_after_holiday"] == 1]

    def stats(frame):
        return {"observations": int(len(frame)), "average_patients": round(float(frame["patients"].mean()), 2) if len(frame) else None}

    return {
        "modality": modality,
        "regular_days": stats(regular),
        "holidays": stats(holiday),
        "day_before_holiday": stats(before),
        "day_after_holiday": stats(after),
    }
