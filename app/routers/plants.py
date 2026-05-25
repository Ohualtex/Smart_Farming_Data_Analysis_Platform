"""
Plant Health API Endpoints — REBUILD Faz 1 RBAC
=================================================
Yaprak görseli yükle/listele + CNN tabanlı hastalık tespiti uçları.
Default heuristic mod, ONNX model dosyası varsa otomatik geçer.

RBAC kapsamı:
    GET  /health-images             → Bearer + field ownership (filter)
    POST /health-images             → Bearer + write yetki + field ownership
    POST /health-images/analyze     → Bearer + write yetki + field ownership
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from sqlalchemy.orm import Session

from app.database import MAX_SQLITE_INT, get_db
from app.middleware.exceptions import ForbiddenError, ValidationError
from app.middleware.rate_limiter import AUTH_RATE, STRICT_RATE, limiter
from app.middleware.rbac import _WRITE_ROLES, assert_field_ownership
from app.ml.plant_disease_model import plant_disease_model
from app.models.models import Farm, Field, PlantHealthImage, User
from app.routers.auth import get_current_user_or_403

router = APIRouter(prefix="/api/plants", tags=["Bitki Sağlığı"])


def _require_write(user: User) -> None:
    """overseer/developer için 403; farmer + admin OK."""
    if user.role not in _WRITE_ROLES:
        raise ForbiddenError(detail=f"Yazma yetkisi yok (rol: {user.role}); farmer veya admin gerek.")


def _scope_images_to_user(query, user: User):  # noqa: ANN001
    """PlantHealthImage list query'sini rol'e göre kapsamlandır.

    farmer: image → field → farm.user_id == user.id
    admin/overseer/developer: bypass
    """
    if user.role in ("admin", "overseer", "developer"):
        return query
    return (
        query.join(Field, PlantHealthImage.field_id == Field.id)
        .join(Farm, Field.farm_id == Farm.id)
        .filter(Farm.user_id == user.id)
    )


# Yüklenen görsellerin saklanacağı dizin (gitignore'da)
UPLOAD_DIR = Path("app/ml/plant_uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# İzin verilen dosya formatları + maksimum boyut
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp"}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB


@router.get(
    "/health-images",
    response_model=list,
    summary="Bitki sağlığı görsellerini listele (rol-aware)",
    description="Belirli bir tarla (`field_id`) için kayıtlı görüntüleri en yeniden eskiye sıralar.",
    responses={401: {"description": "Bearer token gerekli"}},
)
def get_health_images(
    field_id: int | None = Query(default=None, ge=1, le=MAX_SQLITE_INT, description="Belirli tarla filtresi"),
    limit: int = Query(default=20, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_403),
) -> list[dict]:
    if field_id is not None:
        assert_field_ownership(db, field_id, current_user)
        query = db.query(PlantHealthImage).filter(PlantHealthImage.field_id == field_id)
    else:
        query = _scope_images_to_user(db.query(PlantHealthImage), current_user)
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
    summary="Yeni bitki sağlığı görseli yükle (URL bazlı, rol-aware)",
    description="`field_id` ve `image_url` ile kayıt oluşturur (CDN/external URL için). "
    "Multipart upload için `/health-images/analyze` kullanın.",
    responses={
        401: {"description": "Bearer token gerekli"},
        403: {"description": "Yazma yetkisi yok veya field sahibi değilsin"},
        404: {"description": "Field bulunamadı"},
    },
)
@limiter.limit(STRICT_RATE)
def upload_health_image(
    request: Request,
    field_id: int = Query(..., ge=1, le=MAX_SQLITE_INT, description="Tarla ID"),
    image_url: str = Query(..., description="CDN/external görsel URL'i"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_403),
) -> dict:
    _require_write(current_user)
    assert_field_ownership(db, field_id, current_user)
    image = PlantHealthImage(field_id=field_id, image_url=image_url)
    db.add(image)
    db.commit()
    db.refresh(image)
    return {"id": image.id, "message": "Goruntu yuklendi"}


@router.post(
    "/health-images/analyze",
    status_code=201,
    summary="Görsel yükle ve CNN ile anında hastalık teşhisi al (rol-aware)",
    description="Multipart form ile yaprak görseli yüklenir, `plant_disease_model` üzerinden "
    "tahmin yapılır ve sonuç hem response'da döner hem `PlantHealthImage` tablosuna kaydedilir.",
    responses={
        401: {"description": "Bearer token gerekli"},
        403: {"description": "Yazma yetkisi yok veya field sahibi değilsin"},
        404: {"description": "Field bulunamadı"},
        413: {"description": "Dosya çok büyük"},
        415: {"description": "Desteklenmeyen format"},
    },
)
@limiter.limit(AUTH_RATE)
async def analyze_plant_image(
    request: Request,
    field_id: int = Form(..., ge=1, le=MAX_SQLITE_INT, description="Tarla ID"),
    image: UploadFile = File(..., description="Yaprak görseli (JPG/PNG/WebP, max 5 MB)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_or_403),
) -> dict:
    _require_write(current_user)
    assert_field_ownership(db, field_id, current_user)
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
        raise ValidationError(message="Dosya boş.")

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
