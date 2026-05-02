"""
Model Performans Raporlama API'si
===================================
ML modellerin tahmin / gerçekleşen sapmalarını ve doğruluk skorlarını
saklayan ModelPerformanceLog tablosu için CRUD + agregat raporlama.

Mehmet Sait Tayşi — Cycle 6 Görevi (shiftSession): Model Performansını
İzleme ve Raporlama Altyapısı

Endpoint'ler:
- GET /              listele (model_name + limit filtre)
- POST /             yeni log (auth)
- PATCH /{id}        gerçek değer + accuracy doldur (auth)
- GET /summary/{m}   model bazlı agregat özet
- GET /timeseries/{m} günlük accuracy zaman serisi
- GET /compare       birden fazla modeli karşılaştır
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import verify_api_key
from app.models.models import ModelPerformanceLog
from app.schemas.schemas import (
    ModelPerformanceCompareItem,
    ModelPerformanceLogCreate,
    ModelPerformanceLogResponse,
    ModelPerformanceLogUpdate,
    ModelPerformanceSummary,
    ModelPerformanceTimeseriesPoint,
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


@router.patch(
    "/{log_id}",
    response_model=ModelPerformanceLogResponse,
    dependencies=[Depends(verify_api_key)],
    summary="Log'a gerçek değer + accuracy ekle",
    description="Tahmin sonradan gerçekleştiğinde `actual_data` ve `accuracy_score` alanlarını "
    "günceller. Tipik akış: önce POST ile log yaratılır, gerçek sonuç bilindiğinde bu PATCH "
    "ile doldurulur.",
)
def update_log(log_id: int, payload: ModelPerformanceLogUpdate, db: Session = Depends(get_db)):
    log = db.query(ModelPerformanceLog).filter(ModelPerformanceLog.id == log_id).first()
    if log is None:
        raise HTTPException(status_code=404, detail=f"Log {log_id} bulunamadi")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(log, field, value)
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


@router.get(
    "/timeseries/{model_name}",
    response_model=list[ModelPerformanceTimeseriesPoint],
    summary="Günlük accuracy zaman serisi",
    description="Modelin son N gündeki günlük ortalama accuracy değerini döndürür. "
    "Trend takibi ve drift tespiti için kullanılır.",
)
def model_timeseries(
    model_name: str,
    days: int = Query(default=30, ge=1, le=365, description="Son kaç gün"),
    db: Session = Depends(get_db),
):
    since = datetime.now(UTC) - timedelta(days=days)
    # SQLite ve PostgreSQL'de date() farklı çalışıyor — func.date() ile tarih bazlı gruplama
    rows = (
        db.query(
            func.date(ModelPerformanceLog.logged_at).label("d"),
            func.avg(ModelPerformanceLog.accuracy_score).label("avg_acc"),
            func.count(ModelPerformanceLog.id).label("count"),
        )
        .filter(
            ModelPerformanceLog.model_name == model_name,
            ModelPerformanceLog.logged_at >= since,
        )
        .group_by(func.date(ModelPerformanceLog.logged_at))
        .order_by(func.date(ModelPerformanceLog.logged_at))
        .all()
    )
    return [
        ModelPerformanceTimeseriesPoint(
            date=str(r.d),
            avg_accuracy=float(r.avg_acc) if r.avg_acc is not None else None,
            count=r.count,
        )
        for r in rows
    ]


@router.get(
    "/compare",
    response_model=list[ModelPerformanceCompareItem],
    summary="Birden fazla modeli karşılaştır",
    description="Virgülle ayrılmış model isimleri için yan-yana metrikler (toplam tahmin, "
    "ortalama / min / max accuracy, son log zamanı). Örnek: `?models=irrigation_rf,plant_disease_cnn`",
)
def compare_models(
    models: str = Query(..., description="Virgülle ayrılmış model isimleri"),
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    model_names = [m.strip() for m in models.split(",") if m.strip()]
    if not model_names:
        raise HTTPException(status_code=422, detail="En az bir model adi gerekli")

    since = datetime.now(UTC) - timedelta(days=days)
    results: list[ModelPerformanceCompareItem] = []
    for name in model_names:
        row = (
            db.query(
                func.count(ModelPerformanceLog.id).label("total"),
                func.avg(ModelPerformanceLog.accuracy_score).label("avg_acc"),
                func.min(ModelPerformanceLog.accuracy_score).label("min_acc"),
                func.max(ModelPerformanceLog.accuracy_score).label("max_acc"),
                func.max(ModelPerformanceLog.logged_at).label("last"),
            )
            .filter(
                ModelPerformanceLog.model_name == name,
                ModelPerformanceLog.logged_at >= since,
            )
            .one()
        )
        results.append(
            ModelPerformanceCompareItem(
                model_name=name,
                total_predictions=row.total or 0,
                avg_accuracy=float(row.avg_acc) if row.avg_acc is not None else None,
                min_accuracy=float(row.min_acc) if row.min_acc is not None else None,
                max_accuracy=float(row.max_acc) if row.max_acc is not None else None,
                last_logged=row.last,
            )
        )
    return results
