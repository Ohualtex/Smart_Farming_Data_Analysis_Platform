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

## 🦠 2. Bitki Sağlığı Görüntü Analizi (CNN Modeli) - *Gelecek Eklenti*
Cycle 7 kapsamında sisteme Ayşe Eslem Çekici tarafından entegre edilecek olan evrişimli sinir ağı (CNN) modelidir.
- Çiftçilerin yüklediği yaprak görsellerini işleyerek "Sağlıklı", "Pas Hastalığı", "Mantar" gibi tespitler yapması planlanmaktadır.
- Modele ait döküman, entegrasyon tamamlandığında bu rehbere eklenecektir.
