# 🤖 Makine Öğrenimi (ML) Modelleri Rehberi

Bu belge, SFDAP (Akıllı Tarım Veri Analizi Platformu) içerisinde aktif olarak çalışan yapay zeka modellerinin teknik çalışma prensiplerini, performans ölçümlerini ve sınırlarını açıklar. Sistemdeki **tek ML referans dökümanıdır**.

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

### Performans Değerlendirmesi (Sentetik Veri Üzerinde)

Sentetik veri yapısı üzerinde (1000 örnek, %80/%20 eğitim/test ayrımı) yürütülen değerlendirmede aktif RandomForest yapılandırmasının ölçülen metrikleri:

| Metrik | Değer | Açıklama |
|---|---|---|
| MAE | 3.5351 | Tahmin ile gerçek değer arasındaki ortalama fark (litre). Düşük olması iyidir. |
| RMSE | 6.9893 | Büyük hatalara daha duyarlı hata metriği. Düşük olması iyidir. |
| R² | 0.9059 | Modelin veriyi açıklama oranı. 1.0 mükemmel demektir. |
| CV R² | 0.8967 | 5 katlı çapraz doğrulama skoru. Yeni verilere genelleme yeteneğini gösterir. |

> **Not:** Bu metrikler **sentetik** veri üzerinde elde edilmiştir ve gerçek saha performansını yansıtmaz. Gerçek saha verisi temin edildiğinde model yeniden eğitilmeli ve değerlendirme tekrarlanmalıdır.

### Özellik Önemi (Feature Importance)

| Özellik | Önem (%) |
|---|---|
| soil_moisture (Toprak Nemi) | %38.16 |
| precipitation (Yağış) | %34.00 |
| temperature (Hava Sıcaklığı) | %20.24 |
| humidity (Hava Nemi) | %6.16 |
| soil_temperature (Toprak Sıcaklığı) | %1.44 |

Toprak nemi ve yağış miktarı birlikte modelin kararlarının yaklaşık **%72'sini** belirlemektedir.

### Parametre Notları
Sentetik veri üzerinde yapılan parametre denemelerinde `n_estimators=200, max_depth=15` yapılandırması MAE'yi 3.5351'den 3.4865'e (yaklaşık %1.4) marjinal olarak düşürmüştür. Bu fark sentetik veride önemsiz olduğundan, aktif modelde varsayılan `n_estimators=100, max_depth=10` yapılandırması korunmaktadır. Gerçek saha verisiyle yeniden değerlendirme yapılmadan parametre değişikliği önerilmemektedir.

## 🦠 2. Bitki Sağlığı Görüntü Analizi (`PlantDiseaseModel`)

Bitki yaprak görüntülerinden hastalık teşhisi yapan model sarıcısı `app/ml/plant_disease_model.py` içinde canlıdır. Sarıcı iki çalışma moduna sahip olacak şekilde tasarlanmıştır:

| Mod | Açıklama | Durum |
|---|---|---|
| **ONNX Modu** | `onnxruntime` ile gerçek CNN inference | `plant_disease_cnn.onnx` mevcutsa otomatik aktifleşir (şu an dosya yok) |
| **Heuristic Mod** | Pillow tabanlı HSV renk analizi (kural-bazlı teşhis) | Aktif ve çalışıyor |

Sistem başlatıldığında `app/ml/models/plant_disease_cnn.onnx` dosyası aranır. Bu dosya henüz mevcut olmadığından model otomatik olarak heuristic moda geçer. ONNX inference için `onnxruntime`, görüntü işleme için `Pillow` kullanılır. **Bu akışta TensorFlow, Keras, OpenCV veya LSTM kullanılmamaktadır.**

### API Entegrasyonu
- **API endpoint'i:** `POST /api/plants/health-images/analyze` (multipart upload). Yüklenen görseli kaydedip `PlantHealthImage` tablosuna yazar.
- **Test kapsamı:** `tests/test_plants.py` (heuristic ve ONNX path'leri için integration testleri).

### Desteklenen Hastalık Sınıfları

Model şu an 8 sınıfı desteklemektedir:

| Sınıf | Açıklama | Şiddet |
|---|---|---|
| healthy | Sağlıklı yaprak | none |
| leaf_spot | Yaprak lekesi | low |
| powdery_mildew | Külleme | medium |
| rust | Pas hastalığı | medium |
| blight | Yanıklık | high |
| mosaic_virus | Mozaik virüsü | high |
| bacterial_wilt | Bakteriyel solgunluk | high |
| anthracnose | Antraknoz | medium |

### Heuristic Modun Çalışma Mantığı

Model, yaprak görüntüsünü HSV renk uzayına çevirerek (Pillow ile) renk oranlarını analiz eder ve aşağıdaki kurallara göre teşhis üretir:

| Renk Sinyali | Eşik | Olası Teşhis |
|---|---|---|
| Beyaz/gri tabaka | %18 üzeri | powdery_mildew |
| Kahverengi leke | %25 üzeri | blight |
| Kahverengi leke | %12-25 arası | leaf_spot |
| Sarı baskın | %18 üzeri | mosaic_virus veya anthracnose |
| Düşük doygunluk | %15 altı | rust |
| Yüksek yeşil oranı | %40 üzeri | healthy |
| Diğer | — | bacterial_wilt |

### Heuristic Mod Test Çıktısı

Heuristic modun 4 farklı yaprak görüntüsü senaryosu üzerindeki örnek tahmin sonuçları:

| Test Senaryosu | Teşhis | Güven Skoru | Şiddet |
|---|---|---|---|
| Sağlıklı Yaprak | healthy | 0.86 | none |
| Yaprak Lekesi | leaf_spot | 0.86 | low |
| Külleme | powdery_mildew | 0.80 | medium |
| Yanıklık | blight | 0.95 | high |

> Bu güven skorları heuristic (renk oranı) tabanlıdır; eğitilmiş bir CNN'in doğruluk metriği değildir.

### CNN/ONNX Modu — Açık Adımlar

ONNX modu, eğitilmiş bir model dosyası yerleştirildiğinde otomatik olarak devreye girer. CNN eğitimi henüz tamamlanmadığından gerçek accuracy/precision/recall/confusion matrix metrikleri **ölçülememektedir**. İlerleyen sprintler için açık adımlar:

- PlantVillage veri seti ile bir CNN modelinin eğitilmesi
- Eğitilen modelin ONNX formatına export edilmesi (`plant_disease_cnn.onnx`)
- `app/ml/models/` klasörüne ONNX dosyasının eklenmesi
- ONNX modu aktifken accuracy, precision, recall ve confusion matrix hesaplanması
- Test görüntüleri üzerinde gerçek tahmin çıktılarının belgelenmesi
- Bitki türüne göre özelleştirilmiş model desteğinin araştırılması

### Mevcut Sınırlar

1. **ONNX modeli eksik:** `plant_disease_cnn.onnx` dosyası henüz üretilmemiştir; sistem heuristic modda çalışmaktadır.
2. **Heuristic modun yetersizliği:** Renk tabanlı analiz yalnızca belirgin renk farklılıklarında doğru çalışır. Erken evre hastalıklar ve düşük ışık koşullarında hatalı teşhis riski yüksektir.
3. **Çoklu hastalık desteği yok:** Model bir görüntüde yalnızca tek bir hastalık sınıfı döndürür.
4. **Bitki türü ayrımı yok:** Tüm bitki türleri için aynı model kullanılır.
5. **Veri seti bağımlılığı:** PlantVillage veri seti laboratuvar koşullarında çekilmiş görüntüler içerir; gerçek saha görüntüleriyle performans düşebilir.

## 📊 3. Model Performans Loglama ve Drift Tespiti

Şu an `ModelPerformanceLog`'a otomatik yazan tek akış **sulama** tahminleridir (`model_name='irrigation_rf'`, `app/routers/irrigation.py` içinde `_log_prediction`). Bitki hastalığı analizi (`plant_disease`) henüz bu loglamaya bağlanmamıştır — yalnız `PlantHealthImage` kaydı oluşur.

Drift detection endpoint'i (`GET /api/model-performance/drift/{model_name}`) parametriktir; bir modelin log kaydı oluştuğunda eşik altı düşüşte `SystemAlert` üretir. Model performans router'ı (`/api/model-performance`), Bearer JWT yerine legacy `X-API-Key` doğrulaması kullanan tek API yüzeyidir.
