"""
Gübreleme API Endpoint'leri
=============================
Bitki türüne göre gübreleme önerisi ve takvim oluşturma.

Ayşe Eslem Çekici — Cycle 5 Görevi
"""

from fastapi import APIRouter

from app.schemas.schemas import (
    FertilizerRecommendRequest,
    FertilizerRecommendResponse,
    FertilizerScheduleRequest,
    FertilizerScheduleResponse,
)
from app.services.fertilizer_service import fertilizer_service

router = APIRouter(prefix="/api/fertilizer", tags=["Gubreleme Onerileri"])


@router.get("/crops")
def get_supported_crops():
    """Desteklenen bitki türlerini listeler."""
    crops = fertilizer_service.get_supported_crops()
    return {
        "count": len(crops),
        "crops": crops,
    }


@router.post("/recommend", response_model=FertilizerRecommendResponse)
def recommend_fertilizer(data: FertilizerRecommendRequest):
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
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail=result["message"])

    return result


@router.post("/schedules", response_model=list[FertilizerScheduleResponse])
def get_fertilizer_schedule(data: FertilizerScheduleRequest):
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
        from fastapi import HTTPException

        raise HTTPException(
            status_code=400,
            detail=f"Bilinmeyen bitki turu: {data.crop_type}",
        )

    return schedule
