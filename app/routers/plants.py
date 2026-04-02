from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.models import PlantHealthImage

router = APIRouter(prefix="/api/plants", tags=["Bitki Sagligi"])


@router.get("/health-images", response_model=list)
def get_health_images(field_id: int = None, limit: int = 20, db: Session = Depends(get_db)):
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


@router.post("/health-images", status_code=201)
def upload_health_image(
    field_id: int,
    image_url: str,
    db: Session = Depends(get_db)
):
    image = PlantHealthImage(field_id=field_id, image_url=image_url)
    db.add(image)
    db.commit()
    db.refresh(image)
    return {"id": image.id, "message": "Goruntu yuklendi"}
