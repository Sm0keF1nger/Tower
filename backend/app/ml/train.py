from __future__ import annotations

import json
from datetime import datetime, timezone

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import TimeSeriesSplit

from app.config import BACKTEST_FILE, DATA_FILE, METADATA_FILE, MODEL_DIR, MODEL_FILE
from app.ml.data import MODALITY_COLUMNS, MODALITY_LABELS, load_visits, select_modality
from app.ml.features import BASE_FEATURE_COLUMNS, FEATURE_COLUMNS, HOLIDAY_FEATURE_COLUMNS, model_frame

MODEL_NAMES = ["linear_regression", "random_forest", "gradient_boosting"]


def mape(y_true, y_pred) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mask = y_true != 0
    if not mask.any():
        return float("nan")
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


def evaluate(y_true, y_pred) -> dict:
    return {
        "mae": round(float(mean_absolute_error(y_true, y_pred)), 4),
        "rmse": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 4),
        "mape": round(mape(y_true, y_pred), 4),
        "r2": round(float(r2_score(y_true, y_pred)), 6),
    }


def _make_model(name: str):
    if name == "linear_regression":
        return LinearRegression()
    if name == "random_forest":
        return RandomForestRegressor(
            n_estimators=200,
            random_state=42,
            min_samples_leaf=2,
            n_jobs=-1,
        )
    if name == "gradient_boosting":
        return GradientBoostingRegressor(random_state=42)
    raise ValueError(f"Невідомий тип моделі: {name}")


def _cv_mae(frame, features: list[str], model_name: str, splits: int = 4) -> float:
    splitter = TimeSeriesSplit(n_splits=splits)
    fold_scores: list[float] = []
    X = frame[features]
    y = frame["patients"]
    for train_index, validation_index in splitter.split(X):
        model = _make_model(model_name)
        model.fit(X.iloc[train_index], y.iloc[train_index])
        prediction = model.predict(X.iloc[validation_index])
        fold_scores.append(float(mean_absolute_error(y.iloc[validation_index], prediction)))
    return float(np.mean(fold_scores))


def _variant_selection(train_df) -> dict:
    variants = {
        "with_holidays": FEATURE_COLUMNS,
        "without_holidays": BASE_FEATURE_COLUMNS,
    }
    cv_results: dict[str, dict[str, float]] = {}
    for variant, features in variants.items():
        cv_results[variant] = {
            name: round(_cv_mae(train_df, features, name), 4)
            for name in MODEL_NAMES
        }

    best_with = min(cv_results["with_holidays"], key=cv_results["with_holidays"].get)
    best_without = min(cv_results["without_holidays"], key=cv_results["without_holidays"].get)
    with_score = cv_results["with_holidays"][best_with]
    without_score = cv_results["without_holidays"][best_without]

    if with_score <= without_score:
        selected_variant = "with_holidays"
        selected_model = best_with
        selected_features = FEATURE_COLUMNS
    else:
        selected_variant = "without_holidays"
        selected_model = best_without
        selected_features = BASE_FEATURE_COLUMNS

    return {
        "cv_results": cv_results,
        "best_with_holidays": best_with,
        "best_without_holidays": best_without,
        "selected_variant": selected_variant,
        "selected_model": selected_model,
        "selected_features": list(selected_features),
    }


def _fit_and_evaluate(model_name: str, features: list[str], train_df, test_df) -> tuple[object, np.ndarray, dict]:
    model = _make_model(model_name)
    model.fit(train_df[features], train_df["patients"])
    prediction = model.predict(test_df[features])
    return model, prediction, evaluate(test_df["patients"], prediction)


def _train_one(data, modality: str) -> tuple[dict, dict, dict]:
    series = select_modality(data, modality)
    frame = model_frame(series)
    if len(frame) < 90:
        raise ValueError(
            f"Для {MODALITY_LABELS[modality]} недостатньо даних: після побудови ознак залишилося "
            f"{len(frame)} рядків. Рекомендовано щонайменше 90 повних щоденних записів."
        )

    split = int(len(frame) * 0.8)
    train_df = frame.iloc[:split].copy()
    test_df = frame.iloc[split:].copy()
    if len(train_df) < 50 or len(test_df) < 15:
        raise ValueError(f"Для {MODALITY_LABELS[modality]} недостатньо даних для надійного хронологічного тестування.")

    selection = _variant_selection(train_df)
    selected_features: list[str] = selection["selected_features"]
    selected_model_name: str = selection["selected_model"]
    uses_holidays = selection["selected_variant"] == "with_holidays"

    # Порівняння алгоритмів на фінальному відкладеному періоді для обраного набору ознак.
    metrics: dict[str, dict] = {
        "weekly_naive_baseline": evaluate(test_df["patients"], test_df["lag_7"].to_numpy())
    }
    test_predictions: dict[str, np.ndarray] = {}
    evaluation_models: dict[str, object] = {}
    for name in MODEL_NAMES:
        model, prediction, model_metrics = _fit_and_evaluate(name, selected_features, train_df, test_df)
        metrics[name] = model_metrics
        test_predictions[name] = prediction
        evaluation_models[name] = model

    selected_evaluation_model = evaluation_models[selected_model_name]
    selected_prediction = test_predictions[selected_model_name]
    selected_metrics = metrics[selected_model_name]

    # Окрема абляція: найкращий за CV алгоритм кожного варіанта оцінюємо на тому самому holdout-періоді.
    best_with_name: str = selection["best_with_holidays"]
    best_without_name: str = selection["best_without_holidays"]
    _, _, with_holiday_metrics = _fit_and_evaluate(best_with_name, FEATURE_COLUMNS, train_df, test_df)
    _, _, without_holiday_metrics = _fit_and_evaluate(best_without_name, BASE_FEATURE_COLUMNS, train_df, test_df)
    no_holiday_mae = without_holiday_metrics["mae"]
    holiday_mae = with_holiday_metrics["mae"]
    improvement = 0.0 if no_holiday_mae == 0 else ((no_holiday_mae - holiday_mae) / no_holiday_mae) * 100

    importance_result = permutation_importance(
        selected_evaluation_model,
        test_df[selected_features],
        test_df["patients"],
        scoring="neg_mean_absolute_error",
        n_repeats=8,
        random_state=42,
        n_jobs=-1,
    )
    feature_importance = sorted(
        [
            {"feature": feature, "importance": round(float(max(0.0, importance)), 4)}
            for feature, importance in zip(selected_features, importance_result.importances_mean)
        ],
        key=lambda item: item["importance"],
        reverse=True,
    )

    backtest = {
        "model_name": selected_model_name,
        "uses_holiday_features": uses_holidays,
        "test_start": test_df["date"].iloc[0].date().isoformat(),
        "test_end": test_df["date"].iloc[-1].date().isoformat(),
        "points": [
            {
                "date": current_date.date().isoformat(),
                "actual": int(actual),
                "predicted": round(float(max(0, predicted)), 2),
                "error": round(float(predicted - actual), 2),
            }
            for current_date, actual, predicted in zip(test_df["date"], test_df["patients"], selected_prediction)
        ],
    }

    production_model = _make_model(selected_model_name)
    production_model.fit(frame[selected_features], frame["patients"])
    artifact = {
        "model": production_model,
        "features": selected_features,
        "model_name": selected_model_name,
        "uses_holiday_features": uses_holidays,
    }

    metadata = {
        "label": MODALITY_LABELS[modality],
        "model_name": selected_model_name,
        "uses_holiday_features": uses_holidays,
        "selected_features": selected_features,
        "selection_method": "TimeSeriesSplit (4 фолди) на перших 80% + фінальний хронологічний holdout 20%",
        "records_used": int(len(frame)),
        "train_rows_for_evaluation": int(len(train_df)),
        "test_rows": int(len(test_df)),
        "test_start": test_df["date"].iloc[0].date().isoformat(),
        "test_end": test_df["date"].iloc[-1].date().isoformat(),
        "metrics": metrics,
        "selected_metrics": selected_metrics,
        "feature_importance": feature_importance,
        "cv_mae": round(float(selection["cv_results"][selection["selected_variant"]][selected_model_name]), 4),
        "holiday_comparison": {
            "selected_variant": selection["selected_variant"],
            "best_with_holidays_model_name": best_with_name,
            "best_without_holidays_model_name": best_without_name,
            "with_holidays": with_holiday_metrics,
            "without_holidays": without_holiday_metrics,
            "mae_improvement_percent": round(float(improvement), 2),
            "cv_mae_with_holidays": round(float(selection["cv_results"]["with_holidays"][best_with_name]), 4),
            "cv_mae_without_holidays": round(float(selection["cv_results"]["without_holidays"][best_without_name]), 4),
        },
    }
    return metadata, backtest, artifact


def train() -> dict:
    data = load_visits(DATA_FILE)
    if len(data) < 120:
        raise ValueError("Для навчання рекомендовано щонайменше 120 щоденних записів.")

    modality_metadata: dict[str, dict] = {}
    modality_backtests: dict[str, dict] = {}
    artifacts: dict[str, dict] = {}

    for modality in MODALITY_COLUMNS:
        metadata, backtest, artifact = _train_one(data, modality)
        modality_metadata[modality] = metadata
        modality_backtests[modality] = backtest
        artifacts[modality] = artifact

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "modalities": artifacts,
            "version": "0.4.0",
        },
        MODEL_FILE,
    )

    generated_at = datetime.now(timezone.utc).isoformat()
    BACKTEST_FILE.write_text(
        json.dumps({"generated_at": generated_at, "modalities": modality_backtests}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    metadata = {
        "version": "0.4.0",
        "trained_at": generated_at,
        "records_total": int(len(data)),
        "base_features": BASE_FEATURE_COLUMNS,
        "holiday_features": HOLIDAY_FEATURE_COLUMNS,
        "modalities": modality_metadata,
    }
    METADATA_FILE.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return metadata


if __name__ == "__main__":
    print(json.dumps(train(), ensure_ascii=False, indent=2))
