"""
Bitki Sağlığı API Endpoint'leri
=================================
Yapraktan görüntü alarak hastalık teşhisi yapılan PlantHealthImage kayıtları.
Cycle 7'de (Ayşe) bu endpoint CNN modeli ile entegre edilecek; şu an
sadece kayıtların listelenmesi ve URL bazlı upload destekleniyor.

Mehmet Sait Tayşi — Cycle 4 (skeleton) / Ayşe Eslem Çekici — Cycle 7 (CNN)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import verify_api_key
from app.models.models import PlantHealthImage

router = APIRouter(prefix="/api/plants", tags=["Bitki Sağlığı"])


@router.get(
    "/health-images",
    response_model=list,
    summary="Bitki sağlığı görsellerini listele",
    description="Belirli bir tarla (`field_id`) için kayıtlı görüntüleri en yeniden eskiye sıralar.",
)
def get_health_images(field_id: int | None = None, limit: int = 20, db: Session = Depends(get_db)):
    query = db.query(PlantHealthImage)
    if field_id:
        query = query.filter(PlantHealthImage.field_id == field_id)
    results = query.order_by(PlantHealthImage.captured_at.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "field_id": r.field_id,
            "image_url": r.image_url,
            "captured_at": str(r.captured_at),
            "diagnosis": r.diagnosis,
            "confidence_score": r.confidence_score,
            "severity": r.severity,
        }
        for r in results
    ]


@router.post(
    "/health-images",
    status_code=201,
    dependencies=[Depends(verify_api_key)],
    summary="Yeni bitki sağlığı görseli yükle",
    description="`field_id` ve `image_url` ile kayıt oluşturur. Cycle 7'de "
    "multipart upload + CNN tahmini ile genişletilecek.",
)
def upload_health_image(field_id: int, image_url: str, db: Session = Depends(get_db)):
    image = PlantHealthImage(field_id=field_id, image_url=image_url)
    db.add(image)
    db.commit()
    db.refresh(image)
    return {"id": image.id, "message": "Goruntu yuklendi"}
