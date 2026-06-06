# Makine Öğrenimi Modeli Değerlendirme ve Optimizasyon Raporu

**Proje:** SFDAP — Akıllı Tarım Veri Analizi Platformu
**Görev:** Model Değerlendirme ve Optimizasyon
**Değerlendirilen Model:** Sulama Optimizasyon Modeli (`app/ml/irrigation_model.py`)

---

## 1. Giriş

`IrrigationOptimizer` sınıfı, toprak nemi, toprak sıcaklığı, hava nemi, hava sıcaklığı ve yağış miktarı verilerini kullanarak gereken sulama miktarını (litre) tahmin eden bir RandomForestRegressor modeli içerir. Bu raporda söz konusu modelin performansı ölçülmüş, farklı algoritmalarla karşılaştırılmış ve parametre optimizasyonu yapılmıştır.

---

## 2. Kullanılan Veri

İlk eğitimle aynı synthetic veri yapısı kullanılmıştır:

- **Örnek sayısı:** 1000
- **Özellik sayısı:** 5
- **Eğitim / Test ayrımı:** %80 / %20 (800 eğitim, 200 test)
- **Özellikler:** `soil_moisture`, `soil_temp`, `humidity`, `air_temp`, `precipitation`
- **Hedef değişken:** `water_needed` (litre)

---

## 3. Algoritma Karşılaştırması

Baseline RandomForest modelinin yanı sıra 4 farklı algoritma daha test edilmiştir:

| Model | MAE | RMSE | R² | CV R² |
|---|---|---|---|---|
| **GradientBoosting** | **3.1387** | **6.3068** | **0.9234** | **0.9069** |
| RandomForest (baseline) | 3.5351 | 6.9893 | 0.9059 | 0.8967 |
| DecisionTree | 3.8456 | 8.6613 | 0.8554 | 0.7292 |
| Ridge | 10.9678 | 15.8246 | 0.5174 | 0.4697 |
| LinearRegression | 10.9697 | 15.8203 | 0.5177 | 0.4696 |

**Metrik Açıklamaları:**
- **MAE:** Tahmin ile gerçek değer arasındaki ortalama fark (litre). Düşük olması iyidir.
- **RMSE:** Büyük hatalara daha duyarlı hata metriği. Düşük olması iyidir.
- **R²:** Modelin veriyi açıklama oranı. 1.0 mükemmel demektir.
- **CV R²:** 5 katlı çapraz doğrulama skoru. Modelin yeni verilere genelleme yeteneğini gösterir.

### Değerlendirme

- **GradientBoosting** en düşük MAE (3.14) ve en yüksek R² (0.92) ile en iyi performansı sergilemiştir.
- **Baseline RandomForest modeli** ikinci sıradadır. R² değeri 0.91 ile güçlü bir performans göstermektedir.
- **LinearRegression ve Ridge** bu veri yapısı için yetersiz kalmıştır (R² ≈ 0.52). Sulama miktarı ile özellikler arasındaki ilişki doğrusal değildir.

---

## 4. RandomForest Parametre Optimizasyonu

Baseline varsayılan parametreler (`n_estimators=100, max_depth=10`) optimize edilmiştir:

| Parametreler | MAE | RMSE | R² |
|---|---|---|---|
| n=50, depth=5 | 4.2286 | 8.3558 | 0.8655 |
| n=100, depth=10 *(baseline varsayılan)* | 3.5351 | 6.9893 | 0.9059 |
| n=200, depth=10 | 3.5158 | 6.9731 | 0.9063 |
| n=100, depth=15 | 3.5060 | 6.8996 | 0.9083 |
| **n=200, depth=15** | **3.4865** | **6.9062** | **0.9081** |
| n=300, depth=None | 3.5188 | 6.9723 | 0.9063 |

**En iyi parametreler:** `n_estimators=200, max_depth=15`
Bu yapılandırma ile baseline RandomForest MAE değeri **3.5351'den 3.4865'e** düşürülmüştür (%1.4 iyileşme).

---

## 5. Özellik Önemi

| Özellik | Önem (%) |
|---|---|
| soil_moisture (Toprak Nemi) | %38.16 |
| precipitation (Yağış) | %34.00 |
| air_temp (Hava Sıcaklığı) | %20.24 |
| humidity (Hava Nemi) | %6.16 |
| soil_temp (Toprak Sıcaklığı) | %1.44 |

Toprak nemi ve yağış miktarı birlikte modelin kararlarının **%72'sini** belirlemektedir.

---

## 6. Sonuç ve Öneriler

1. **En iyi algoritma GradientBoosting'dir.** Baseline RandomForest modelinin yerini alması önerilebilir.
2. **Cycle 4 RandomForest modeli** parametreleri `n_estimators=200, max_depth=15` olarak güncellenerek performansı artırılabilir.
3. **Toprak nemi ve yağış** en kritik özelliklerdir.
4. Gerçek saha verisi temin edildiğinde modeller yeniden eğitilmeli ve değerlendirme tekrarlanmalıdır.
