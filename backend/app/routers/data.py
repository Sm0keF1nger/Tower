from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
import shutil

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.auth.security import CurrentUser, require_admin
from app.config import DATA_DIR, DATA_FILE, METADATA_FILE
from app.ml.data import MODALITY_COLUMNS, load_visits

router = APIRouter(prefix="/data", tags=["Дані"], dependencies=[Depends(require_admin)])

DATE_ALIASES = {"date", "day", "visit_date", "date_of_visit", "attendance_date", "дата", "день"}
MRI_ALIASES = {"mri", "mrt", "мрт", "magnetic_resonance", "magnetic_resonance_imaging"}
CT_ALIASES = {"ct", "kt", "кт", "computed_tomography", "computer_tomography"}
XRAY_ALIASES = {"xray", "x_ray", "рентген", "rentgen", "radiography", "xray_count"}
MODALITY_COLUMN_ALIASES = {"modality", "type", "exam_type", "service", "тип", "обстеження"}
PATIENT_ALIASES = {
    "patients", "patient_count", "patients_count", "amount", "count", "visitors", "visits",
    "number_of_patients", "кількість", "пацієнти", "кількість_пацієнтів",
}
MODALITY_VALUE_MAP = {
    "mri": "mri", "mrt": "mri", "мрт": "mri",
    "ct": "ct", "kt": "ct", "кт": "ct",
    "xray": "xray", "x_ray": "xray", "рентген": "xray", "rentgen": "xray",
}


def _normalize_column_name(value: object) -> str:
    return (
        str(value).strip().lower().replace("-", "_").replace(" ", "_").replace("/", "_")
    )


def _find_column(columns: list[str], aliases: set[str]) -> str | None:
    return next((column for column in columns if column in aliases), None)


def _read_uploaded_table(filename: str, content: bytes) -> pd.DataFrame:
    suffix = Path(filename).suffix.lower()
    stream = BytesIO(content)
    if suffix == ".csv":
        try:
            return pd.read_csv(stream)
        except UnicodeDecodeError:
            stream.seek(0)
            return pd.read_csv(stream, encoding="cp1251")
    if suffix == ".xlsx":
        return pd.read_excel(stream, engine="openpyxl")
    raise ValueError("Підтримуються лише файли .csv та .xlsx.")


def _prepare_wide(working: pd.DataFrame, date_column: str) -> pd.DataFrame | None:
    mri = _find_column(list(working.columns), MRI_ALIASES)
    ct = _find_column(list(working.columns), CT_ALIASES)
    xray = _find_column(list(working.columns), XRAY_ALIASES)
    if not all([mri, ct, xray]):
        return None
    return working[[date_column, mri, ct, xray]].rename(
        columns={date_column: "date", mri: "mri", ct: "ct", xray: "xray"}
    )


def _prepare_long(working: pd.DataFrame, date_column: str) -> pd.DataFrame | None:
    modality_column = _find_column(list(working.columns), MODALITY_COLUMN_ALIASES)
    patient_column = _find_column(list(working.columns), PATIENT_ALIASES)
    if modality_column is None or patient_column is None:
        return None

    long = working[[date_column, modality_column, patient_column]].rename(
        columns={date_column: "date", modality_column: "modality", patient_column: "patients"}
    )
    long["modality"] = long["modality"].map(lambda value: MODALITY_VALUE_MAP.get(_normalize_column_name(value)))
    long["patients"] = pd.to_numeric(long["patients"], errors="coerce")
    long["date"] = pd.to_datetime(long["date"], errors="coerce")
    long = long.dropna(subset=["date", "modality", "patients"])
    if long.empty:
        return None

    # У довгому форматі відсутній рядок не прирівнюємо до нуля автоматично:
    # кожна дата повинна явно містити МРТ, КТ і рентген (значення 0 дозволене).
    present_per_date = long.groupby("date")["modality"].nunique()
    incomplete_dates = present_per_date[present_per_date < len(MODALITY_COLUMNS)]
    if not incomplete_dates.empty:
        first_dates = ", ".join(value.date().isoformat() for value in incomplete_dates.index[:5])
        raise ValueError(
            "У довгому форматі кожна дата повинна містити окремі значення mri, ct і xray, "
            f"навіть якщо значення дорівнює 0. Неповні дати: {first_dates}."
        )

    pivoted = long.pivot_table(index="date", columns="modality", values="patients", aggfunc="sum")
    return pivoted.reset_index()[["date", *MODALITY_COLUMNS]]


def _prepare_upload(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    if raw.empty:
        raise ValueError("Завантажений файл порожній.")

    original_rows = len(raw)
    working = raw.copy()
    working.columns = [_normalize_column_name(column) for column in working.columns]
    date_column = _find_column(list(working.columns), DATE_ALIASES)
    if date_column is None:
        raise ValueError("Не вдалося знайти колонку з датою. Рекомендована назва: date.")

    prepared = _prepare_wide(working, date_column)
    input_format = "wide"
    if prepared is None:
        prepared = _prepare_long(working, date_column)
        input_format = "long"

    if prepared is None:
        patient_column = _find_column(list(working.columns), PATIENT_ALIASES)
        if patient_column is not None:
            raise ValueError(
                "Файл містить лише загальну кількість пацієнтів. Tower v4 не ділить її на МРТ, КТ і рентген штучно. "
                "Додайте колонки mri, ct, xray або використайте довгий формат: date, modality, patients."
            )
        raise ValueError(
            "Не вдалося визначити дані МРТ, КТ і рентгену. Використайте колонки date,mri,ct,xray "
            "або date,modality,patients."
        )

    prepared["date"] = pd.to_datetime(prepared["date"], errors="coerce")
    invalid_date_rows = int(prepared["date"].isna().sum())
    for column in MODALITY_COLUMNS:
        prepared[column] = pd.to_numeric(prepared[column], errors="coerce")

    invalid_count_rows = int(prepared[MODALITY_COLUMNS].isna().any(axis=1).sum())
    valid = prepared.dropna(subset=["date", *MODALITY_COLUMNS]).copy()
    negative_rows = int((valid[MODALITY_COLUMNS] < 0).any(axis=1).sum())
    valid = valid[(valid[MODALITY_COLUMNS] >= 0).all(axis=1)]
    for column in MODALITY_COLUMNS:
        valid[column] = valid[column].round().astype(int)
    valid["date"] = valid["date"].dt.normalize()

    duplicate_date_rows = int(valid.duplicated(subset=["date"], keep=False).sum())
    cleaned = (
        valid.groupby("date", as_index=False)[MODALITY_COLUMNS]
        .sum().sort_values("date").reset_index(drop=True)
    )
    if cleaned.empty:
        raise ValueError("У файлі не знайдено коректних записів.")

    full_range = pd.date_range(cleaned["date"].min(), cleaned["date"].max(), freq="D")
    recorded_dates = set(cleaned["date"])
    gap_days = int(sum(1 for value in full_range if value not in recorded_dates))

    report = {
        "input_format": input_format,
        "original_rows": int(original_rows),
        "saved_daily_rows": int(len(cleaned)),
        "invalid_date_rows": invalid_date_rows,
        "invalid_count_rows": invalid_count_rows,
        "negative_count_rows": negative_rows,
        "duplicate_date_rows": duplicate_date_rows,
        "calendar_gap_days": gap_days,
        "start_date": cleaned["date"].min().date().isoformat(),
        "end_date": cleaned["date"].max().date().isoformat(),
        "totals": {column: int(cleaned[column].sum()) for column in MODALITY_COLUMNS},
    }
    report["totals"]["total"] = int(sum(report["totals"].values()))
    return cleaned, report


def _model_status() -> tuple[str | None, bool]:
    if not METADATA_FILE.exists():
        return None, True
    try:
        import json
        metadata = json.loads(METADATA_FILE.read_text(encoding="utf-8"))
        trained_at = metadata.get("trained_at")
    except Exception:
        return None, True

    data_modified = datetime.fromtimestamp(DATA_FILE.stat().st_mtime, tz=timezone.utc)
    try:
        trained_dt = datetime.fromisoformat(trained_at) if trained_at else None
    except ValueError:
        trained_dt = None
    return trained_at, trained_dt is None or data_modified > trained_dt


@router.get("/info", summary="Інформація про набір даних")
def dataset_info():
    try:
        df = load_visits(DATA_FILE)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    if df.empty:
        raise HTTPException(status_code=404, detail="Дані про відвідування відсутні.")

    full_range = pd.date_range(df["date"].min(), df["date"].max(), freq="D")
    recorded_dates = set(df["date"].dt.normalize())
    gap_dates = [value for value in full_range if value not in recorded_dates]
    coverage = 100.0 * len(df) / len(full_range) if len(full_range) else 100.0
    trained_at, needs_retraining = _model_status()
    return {
        "filename": DATA_FILE.name,
        "rows": int(len(df)),
        "start_date": df["date"].min().date().isoformat(),
        "end_date": df["date"].max().date().isoformat(),
        "totals": {column: int(df[column].sum()) for column in [*MODALITY_COLUMNS, "total"]},
        "calendar_gap_days": int(len(gap_dates)),
        "calendar_coverage_percent": round(float(coverage), 2),
        "model_trained_at": trained_at,
        "model_needs_retraining": needs_retraining,
    }


@router.get("/preview", summary="Переглянути останні записи")
def dataset_preview(limit: int = 10):
    limit = max(1, min(limit, 50))
    df = load_visits(DATA_FILE).tail(limit)
    return [
        {
            "date": row.date.date().isoformat(),
            "mri": int(row.mri),
            "ct": int(row.ct),
            "xray": int(row.xray),
            "total": int(row.total),
        }
        for row in df.itertuples()
    ]


@router.post("/upload", summary="Завантажити новий набір даних")
async def upload_dataset(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Не вказано ім'я файлу.")
    try:
        content = await file.read()
        raw = _read_uploaded_table(file.filename, content)
        cleaned, report = _prepare_upload(raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Не вдалося прочитати файл: {exc}") from exc

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    backup_dir = DATA_DIR / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_file = None
    if DATA_FILE.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"clinic_visits_{timestamp}.csv"
        shutil.copy2(DATA_FILE, backup_file)

    cleaned.to_csv(DATA_FILE, index=False, date_format="%Y-%m-%d")
    return {
        "message": "Набір даних успішно завантажено та нормалізовано.",
        "source_filename": file.filename,
        "saved_as": DATA_FILE.name,
        "backup_created": backup_file.name if backup_file else None,
        "model_needs_retraining": True,
        "quality": report,
    }
