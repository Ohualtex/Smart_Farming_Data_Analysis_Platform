# Akilli Tarim Veri Analizi Platformu (SFDAP) - Hafta 1 Analiz Raporu

**Hazirlayan:** Emirhan Gunay
**Gorev:** Proje Amaci, Kapsami ve Veri Kaynaklari Analizi
**Tarih:** 08.03.2026

---

## 1. Proje Vizyonu ve Stratejik Amaclar
Bu proje, geleneksel tarim pratiklerini modern veri bilimi ve IoT ekosistemiyle birlestirerek "Hassas Tarim" (Precision Agriculture) disiplinini hayata gecirmeyi amaclar. Temel vizyonumuz, ciftcilerin sezgisel kararlar yerine veriye dayali kararlar almasini saglayarak tarimsal verimliligi dijital bir seviyeye tasimaktir.

### Stratejik Hedefler:
* **Kaynak Optimizasyonu:** Toprak nem ve sicaklik sensorlerinden gelen verileri anlik analiz ederek gereksiz sulamayi onlemek ve su kaynaklarinda %30 tasarruf saglamak.
* **Yapay Zeka Destekli Erken Uyari:** Derin ogrenme modelleri ile bitki yapraklarindaki hastalik belirtilerini henüz baslangic asamasindayken tespit edip mahsul kaybini minimize etmek.
* **Karar Destek Sistemi:** Ciftcilere sulama, gubreleme ve hasat zamanlamasi konularinda bilimsel veriye dayali rehberlik sunmak.

---

## 2. Teknik Kapsam ve Sistem Mimarisi
SFDAP, uc-uca bir veri isleme hatti (Data Pipeline) olarak tasarlanmistir. Sistem su dort ana katmandan olusmaktadir:

* **Veri Toplama (IoT & API):** Saha sensorlerinden (nem, pH, sicaklik) gelen canli verilerin ve harici meteoroloji servislerinin (OpenWeatherMap) sisteme entegrasyonu.
* **Veri Yonetimi (Backend):** Ham verilerin temizlenmesi, islenmesi ve SQL tabanli veritabanlarinda yapilandirilmis halde saklanmasi.
* **Analiz Katmani (AI & ML):** TensorFlow kullanilarak egitilen modellerin bitki sagligi analizleri yapmasi ve gelecek donem risk tahminleri uretmesi.
* **Gorsellestirme (Frontend):** Karmasik verilerin ciftciler tarafindan kolayca anlasilabilecek isi haritalarina, grafiklere ve anlik bildirimlere donusturulmesi.

---

## 3. Kullanilacak Kritik Veri Kaynaklari
Platformun analiz gucu, asagidaki yuksek kaliteli veri setlerinden ve servislerden beslenecektir:

| Veri Kategorisi | Kaynak / Arac | Kullanim Amaci |
| :--- | :--- | :--- |
| **Meteoroloji** | OpenWeatherMap API | Yagis tahmini, don riski ve nem dengesi analizi. |
| **Bitki Sagligi** | PlantVillage (Kaggle) | 50.000+ etiketli gorsel ile hastalik tespit modelinin egitilmesi. |
| **Saha Verileri** | IoT Sensor Simulasyonu | Gercek zamanli toprak nemi, sicakligi ve pH takibi. |
| **Analiz Araclari** | TensorFlow & Pandas | Derin ogrenme modelleri ve veri manipulasyonu. |

---

## 4. Beklenen Somut Sonuclar (KPI)
Proje sureci sonunda asagidaki basari kriterlerine ulasilmasi hedeflenmektedir:
1. **Maliyet Yonetimi:** Veriye dayali gubreleme ve sulama sayesinde operasyonel maliyetlerde %25 oraninda azalma.
2. **Yuksek Dogruluk:** Bitki hastaliklari siniflandirma modelinde minimum %90 dogruluk payi.
3. **Surdurulebilirlik:** Gereksiz ilac kullaniminin onune gecilerek toprak kalitesinin korunmasi ve cevre dostu uretim.
4. **Erisilebilirlik:** Teknik bilgisi sinirli kullanicilarin bile kolayca kullanabilecegi sade bir yonetim paneli.
