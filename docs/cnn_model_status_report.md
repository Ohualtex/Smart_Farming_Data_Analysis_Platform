# Bitki Hastalığı Tespit Modeli — Teknik Durum Notu

**Proje:** SFDAP — Akıllı Tarım Veri Analizi Platformu  
**Hafta:** 6  
**Konu:** CNN Tabanlı Bitki Hastalığı Tespit Modeli Durum Değerlendirmesi  
**İlgili Dosya:** `app/ml/plant_decision_model.py`

---

## 1. Mevcut Durum

`PlantDiseaseModel` sınıfı iki çalışma moduna sahip olarak tasarlanmıştır:

| Mod | Açıklama | Durum |
|---|---|---|
| **ONNX Modu** | Eğitilmiş CNN modeli ile gerçek inference | Henüz hazır değil |
| **Heuristic Mod** | Renk analizi tabanlı kural-bazlı teşhis | Aktif ve çalışıyor |

Sistem başlatıldığında `app/ml/models/plant_disease_cnn.onnx` dosyası aranmaktadır. Bu dosya henüz mevcut olmadığından model otomatik olarak heuristic moda geçmektedir.

---

## 2. Tespit Edilebilen Hastalıklar

Model şu an 8 sınıfı desteklemektedir:

| Sınıf | Açıklama | Şiddet |
|---|---|---|
| healthy | Sağlıklı yaprak | Yok |
| leaf_spot | Yaprak lekesi | Düşük |
| powdery_mildew | Külleme | Orta |
| rust | Pas hastalığı | Orta |
| blight | Yanıklık | Yüksek |
| mosaic_virus | Mozaik virüsü | Yüksek |
| bacterial_wilt | Bakteriyel solgunluk | Yüksek |
| anthracnose | Antraknoz | Orta |

---

## 3. Model Test Çıktısı

Heuristic modun 4 farklı yaprak görüntüsü senaryosu üzerindeki tahmin sonuçları (ekran görüntüsü: test_output.png):

| Test Senaryosu | Teşhis | Güven Skoru | Şiddet |
|---|---|---|---|
| Sağlıklı Yaprak | healthy | 0.86 | none |
| Yaprak Lekesi | leaf_spot | 0.86 | low |
| Külleme | powdery_mildew | 0.80 | medium |
| Yanıklık | blight | 0.95 | high |

---

## 4. Heuristic Modun Çalışma Mantığı

Model, yaprak görüntüsünü HSV renk uzayına çevirerek şu renk oranlarını analiz eder:

| Renk Sinyali | Eşik | Olası Teşhis |
|---|---|---|
| Beyaz/gri tabaka | %18 üzeri | powdery_mildew |
| Kahverengi leke | %25 üzeri | blight |
| Kahverengi leke | %12-25 arası | leaf_spot |
| Sarı baskın | %18 üzeri | mosaic_virus veya anthracnose |
| Düşük doygunluk | %15 altı | rust |
| Yüksek yeşil oranı | %40 üzeri | healthy |
| Diğer | — | bacterial_wilt |

---

## 5. Performans Metrikleri

CNN modeli henüz eğitilmediğinden gerçek metrikler hesaplanamamaktadır:

| Metrik | Hedef | Mevcut Durum |
|---|---|---|
| Accuracy | %90 ve üzeri | Ölçülemiyor (ONNX eksik) |
| Precision | %88 ve üzeri | Ölçülemiyor (ONNX eksik) |
| Recall | %88 ve üzeri | Ölçülemiyor (ONNX eksik) |
| Confusion Matrix | — | Ölçülemiyor (ONNX eksik) |

---

## 6. Mevcut Sınırlar

1. **ONNX modeli eksik:** plant_disease_cnn.onnx dosyası henüz üretilmemiştir.
2. **Heuristic modun yetersizliği:** Renk tabanlı analiz yalnızca belirgin renk farklılıklarında doğru çalışır. Erken evre hastalıklar ve düşük ışık koşullarında hatalı teşhis riski yüksektir.
3. **Çoklu hastalık desteği yok:** Model bir görüntüde yalnızca tek bir hastalık sınıfı döndürmektedir.
4. **Bitki türü ayrımı yok:** Tüm bitki türleri için aynı model kullanılmaktadır.
5. **Veri seti bağımlılığı:** PlantVillage veri seti laboratuvar koşullarında çekilmiş görüntüler içermektedir. Gerçek saha görüntüleri ile performans düşebilir.

---

## 7. İlerleyen Sprintler İçin Açık Adımlar

- PlantVillage veri seti ile TensorFlow/Keras CNN modelinin eğitilmesi
- Eğitilen modelin ONNX formatına export edilmesi (plant_disease_cnn.onnx)
- app/ml/models/ klasörüne ONNX dosyasının eklenmesi
- ONNX modu aktifken accuracy, precision, recall ve confusion matrix hesaplanması
- Test görüntüleri üzerinde gerçek tahmin çıktılarının belgelenmesi
- Bitki türüne göre özelleştirilmiş model desteğinin araştırılması

---

## 8. Sonuç

CNN tabanlı bitki hastalığı tespit modeli mimari olarak tamamlanmış ve sisteme entegre edilmiştir. Model, ONNX dosyası hazır olduğunda otomatik olarak gerçek CNN inference moduna geçecek şekilde tasarlanmıştır. Mevcut heuristic mod, CNN eğitimi tamamlanana kadar geçici bir çözüm olarak işlev görmektedir. Projenin ilerleyen sprintlerinde PlantVillage veri seti ile model eğitiminin tamamlanması öncelikli hedef olarak belirlenmiştir.