"""
Fertilizer API Endpoints — REBUILD Faz 1 RBAC (stateless public)
==================================================================
Bitki türüne göre gübreleme önerisi + takvim oluşturma uçları.

RBAC kapsamı: **public** — stateless calculator endpoint'leri, DB'ye
yazmaz (irrigation `/predict` gibi). Demo akışında her kullanıcı
(anonim dahil) gübre önerisi alabilir.

Faz 4'te (`FertilizerRecommendationLog` ile öneri persist edildiğinde)
field ownership eklenecek; o ana kadar auth bağımsız.
"""

from fastapi import APIRouter

from app.middleware.exceptions import ValidationError
from app.schemas.schemas import (
    FertilizerRecommendRequest,
    FertilizerRecommendResponse,
    FertilizerScheduleRequest,
    FertilizerScheduleResponse,
)
from app.services.fertilizer_service import fertilizer_service

router = APIRouter(prefix="/api/fertilizer", tags=["Gubreleme Onerileri"])


@router.get("/crops")
def get_supported_crops() -> dict:
    """Desteklenen bitki türlerini listeler."""
    crops = fertilizer_service.get_supported_crops()
    return {
        "count": len(crops),
        "crops": crops,
    }


@router.post(
    "/recommend",
    response_model=FertilizerRecommendResponse,
    responses={400: {"description": "Geçersiz JSON body veya iş kuralı ihlali"}},
)
def recommend_fertilizer(data: FertilizerRecommendRequest) -> FertilizerRecommendResponse:
    """
    Bitki türü ve toprak analiz değerlerine göre gübreleme önerisi döndürür.

    NPK eksikliğini hesaplar ve hektar başına gereken gübre miktarını belirler.
    """
    result = fertilizer_service.recommend(
        crop_type=data.crop_type,
        soil_nitrogen=data.soil_nitrogen,
        soil_phosphorus=data.soil_phosphorus,
        soil_potassium=data.soil_potassium,
        area_hectares=data.area_hectares,
    )

    if result.get("error"):
        raise ValidationError(message=result["message"])

    return result


@router.post(
    "/schedules",
    response_model=list[FertilizerScheduleResponse],
    responses={400: {"description": "Geçersiz JSON body"}},
)
def get_fertilizer_schedule(data: FertilizerScheduleRequest) -> list[FertilizerScheduleResponse]:
    """
    Ekim tarihine ve bitki türüne göre gübreleme takvimi oluşturur.

    5 fazlı gübreleme programı döndürür:
    1. Toprak Hazırlığı (ekim öncesi)
    2. Ekim Dönemi
    3. Erken Gelişim
    4. Çiçeklenme Öncesi
    5. Son Gübre
    """
    schedule = fertilizer_service.generate_schedule(
        crop_type=data.crop_type,
        planting_date=data.planting_date,
        area_hectares=data.area_hectares,
        soil_nitrogen=data.soil_nitrogen,
        soil_phosphorus=data.soil_phosphorus,
        soil_potassium=data.soil_potassium,
    )

    if not schedule:
        raise ValidationError(message=f"Bilinmeyen bitki türü: {data.crop_type}")

    return schedule
