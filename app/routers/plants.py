"""
Bitki Sağlığı API Endpoint'leri
=================================
Yaprak görüntülerinin yüklenmesi, listelenmesi ve CNN tabanlı hastalık
teşhisi. Mevcut model şu an stub (deterministic), Cycle 7'de Ayşe Eslem
Çekici tarafından gerçek ONNX CNN ile değiştirilecek.

Endpoint'ler:
- GET  /health-images           : Listele (field_id filtre, limit)
- POST /health-images           : URL ile kayıt (auth)
- POST /health-images/analyze   : Multipart upload + anında CNN teşhisi (auth)

Mehmet Sait Tayşi — Cycle 4 (skeleton) / Ayşe Eslem Çekici — Cycle 7 (CNN)
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from sqlalchemy.orm import Session

from app.database import MAX_SQLITE_INT, get_db
from app.middleware.auth import verify_api_key
from app.middleware.rate_limiter import AUTH_RATE, STRICT_RATE, limiter
from app.ml.plant_disease_model import plant_disease_model
from app.models.models import PlantHealthImage

router = APIRouter(prefix="/api/plants", tags=["Bitki Sağlığı"])

# Yüklenen görsellerin saklanacağı dizin (gitignore'da)
UPLOAD_DIR = Path("app/ml/plant_uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# İzin verilen dosya formatları + maksimum boyut
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp"}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB


@router.get(
    "/health-images",
    response_model=list,
    summary="Bitki sağlığı görsellerini listele",
    description="Belirli bir tarla (`field_id`) için kayıtlı görüntüleri en yeniden eskiye sıralar.",
)
def get_health_images(
    field_id: int | None = Query(default=None, ge=1, le=MAX_SQLITE_INT, description="Belirli tarla filtresi"),
    limit: int = Query(default=20, ge=1, le=500),
    db: Session = Depends(get_db),
):
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
    summary="Yeni bitki sağlığı görseli yükle (URL bazlı)",
    description="`field_id` ve `image_url` ile kayıt oluşturur (CDN/external URL için). "
    "Multipart upload için `/health-images/analyze` kullanın.",
)
@limiter.limit(STRICT_RATE)
def upload_health_image(request: Request, field_id: int, image_url: str, db: Session = Depends(get_db)):
    image = PlantHealthImage(field_id=field_id, image_url=image_url)
    db.add(image)
    db.commit()
    db.refresh(image)
    return {"id": image.id, "message": "Goruntu yuklendi"}


@router.post(
    "/health-images/analyze",
    status_code=201,
    dependencies=[Depends(verify_api_key)],
    summary="Görsel yükle ve CNN ile anında hastalık teşhisi al",
    description="Multipart form ile yaprak görseli yüklenir, `plant_disease_model` üzerinden "
    "tahmin yapılır ve sonuç hem response'da döner hem `PlantHealthImage` tablosuna kaydedilir.",
)
@limiter.limit(AUTH_RATE)
async def analyze_plant_image(
    request: Request,
    field_id: int = Form(..., description="Tarla ID"),
    image: UploadFile = File(..., description="Yaprak görseli (JPG/PNG/WebP, max 5 MB)"),
    db: Session = Depends(get_db),
):
    # ─── Validasyon ──────────────────────────────────────────────
    ext = Path(image.filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(
            status_code=415,
            detail=f"Desteklenmeyen format: {ext}. Izin verilen: {', '.join(ALLOWED_EXT)}",
        )

    # Dosyayı oku + boyut sınırı
    content = await image.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Dosya cok buyuk ({len(content)} byte). Max: {MAX_UPLOAD_BYTES} byte.",
        )
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Dosya bos")

    # ─── Diske kaydet ────────────────────────────────────────────
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f")
    safe_name = f"field{field_id}_{timestamp}{ext}"
    save_path = UPLOAD_DIR / safe_name
    save_path.write_bytes(content)
    image_url = f"/static/plant_uploads/{safe_name}"  # frontend bu URL ile erişir

    # ─── CNN modelinden tahmin ───────────────────────────────────
    prediction = plant_disease_model.predict(content)

    # ─── DB kaydı ────────────────────────────────────────────────
    record = PlantHealthImage(
        field_id=field_id,
        image_url=image_url,
        diagnosis=prediction["diagnosis"],
        confidence_score=prediction["confidence_score"],
        severity=prediction["severity"],
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "id": record.id,
        "field_id": record.field_id,
        "image_url": record.image_url,
        "diagnosis": record.diagnosis,
        "confidence_score": record.confidence_score,
        "severity": record.severity,
        "size_bytes": len(content),
        "model_version": prediction["model_version"],
        "all_scores": prediction["all_scores"],
    }


# Yüklenen dosyalar gitignore'da kalsın
def _ensure_gitignore():
    gi = UPLOAD_DIR / ".gitignore"
    if not gi.exists():
        gi.write_text("*\n!.gitignore\n")


_ensure_gitignore()
