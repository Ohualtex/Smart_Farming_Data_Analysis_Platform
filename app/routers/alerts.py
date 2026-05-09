"""
Sistem Uyarı (System Alert) API Endpoint'leri
==============================================
Veri hattı izleme ve sistem uyarılarının CRUD işlemleri.
Sensör anomalisi, hava durumu uyarıları, sistem hataları gibi
otomatik veya manuel oluşturulan alert'lerin listelenmesi,
oluşturulması ve resolve edilmesi.

Ecenur Üner — Cycle 6 Görevi (shiftSession): Veri Hattı İzleme ve Uyarı Sistemi

Bu modül router skeleton + 4 temel endpoint sağlar; Ecenur tarafından
genişletilebilir (filtreleme, severity bazlı query, batch resolve, vb.).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import verify_api_key
from app.middleware.rate_limiter import STRICT_RATE, limiter
from app.models.models import SystemAlert
from app.schemas.schemas import SystemAlertCreate, SystemAlertResponse, SystemAlertUpdate

router = APIRouter(prefix="/api/alerts", tags=["Sistem Uyarıları"])


@router.get(
    "/",
    response_model=list[SystemAlertResponse],
    summary="Sistem uyarılarını listele",
    description="Tüm sistem alert'lerini en yeniden eskiye sıralı döndürür. "
    "Severity ve resolved durumuna göre filtrelenebilir.",
)
def list_alerts(
    severity: str | None = Query(default=None, description="Filtre: 'low' | 'medium' | 'critical'"),
    is_resolved: bool | None = Query(default=None, description="Filtre: çözüldü mü?"),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    query = db.query(SystemAlert)
    if severity is not None:
        query = query.filter(SystemAlert.severity == severity)
    if is_resolved is not None:
        query = query.filter(SystemAlert.is_resolved == is_resolved)
    return query.order_by(SystemAlert.created_at.desc()).limit(limit).all()


@router.get(
    "/{alert_id}",
    response_model=SystemAlertResponse,
    summary="Tek bir uyarı getir",
)
def get_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(SystemAlert).filter(SystemAlert.id == alert_id).first()
    if alert is None:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} bulunamadi")
    return alert


@router.post(
    "/",
    response_model=SystemAlertResponse,
    status_code=201,
    dependencies=[Depends(verify_api_key)],
    summary="Yeni uyarı oluştur",
)
@limiter.limit(STRICT_RATE)
def create_alert(request: Request, payload: SystemAlertCreate, db: Session = Depends(get_db)):
    alert = SystemAlert(**payload.model_dump())
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


@router.patch(
    "/{alert_id}",
    response_model=SystemAlertResponse,
    dependencies=[Depends(verify_api_key)],
    summary="Uyarıyı güncelle (resolve / severity / mesaj)",
)
@limiter.limit(STRICT_RATE)
def update_alert(request: Request, alert_id: int, payload: SystemAlertUpdate, db: Session = Depends(get_db)):
    alert = db.query(SystemAlert).filter(SystemAlert.id == alert_id).first()
    if alert is None:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} bulunamadi")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(alert, field, value)
    db.commit()
    db.refresh(alert)
    return alert
