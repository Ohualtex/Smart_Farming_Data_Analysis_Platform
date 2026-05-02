"""
Model Performans Raporlama API'si
===================================
ML modellerin tahmin / gerçekleşen sapmalarını ve doğruluk skorlarını
saklayan ModelPerformanceLog tablosu için CRUD + agregat raporlama.

Mehmet Sait Tayşi — Cycle 6 Görevi (shiftSession): Model Performansını
İzleme ve Raporlama Altyapısı

Skeleton: log oluşturma, listeleme ve model bazlı özet endpoint'i.
Genişletmeler (Mehmet):
- Tarih aralığı filtresi
- Model performans karşılaştırma
- Drift detection (gelişmiş)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import verify_api_key
from app.models.models import ModelPerformanceLog
from app.schemas.schemas import (
    ModelPerformanceLogCreate,
    ModelPerformanceLogResponse,
    ModelPerformanceSummary,
)

router = APIRouter(prefix="/api/model-performance", tags=["Model Performansı"])


@router.get(
    "/",
    response_model=list[ModelPerformanceLogResponse],
    summary="Performans loglarını listele",
)
def list_logs(
    model_name: str | None = Query(default=None, description="Filtre: belirli bir model"),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    query = db.query(ModelPerformanceLog)
    if model_name:
        query = query.filter(ModelPerformanceLog.model_name == model_name)
    return query.order_by(ModelPerformanceLog.logged_at.desc()).limit(limit).all()


@router.post(
    "/",
    response_model=ModelPerformanceLogResponse,
    status_code=201,
    dependencies=[Depends(verify_api_key)],
    summary="Yeni performans logu kaydet",
)
def create_log(payload: ModelPerformanceLogCreate, db: Session = Depends(get_db)):
    log = ModelPerformanceLog(**payload.model_dump())
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.get(
    "/summary/{model_name}",
    response_model=ModelPerformanceSummary,
    summary="Model bazlı agregat performans özeti",
    description="Belirtilen model için toplam tahmin sayısı, ortalama doğruluk skoru ve son log zamanını döndürür.",
)
def model_summary(model_name: str, db: Session = Depends(get_db)):
    rows = (
        db.query(
            func.count(ModelPerformanceLog.id).label("total"),
            func.avg(ModelPerformanceLog.accuracy_score).label("avg_acc"),
            func.max(ModelPerformanceLog.logged_at).label("last"),
        )
        .filter(ModelPerformanceLog.model_name == model_name)
        .one()
    )
    if rows.total == 0:
        raise HTTPException(status_code=404, detail=f"'{model_name}' icin log bulunamadi")
    return ModelPerformanceSummary(
        model_name=model_name,
        total_predictions=rows.total,
        avg_accuracy=float(rows.avg_acc) if rows.avg_acc is not None else None,
        last_logged=rows.last,
    )
