"""
Plant Disease Detection Model
==============================
Yaprak görsellerinden bitki hastalığı teşhisi yapan ML servisi.

İki çalışma modu:
1) **ONNX modu** — `MODEL_PATH` altında `plant_disease_cnn.onnx` mevcutsa
   onnxruntime InferenceSession ile gerçek CNN inference yapar.
2) **Heuristic modu** — model dosyası yoksa Pillow ile görsel analiz
   (renk histogramı + sağlıklı yeşil oranı + kahve/sarı leke oranı)
   üzerinden kural-bazlı teşhis verir. Hash-stub'tan farklı olarak
   gerçekten görsele duyarlıdır.

Çıktı her iki modda da aynı şemada:
    {
        "diagnosis": "leaf_spot",
        "confidence_score": 0.78,
        "severity": "low",
        "all_scores": {"healthy": 0.12, "leaf_spot": 0.78, ...},
        "model_version": "heuristic-v1" | "onnx-v1",
    }

CNN model eğitimi (PlantVillage dataset) tamamlanıp ONNX'e export
edildiğinde dosyayı `app/ml/models/plant_disease_cnn.onnx` olarak koy;
servis otomatik olarak ONNX moduna geçer.

Ayşe Eslem Çekici — Cycle 7
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import numpy as np

from app.config import settings

DISEASE_CLASSES = [
    "healthy",
    "leaf_spot",
    "powdery_mildew",
    "rust",
    "blight",
    "mosaic_virus",
    "bacterial_wilt",
    "anthracnose",
]

SEVERITY_MAP = {
    "healthy": "none",
    "leaf_spot": "low",
    "powdery_mildew": "medium",
    "rust": "medium",
    "blight": "high",
    "mosaic_virus": "high",
    "bacterial_wilt": "high",
    "anthracnose": "medium",
}

# ONNX inference için input shape — eğitim sırasında belirlenecek
ONNX_INPUT_SIZE = (224, 224)

# Heuristic eşikleri (Pillow HSV: H, S, V hepsi 0-255 aralığında)
HEALTHY_GREEN_HUE = (75, 110)  # taze yeşil yaprak (HSV ~120°)
YELLOW_HUE = (28, 50)  # sararma → mosaic_virus / anthracnose (~50°)
BROWN_HUE = (10, 25)  # kahverengi leke → leaf_spot / blight (~25°)
WHITE_LIGHTNESS_MIN = 200  # beyaz/gri tabaka → powdery_mildew


class PlantDiseaseModel:
    """
    Yaprak görüntüsünden hastalık teşhisi.

    İlk başlatmada `_load_model()` ONNX dosyasını arar; bulamazsa
    heuristic moda düşer. `predict(image_bytes)` her iki modda da aynı
    şema döndürür.
    """

    def __init__(self, model_path: str | None = None):
        self.model_path = model_path or str(Path(settings.MODEL_PATH) / "plant_disease_cnn.onnx")
        self.session: Any = None
        self.mode = "heuristic"  # 'onnx' | 'heuristic'
        self._load_model()

    def _load_model(self) -> None:
        """ONNX dosyası varsa InferenceSession yükle; yoksa heuristic."""
        if not Path(self.model_path).exists():
            self.session = None
            self.mode = "heuristic"
            return
        try:
            import onnxruntime as ort

            self.session = ort.InferenceSession(self.model_path, providers=["CPUExecutionProvider"])
            self.mode = "onnx"
        except Exception:
            # Onnxruntime yok veya bozuk model — sessizce heuristic'e düş
            self.session = None
            self.mode = "heuristic"

    def predict(self, image_bytes: bytes) -> dict:
        """Görüntü baytlarından sınıf + güven skoru tahmini."""
        if not image_bytes:
            return self._error_response("empty image")
        # Görseli aç ve doğrula
        try:
            from PIL import Image, UnidentifiedImageError
        except ImportError:
            return self._error_response("Pillow yuklu degil")
        try:
            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except (UnidentifiedImageError, OSError, ValueError):
            return self._error_response("invalid image")

        if self.mode == "onnx" and self.session is not None:
            return self._onnx_predict(img)
        return self._heuristic_predict(img)

    # ─── ONNX inference ────────────────────────────────────────
    def _onnx_predict(self, img: Any) -> dict:
        """Gerçek CNN inference — model dosyası varsa."""
        img_resized = img.resize(ONNX_INPUT_SIZE)
        arr = np.asarray(img_resized, dtype=np.float32) / 255.0
        # NCHW: (1, 3, H, W) — eğitim sırasında bu format varsayıldı
        arr = arr.transpose(2, 0, 1)[np.newaxis, ...]

        input_name = self.session.get_inputs()[0].name
        outputs = self.session.run(None, {input_name: arr})
        logits = outputs[0][0]
        probs = self._softmax(logits)

        idx = int(np.argmax(probs))
        diagnosis = DISEASE_CLASSES[idx] if idx < len(DISEASE_CLASSES) else "healthy"
        confidence = float(probs[idx])
        all_scores = {
            DISEASE_CLASSES[i]: round(float(probs[i]), 3) for i in range(min(len(DISEASE_CLASSES), len(probs)))
        }
        return {
            "diagnosis": diagnosis,
            "confidence_score": round(confidence, 3),
            "severity": SEVERITY_MAP.get(diagnosis, "low"),
            "all_scores": all_scores,
            "model_version": "onnx-v1",
        }

    @staticmethod
    def _softmax(x):
        x = np.asarray(x, dtype=np.float64)
        e = np.exp(x - np.max(x))
        return e / e.sum()

    # ─── Heuristic predict ─────────────────────────────────────
    def _heuristic_predict(self, img: Any) -> dict:
        """
        HSV renk dağılımı üzerinden basit kural-bazlı teşhis.

        - Yeşil oranı yüksek → healthy
        - Sarı baskın → mosaic_virus / anthracnose
        - Kahverengi leke → leaf_spot / blight
        - Açık beyaz tabaka → powdery_mildew
        - Düşük doygunluk + soluk → rust
        """
        # Performans için küçült
        thumb = img.copy()
        thumb.thumbnail((128, 128))
        hsv = thumb.convert("HSV")
        # Pillow 14'te getdata() deprecate olacak — numpy ile pixel okuma
        # hem future-proof hem ~3× daha hızlı.
        # EN: getdata() is deprecated in Pillow 14; numpy access is future-
        # proof and ~3× faster than the legacy list(getdata()) path.
        pixel_array = np.asarray(hsv, dtype=np.uint8).reshape(-1, 3)
        pixels = pixel_array.tolist()  # list[list[int]] — for-loop unpack ile uyumlu
        total = len(pixels)
        if total == 0:
            return self._error_response("empty pixels")

        green = yellow = brown = white = saturated = 0
        for h, s, v in pixels:
            if v >= WHITE_LIGHTNESS_MIN and s < 40:
                white += 1
                continue
            if HEALTHY_GREEN_HUE[0] <= h <= HEALTHY_GREEN_HUE[1] and s >= 60:
                green += 1
            elif YELLOW_HUE[0] <= h <= YELLOW_HUE[1] and s >= 80:
                yellow += 1
            elif BROWN_HUE[0] <= h <= BROWN_HUE[1] and s >= 60:
                brown += 1
            if s >= 80:
                saturated += 1

        green_ratio = green / total
        yellow_ratio = yellow / total
        brown_ratio = brown / total
        white_ratio = white / total
        sat_ratio = saturated / total

        # Kural sıralaması (sırayla en güçlü sinyalden başla)
        if white_ratio > 0.18:
            diagnosis = "powdery_mildew"
            confidence = min(0.95, 0.55 + white_ratio)
        elif brown_ratio > 0.12 and brown_ratio > yellow_ratio:
            diagnosis = "blight" if brown_ratio > 0.25 else "leaf_spot"
            confidence = min(0.95, 0.55 + brown_ratio * 1.5)
        elif yellow_ratio > 0.18:
            diagnosis = "mosaic_virus" if green_ratio < 0.2 else "anthracnose"
            confidence = min(0.95, 0.55 + yellow_ratio)
        elif sat_ratio < 0.15 and green_ratio < 0.25:
            diagnosis = "rust"
            confidence = 0.6
        elif green_ratio > 0.4:
            diagnosis = "healthy"
            confidence = min(0.97, 0.6 + green_ratio * 0.4)
        elif green_ratio > 0.2:
            diagnosis = "healthy"
            confidence = 0.65
        else:
            diagnosis = "bacterial_wilt"
            confidence = 0.55

        # Tüm sınıflar için skor üret (diagnosis'e ağırlık)
        base = (1 - confidence) / (len(DISEASE_CLASSES) - 1)
        all_scores = {c: round(base, 3) for c in DISEASE_CLASSES}
        all_scores[diagnosis] = round(confidence, 3)

        return {
            "diagnosis": diagnosis,
            "confidence_score": round(confidence, 3),
            "severity": SEVERITY_MAP.get(diagnosis, "low"),
            "all_scores": all_scores,
            "model_version": "heuristic-v1",
            "color_features": {
                "green_ratio": round(green_ratio, 3),
                "yellow_ratio": round(yellow_ratio, 3),
                "brown_ratio": round(brown_ratio, 3),
                "white_ratio": round(white_ratio, 3),
            },
        }

    @staticmethod
    def _error_response(message: str) -> dict:
        all_scores = dict.fromkeys(DISEASE_CLASSES, 0.0)
        all_scores["healthy"] = 0.0
        return {
            "diagnosis": "unknown",
            "confidence_score": 0.0,
            "severity": "none",
            "all_scores": all_scores,
            "model_version": "error",
            "error": message,
        }


# Global instance — uygulama başlangıcında lazy init
plant_disease_model = PlantDiseaseModel()
