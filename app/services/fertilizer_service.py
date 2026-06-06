"""
Fertilizer Recommendation Service
===================================
Computes per-crop NPK (nitrogen-phosphorus-potassium) needs and
proposes a fertilizer schedule from soil-analysis data.

Rule-based model: `crop need - current soil value = amount to apply`.

---

Bitki türüne göre NPK ihtiyacını hesaplar ve toprak analizine göre
gübre takvimi önerir. Kural: `bitki ihtiyacı - mevcut toprak = uygulama`.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta


class FertilizerService:
    """
    Bitki türüne göre gübreleme önerisi sunan servis.
    NPK hesaplaması ve gübreleme takvimi oluşturma.
    """

    # Per-crop ideal NPK demand (mg/kg soil). Covers 17 crop species
    # spanning the 7 geographic regions of Türkiye (see
    # `database/turkey_data.py`).
    # ---
    # Bitki türüne göre ideal NPK ihtiyacı (mg/kg toprak). Türkiye'nin
    # 7 bölgesinde yetiştirilen 17 bitki türünü kapsar.
    CROP_NPK_REQUIREMENTS: dict[str, dict[str, float]] = {
        # ─── Tahıllar ──────────────────────────────────────────
        "wheat": {"N": 120.0, "P": 60.0, "K": 40.0, "name_tr": "Buğday"},
        "corn": {"N": 180.0, "P": 80.0, "K": 60.0, "name_tr": "Mısır"},
        "barley": {"N": 100.0, "P": 50.0, "K": 40.0, "name_tr": "Arpa"},
        "rice": {"N": 140.0, "P": 50.0, "K": 40.0, "name_tr": "Pirinç"},
        # ─── Sebzeler & Endüstriyel ────────────────────────────
        "tomato": {"N": 150.0, "P": 100.0, "K": 200.0, "name_tr": "Domates"},
        "pepper": {"N": 130.0, "P": 80.0, "K": 160.0, "name_tr": "Biber"},
        "potato": {"N": 160.0, "P": 90.0, "K": 180.0, "name_tr": "Patates"},
        "cotton": {"N": 140.0, "P": 60.0, "K": 80.0, "name_tr": "Pamuk"},
        "sunflower": {"N": 100.0, "P": 70.0, "K": 50.0, "name_tr": "Ayçiçeği"},
        "sugar_beet": {"N": 180.0, "P": 80.0, "K": 240.0, "name_tr": "Şeker Pancarı"},
        # ─── Meyve Ağaçları & Çok Yıllık ───────────────────────
        "olive": {"N": 80.0, "P": 40.0, "K": 80.0, "name_tr": "Zeytin"},
        "grape": {"N": 80.0, "P": 60.0, "K": 120.0, "name_tr": "Üzüm"},
        "apple": {"N": 100.0, "P": 50.0, "K": 120.0, "name_tr": "Elma"},
        "citrus": {"N": 140.0, "P": 60.0, "K": 140.0, "name_tr": "Narenciye"},
        "hazelnut": {"N": 100.0, "P": 50.0, "K": 100.0, "name_tr": "Fındık"},
        "pistachio": {"N": 80.0, "P": 40.0, "K": 80.0, "name_tr": "Antep Fıstığı"},
        "tea": {"N": 120.0, "P": 40.0, "K": 80.0, "name_tr": "Çay"},
    }

    # Gübreleme programı şablonları (bitki türünden bağımsız genel takvim)
    SCHEDULE_TEMPLATE = [
        {
            "phase": "Toprak Hazırlığı",
            "timing": "Ekim öncesi 2 hafta",
            "day_offset": -14,
            "fertilizer_type": "DAP (Diamonyum Fosfat)",
            "npk_ratio": {"N": 0.3, "P": 0.6, "K": 0.2},
            "notes": "Toprağı derin sürüm sonrası uygulayın.",
        },
        {
            "phase": "Ekim Dönemi",
            "timing": "Ekim sırasında",
            "day_offset": 0,
            "fertilizer_type": "20-20-0 Kompoze",
            "npk_ratio": {"N": 0.2, "P": 0.3, "K": 0.0},
            "notes": "Tohum yatağına band halinde uygulayın.",
        },
        {
            "phase": "Erken Gelişim",
            "timing": "Ekimden 30 gün sonra",
            "day_offset": 30,
            "fertilizer_type": "Üre (%46 N)",
            "npk_ratio": {"N": 0.25, "P": 0.0, "K": 0.3},
            "notes": "Yaprak gelişimi için azot takviyesi.",
        },
        {
            "phase": "Çiçeklenme Öncesi",
            "timing": "Ekimden 60 gün sonra",
            "day_offset": 60,
            "fertilizer_type": "Potasyum Sülfat",
            "npk_ratio": {"N": 0.15, "P": 0.1, "K": 0.3},
            "notes": "Meyve/tane oluşumu için potasyum takviyesi.",
        },
        {
            "phase": "Son Gübre",
            "timing": "Hasattan 30 gün önce",
            "day_offset": 90,
            "fertilizer_type": "NPK 15-15-15",
            "npk_ratio": {"N": 0.1, "P": 0.0, "K": 0.2},
            "notes": "Son dönem destek gübrelemesi. Hasat öncesi kesilir.",
        },
    ]

    def get_supported_crops(self) -> list[dict]:
        """Desteklenen bitki türlerini döndürür."""
        return [
            {
                "crop_type": key,
                "name_tr": val["name_tr"],
                "nitrogen_need": val["N"],
                "phosphorus_need": val["P"],
                "potassium_need": val["K"],
            }
            for key, val in self.CROP_NPK_REQUIREMENTS.items()
        ]

    def recommend(
        self,
        crop_type: str,
        soil_nitrogen: float,
        soil_phosphorus: float,
        soil_potassium: float,
        area_hectares: float,
    ) -> dict:
        """
        Bitki türü ve toprak analiz değerlerine göre gübreleme önerisi hesaplar.

        Args:
            crop_type: Bitki türü (wheat, corn, tomato, ...)
            soil_nitrogen: Topraktaki mevcut azot (mg/kg)
            soil_phosphorus: Topraktaki mevcut fosfor (mg/kg)
            soil_potassium: Topraktaki mevcut potasyum (mg/kg)
            area_hectares: Tarla alanı (hektar)

        Returns:
            NPK eksikliği ve gübreleme önerisi
        """
        crop_type_lower = crop_type.lower()

        if crop_type_lower not in self.CROP_NPK_REQUIREMENTS:
            return {
                "error": True,
                "message": f"Bilinmeyen bitki turu: {crop_type}. "
                f"Desteklenen turler: {', '.join(self.CROP_NPK_REQUIREMENTS.keys())}",
            }

        requirements = self.CROP_NPK_REQUIREMENTS[crop_type_lower]

        # Eksik miktarları hesapla (negatif olmamalı)
        n_deficit = max(0.0, requirements["N"] - soil_nitrogen)
        p_deficit = max(0.0, requirements["P"] - soil_phosphorus)
        k_deficit = max(0.0, requirements["K"] - soil_potassium)

        # Hektar başına kg cinsinden toplam ihtiyaç (mg/kg → kg/ha dönüşüm faktörü ~2)
        conversion_factor = 2.0
        n_needed_kg = round(n_deficit * conversion_factor * area_hectares, 1)
        p_needed_kg = round(p_deficit * conversion_factor * area_hectares, 1)
        k_needed_kg = round(k_deficit * conversion_factor * area_hectares, 1)
        total_kg = round(n_needed_kg + p_needed_kg + k_needed_kg, 1)

        # Öneri mesajı
        recommendation = self._generate_recommendation(crop_type_lower, n_deficit, p_deficit, k_deficit, total_kg)

        return {
            "crop_type": crop_type_lower,
            "crop_name_tr": requirements["name_tr"],
            "area_hectares": area_hectares,
            "soil_analysis": {
                "nitrogen": soil_nitrogen,
                "phosphorus": soil_phosphorus,
                "potassium": soil_potassium,
            },
            "deficit": {
                "nitrogen_mg_kg": round(n_deficit, 1),
                "phosphorus_mg_kg": round(p_deficit, 1),
                "potassium_mg_kg": round(k_deficit, 1),
            },
            "nitrogen_needed_kg": n_needed_kg,
            "phosphorus_needed_kg": p_needed_kg,
            "potassium_needed_kg": k_needed_kg,
            "total_fertilizer_kg": total_kg,
            "recommendation": recommendation,
        }

    def generate_schedule(
        self,
        crop_type: str,
        planting_date: str,
        area_hectares: float,
        soil_nitrogen: float = 0.0,
        soil_phosphorus: float = 0.0,
        soil_potassium: float = 0.0,
    ) -> list[dict]:
        """
        Bitki türü ve ekim tarihine göre gübreleme takvimi oluşturur.

        Args:
            crop_type: Bitki türü
            planting_date: Ekim tarihi (YYYY-MM-DD)
            area_hectares: Tarla alanı (hektar)
            soil_*: Mevcut toprak değerleri (opsiyonel)

        Returns:
            Gübreleme takvimi listesi
        """
        crop_type_lower = crop_type.lower()

        if crop_type_lower not in self.CROP_NPK_REQUIREMENTS:
            return []

        requirements = self.CROP_NPK_REQUIREMENTS[crop_type_lower]
        # `planting_date` kullanıcı girdisi (YYYY-MM-DD); UTC olarak yorumla
        # ki naive datetime aritmetiği tz-aware kalsın (DTZ007).
        # EN: Treat user-supplied date as UTC midnight for tz-aware arithmetic.
        base_date = datetime.strptime(planting_date, "%Y-%m-%d").replace(tzinfo=UTC)

        # Eksik miktarları hesapla
        n_deficit = max(0.0, requirements["N"] - soil_nitrogen)
        p_deficit = max(0.0, requirements["P"] - soil_phosphorus)
        k_deficit = max(0.0, requirements["K"] - soil_potassium)

        schedule = []
        for phase in self.SCHEDULE_TEMPLATE:
            target_date = base_date + timedelta(days=phase["day_offset"])

            # Faz başına düşen gübre miktarı
            n_amount = round(n_deficit * phase["npk_ratio"]["N"] * area_hectares * 2, 1)
            p_amount = round(p_deficit * phase["npk_ratio"]["P"] * area_hectares * 2, 1)
            k_amount = round(k_deficit * phase["npk_ratio"]["K"] * area_hectares * 2, 1)
            total_phase = round(n_amount + p_amount + k_amount, 1)

            schedule.append(
                {
                    "phase": phase["phase"],
                    "timing": phase["timing"],
                    "target_date": target_date.strftime("%Y-%m-%d"),
                    "fertilizer_type": phase["fertilizer_type"],
                    "amount_kg_per_hectare": round(total_phase / area_hectares, 1) if area_hectares > 0 else 0,
                    "total_amount_kg": total_phase,
                    "notes": phase["notes"],
                }
            )

        return schedule

    def _generate_recommendation(
        self,
        crop_type: str,
        n_deficit: float,
        p_deficit: float,
        k_deficit: float,
        total_kg: float,
    ) -> str:
        """İnsan okunabilir gübreleme önerisi oluşturur."""
        crop_name = self.CROP_NPK_REQUIREMENTS[crop_type]["name_tr"]

        if total_kg == 0:
            return f"{crop_name} icin topraginiz yeterli besin iceriyor. Ek gubreleme gerekmez."

        parts = []
        if n_deficit > 0:
            parts.append(f"azot (N) eksikligi ({n_deficit:.0f} mg/kg)")
        if p_deficit > 0:
            parts.append(f"fosfor (P) eksikligi ({p_deficit:.0f} mg/kg)")
        if k_deficit > 0:
            parts.append(f"potasyum (K) eksikligi ({k_deficit:.0f} mg/kg)")

        deficit_text = ", ".join(parts)

        if total_kg < 50:
            severity = "Hafif"
        elif total_kg < 150:
            severity = "Orta duzeyde"
        else:
            severity = "Yuksek"

        return (
            f"{crop_name} yetistirmek icin topraginizda {deficit_text} tespit edildi. "
            f"{severity} gubreleme oneriliyor (toplam {total_kg:.0f} kg)."
        )


# Singleton instance
fertilizer_service = FertilizerService()
