from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth.security import require_admin, require_manager_or_admin
from app.config import BACKTEST_FILE, METADATA_FILE
from app.ml.predict import forecast
from app.ml.train import train

router = APIRouter(prefix="/ml", tags=["Прогнозування"])


@router.post("/train", summary="Навчити моделі", dependencies=[Depends(require_admin)])
def train_model():
    try:
        return train()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/forecast", summary="Отримати прогноз", dependencies=[Depends(require_manager_or_admin)])
def get_forecast(days: int = Query(default=7, ge=1, le=90)):
    try:
        return {"days": days, "forecast": forecast(days)}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/performance", summary="Метрики навчених моделей", dependencies=[Depends(require_admin)])
def performance():
    if not METADATA_FILE.exists():
        raise HTTPException(status_code=404, detail="Метадані моделей не знайдено. Виконайте навчання.")
    return json.loads(METADATA_FILE.read_text(encoding="utf-8"))


@router.get("/backtest", summary="Результати хронологічного тестування", dependencies=[Depends(require_admin)])
def backtest():
    if not BACKTEST_FILE.exists():
        raise HTTPException(status_code=404, detail="Результати тестування не знайдено. Виконайте навчання моделей.")
    return json.loads(BACKTEST_FILE.read_text(encoding="utf-8"))
