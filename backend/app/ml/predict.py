from __future__ import annotations

import joblib
import pandas as pd

from app.config import DATA_FILE, MODEL_FILE
from app.ml.calendar_features import holiday_name
from app.ml.data import MODALITY_COLUMNS, load_visits, select_modality
from app.ml.features import build_features


def _feature_row_for_next_day(history: pd.DataFrame) -> pd.DataFrame:
    next_date = history["date"].max() + pd.Timedelta(days=1)
    placeholder = pd.DataFrame({"date": [next_date], "patients": [float("nan")]})
    extended = pd.concat([history, placeholder], ignore_index=True)
    return build_features(extended).iloc[[-1]]


def forecast(days: int = 7) -> list[dict]:
    if days < 1 or days > 90:
        raise ValueError("Кількість днів прогнозу повинна бути від 1 до 90.")
    if not MODEL_FILE.exists():
        raise FileNotFoundError("Моделі не знайдено. Спочатку виконайте навчання.")

    artifact = joblib.load(MODEL_FILE)
    modality_artifacts = artifact["modalities"]
    data = load_visits(DATA_FILE)
    histories = {modality: select_modality(data, modality) for modality in MODALITY_COLUMNS}

    results: list[dict] = []
    for _ in range(days):
        point: dict[str, object] = {}
        predicted_values: dict[str, int] = {}
        target_date: pd.Timestamp | None = None

        for modality in MODALITY_COLUMNS:
            history = histories[modality]
            row = _feature_row_for_next_day(history)
            model_info = modality_artifacts[modality]
            features: list[str] = model_info["features"]
            if row[features].isna().any(axis=None):
                raise ValueError(
                    "Недостатньо безперервних історичних даних для прогнозу. "
                    "Перевірте пропущені календарні дні в розділі «Дані»."
                )

            predicted = max(0, float(model_info["model"].predict(row[features])[0]))
            predicted_int = int(round(predicted))
            target_date = row["date"].iloc[0]
            predicted_values[modality] = predicted_int
            histories[modality] = pd.concat(
                [history, pd.DataFrame({"date": [target_date], "patients": [predicted_int]})],
                ignore_index=True,
            )

        assert target_date is not None
        point["date"] = target_date.date().isoformat()
        point.update(predicted_values)
        point["total"] = int(sum(predicted_values.values()))
        point["calendar_event"] = holiday_name(target_date)
        results.append(point)

    return results
