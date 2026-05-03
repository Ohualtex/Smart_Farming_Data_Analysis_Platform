"""
Bitki Hastalığı CNN Modeli — İskelet
======================================
Yaprak görsellerinden hastalık tespiti yapan CNN modelinin başlangıç
iskeleti. Cycle 7'de Ayşe Eslem Çekici tarafından geliştirilecek.

Mevcut durum: deterministic stub (gerçek inference yerine örnek tahmin
döndürür). Bu sayede `plants.py` endpoint'i ve frontend entegrasyonu
gerçek model eğitilmeden önce test edilebilir.

Genişletme adımları (Cycle 7 — Ayşe):
1. PlantVillage benzeri bir dataset ile baseline CNN eğit (TensorFlow / PyTorch).
2. ONNX'e export et (`onnxruntime` requirements'ta hazır).
3. `_load_model()` içine onnxruntime.InferenceSession yerleştir.
4. `predict()` içinde gerçek tensor preprocessing + inference yap.
5. `eval.py` `classification_metrics()` ile model değerlendirme raporu üret.
6. `ModelPerformanceLog` tablosuna otomatik log entegrasyonu (irrigation gibi).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

# Desteklenen hastalık sınıfları (yer tutucu — gerçek dataset etiketleriyle değiştirilecek)
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


class PlantDiseaseModel:
    """
    Yaprak görüntüsünden bitki hastalığı tespit eden CNN sarıcı.

    Şu an deterministic stub: girdiye (image bytes) göre hash bazlı
    sahte tahmin döndürür. Aynı görüntü → aynı sınıf (test edilebilir).
    Cycle 7'de gerçek ONNX model ile değiştirilecek.
    """

    def __init__(self, model_path: str | None = None):
        self.model_path = model_path or "app/ml/models/plant_disease_cnn.onnx"
        self.session = None  # ONNXRuntime InferenceSession (Cycle 7)
        self._load_model()

    def _load_model(self) -> None:
        """ONNX model dosyasını yükler. Şu an placeholder — yoksa stub kullan."""
        if not Path(self.model_path).exists():
            # Production: yoksa hata fırlatmaz, stub modunda kalır
            self.session = None
            return
        # TODO Cycle 7 — Ayşe:
        # import onnxruntime as ort
        # self.session = ort.InferenceSession(self.model_path)

    def predict(self, image_bytes: bytes) -> dict:
        """
        Görüntü baytlarından sınıf + güven skoru tahmini.

        Returns:
            {
                "diagnosis": "leaf_spot",
                "confidence_score": 0.87,
                "severity": "low",
                "all_scores": {"healthy": 0.05, "leaf_spot": 0.87, ...},
                "model_version": "stub-v0",
            }
        """
        if self.session is None:
            return self._stub_predict(image_bytes)
        # TODO Cycle 7 — Ayşe: gerçek ONNX inference
        # img = self._preprocess(image_bytes)
        # outputs = self.session.run(None, {"input": img})
        # probs = self._softmax(outputs[0][0])
        # return {...}
        return self._stub_predict(image_bytes)

    def _stub_predict(self, image_bytes: bytes) -> dict:
        """Hash bazlı deterministic stub — geliştirme/test için."""
        # Görüntü hash'inden sınıf seç (deterministic)
        h = hashlib.sha256(image_bytes).hexdigest()
        cls_idx = int(h[:8], 16) % len(DISEASE_CLASSES)
        diagnosis = DISEASE_CLASSES[cls_idx]
        # Güven skoru hash'in ikinci yarısından (stable random)
        confidence = 0.65 + (int(h[8:12], 16) % 35) / 100  # 0.65-1.00
        # Tüm skorlar (placeholder uniform)
        all_scores = {
            c: round(0.05 + (int(h[i * 4 : (i + 1) * 4], 16) % 20) / 100, 3) for i, c in enumerate(DISEASE_CLASSES)
        }
        # Seçilen sınıfa yüksek skor
        all_scores[diagnosis] = round(confidence, 3)
        return {
            "diagnosis": diagnosis,
            "confidence_score": round(confidence, 3),
            "severity": SEVERITY_MAP[diagnosis],
            "all_scores": all_scores,
            "model_version": "stub-v0",
        }


# Global instance (lazy load)
plant_disease_model = PlantDiseaseModel()
