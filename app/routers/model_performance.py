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

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import verify_api_key
from app.middleware.rate_limiter import STRICT_RATE, limiter
from app.models.models import ModelPerformanceLog, SystemAlert
from app.schemas.schemas import (
    ModelPerformanceCompareItem,
    ModelPerformanceDriftReport,
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
@limiter.limit(STRICT_RATE)
def create_log(request: Request, payload: ModelPerformanceLogCreate, db: Session = Depends(get_db)):
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
@limiter.limit(STRICT_RATE)
def update_log(request: Request, log_id: int, payload: ModelPerformanceLogUpdate, db: Session = Depends(get_db)):
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


@router.get(
    "/drift/{model_name}",
    response_model=ModelPerformanceDriftReport,
    summary="Model drift kontrolü",
    description="Son N gün accuracy ortalamasını önceki periyotla karşılaştırır. "
    "Belirlenen eşikten fazla düşüş varsa otomatik olarak `SystemAlert` (severity=medium) yaratır. "
    "İdeal sıklık: günde 1-2 kez (cron veya scheduler ile).",
)
def detect_drift(
    model_name: str,
    recent_days: int = Query(default=7, ge=1, le=90, description="Son periyot pencere"),
    baseline_days: int = Query(default=30, ge=2, le=365, description="Önceki baz periyot pencere"),
    threshold_percent: float = Query(default=10.0, gt=0, le=100, description="Drift eşik yüzdesi"),
    db: Session = Depends(get_db),
):
    now = datetime.now(UTC)
    recent_start = now - timedelta(days=recent_days)
    baseline_start = recent_start - timedelta(days=baseline_days)

    def _avg_accuracy(start: datetime, end: datetime) -> float | None:
        val = (
            db.query(func.avg(ModelPerformanceLog.accuracy_score))
            .filter(
                ModelPerformanceLog.model_name == model_name,
                ModelPerformanceLog.logged_at >= start,
                ModelPerformanceLog.logged_at < end,
            )
            .scalar()
        )
        return float(val) if val is not None else None

    recent_avg = _avg_accuracy(recent_start, now)
    baseline_avg = _avg_accuracy(baseline_start, recent_start)

    drift_percent: float | None = None
    drift_detected = False
    alert_created = False

    if recent_avg is not None and baseline_avg is not None and baseline_avg > 0:
        # Pozitif % = iyileşme, negatif % = drift
        drift_percent = ((recent_avg - baseline_avg) / baseline_avg) * 100
        if drift_percent < -threshold_percent:
            drift_detected = True
            # Aynı tip alert son 24 saat içinde varsa tekrar yaratma (spam önleme)
            existing = (
                db.query(SystemAlert)
                .filter(
                    SystemAlert.alert_type == "model_drift",
                    SystemAlert.message.like(f"%{model_name}%"),
                    SystemAlert.created_at >= now - timedelta(hours=24),
                )
                .first()
            )
            if existing is None:
                alert = SystemAlert(
                    alert_type="model_drift",
                    severity="medium",
                    message=(
                        f"Model '{model_name}' son {recent_days} günde %{abs(drift_percent):.1f} "
                        f"accuracy düşüşü gösterdi (baseline: %{baseline_avg * 100:.1f}, "
                        f"recent: %{recent_avg * 100:.1f})."
                    ),
                    is_resolved=False,
                )
                db.add(alert)
                db.commit()
                alert_created = True

    return ModelPerformanceDriftReport(
        model_name=model_name,
        recent_avg_accuracy=recent_avg,
        baseline_avg_accuracy=baseline_avg,
        drift_percent=drift_percent,
        drift_detected=drift_detected,
        threshold_percent=threshold_percent,
        recent_window_days=recent_days,
        baseline_window_days=baseline_days,
        alert_created=alert_created,
    )
