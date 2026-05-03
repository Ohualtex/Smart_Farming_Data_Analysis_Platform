# 🤖 Makine Öğrenimi (ML) Modelleri Rehberi

Bu belge, sistemde aktif olarak çalışan ve gelecekte eklenecek olan yapay zeka modellerinin teknik çalışma prensiplerini açıklar.

## 💧 1. Sulama Optimizasyon Modeli (`IrrigationOptimizer`)
`app/ml/irrigation_model.py` içerisinde yer alan model, scikit-learn kütüphanesi kullanılarak geliştirilmiş bir **Random Forest Regressor** algoritmasıdır.

### Model Mimarisi
- **Algoritma:** Random Forest Regressor (`n_estimators=100`, `max_depth=10`)
- **Girdi Özellikleri (Features):**
  1. Toprak Nemi (`soil_moisture`)
  2. Toprak Sıcaklığı (`soil_temperature`)
  3. Hava Nemi (`humidity`)
  4. Hava Sıcaklığı (`temperature`)
  5. Yağış Miktarı (`precipitation`)
- **Ölçeklendirme (Scaling):** Tüm özellikler model eğitiminden önce `StandardScaler` kullanılarak normalize edilir.

### Eğitim Verisi (Sentetik)
Şu anda model, proje prototip aşamasında olduğu için `_train_with_synthetic_data` metodu ile çalışma anında üretilen sentetik 1000 adet kayıtlık bir veri seti üzerinde eğitilmektedir. Sentetik veri matematiksel bir formülle (örneğin; düşük nem + yüksek sıcaklık = yüksek su ihtiyacı) oluşturulur.

### Tahmin ve Karar Çıktısı
Modelin `predict()` fonksiyonu şu formatta bir sonuç döndürür:
```json
{
  "recommended_water_liters": 12.5,
  "irrigation_needed": true,
  "confidence": 0.85,
  "message": "Hafif sulama oneriliyor: 12.5 litre."
}
```

## 🦠 2. Bitki Sağlığı Görüntü Analizi (CNN Modeli) — *Skeleton hazır (Cycle 7)*

Cycle 7 kapsamında Ayşe Eslem Çekici tarafından geliştirilen evrişimli sinir ağı (CNN) modelinin **deterministic stub sarıcısı** `app/ml/plant_disease_model.py` içinde halihazırda canlıdır:

### Mevcut Skeleton (shiftSession)
- **Sarıcı sınıf:** `PlantDiseaseClassifier` — hash-bazlı deterministic prediction (gerçek inference için ONNX placeholder).
- **API endpoint'i:** `POST /api/plants/health-images/analyze` (multipart upload). Yüklenen görseli `app/ml/plant_uploads/` altına kaydedip `PlantHealthImage` ve `ModelPerformanceLog` tablolarına yazar.
- **Test kapsamı:** `tests/test_plant_disease_model.py` (deterministic output garantisi + endpoint integration testleri).

### Cycle 7 İçinde Tamamlanacak (Ayşe)
- Gerçek CNN eğitimi (Keras/TensorFlow) → `.onnx` export
- Sınıf etiketleri: "Sağlıklı", "Pas Hastalığı", "Mantar Lekesi", "Kurşuni Küf", vb.
- Test seti accuracy hedefi ≥ %85
- Model dosyası `app/ml/models/plant_disease_cnn.onnx` olarak yüklenir, sarıcı runtime'da `onnxruntime` ile yorumlar.

### Otomatik Loglama
Her tahmin `ModelPerformanceLog` tablosuna yazılır (`model_name='plant_disease_cnn'`). Drift detection endpoint'i (`GET /api/model-performance/drift/plant_disease_cnn`) eşik altı düşüşte otomatik `SystemAlert` üretir.
