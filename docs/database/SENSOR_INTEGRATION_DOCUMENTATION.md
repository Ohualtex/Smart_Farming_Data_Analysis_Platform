# SFDAP Sensör Veri Entegrasyon Modülü - Dokümantasyon

> Bu dosya, sensör veri entegrasyonu için **tek başvuru kaynağıdır**: hem detaylı
> mimari/teknik dokümantasyon hem de hızlı başlangıç kılavuzu burada birleştirilmiştir.

## 📋 Proje Özeti

**Proje Adı:** Smart Farming Data Analysis Platform (SFDAP) — Sensör Veri Entegrasyonu
**Modül:** Toprak Nem Sensörleri Veri Temizleme & Veritabanına Kayıt
**Ana Betik:** `scripts/sensor_integration.py`
**Doğrulama Aracı:** `scripts/verify_sensor_data.py`

---

## 🎯 Hedef ve Gereksinimler

### Ana Hedefler
1. ✅ **Bağlantı:** SQLite veritabanı (`database/sfdap.db`) bağlantısı kurulması
2. ✅ **Veri Üretimi:** 20 satırlık örnek ham sensör verisi oluşturulması
3. ✅ **Veri Temizleme:** ETL sürecinin uygulanması
4. ✅ **Veritabanı Kayıt:** Temizlenmiş veriyi append moduyla kaydetme
5. ✅ **Raporlama:** Detaylı işlem raporlaması

### Teknik Gereksinimler
- **Kütüphaneler:** Pandas, NumPy, SQLAlchemy
- **Veritabanı:** SQLite (`database/sfdap.db`)
- **Tablo:** `soil_moisture_readings`
- **Python Sürümü:** 3.8+
- **Platform:** Windows / Linux / macOS

---

## 🗄️ Veritabanı Şeması Uyumu

ETL betiği, ORM modeli `app.models.models.SoilMoistureReading` ile birebir aynı
`soil_moisture_readings` tablosuna yazar. Tablo alanları:

| Sütun | Tip | Açıklama |
|-------|-----|----------|
| `id` | Integer (PK) | Otomatik artan birincil anahtar |
| `sensor_id` | Integer (FK → `sensors.id`) | İlgili sensör (zorunlu) |
| `reading_timestamp` | DateTime | Ölçüm zamanı (varsayılan: UTC now) |
| `moisture_percent` | Float | Toprak nem yüzdesi (zorunlu) |
| `depth_cm` | Float | Ölçüm derinliği (cm) |
| `soil_temperature_c` | Float | Toprak sıcaklığı (°C) |
| `electrical_conductivity` | Float | Elektriksel iletkenlik (dS/m) |

> Not: Sensörlerin kendileri `sensors` tablosunda tutulur
> (`field_id`, `sensor_type`, `serial_number`, `depth_cm`, `lat`, `lng`, `status`).
> 30 günden eski okumalar `sensor_reading_monthly_aggregates` tablosuna periyodik
> olarak özetlenir (bkz. `app.models.models.SensorReadingMonthlyAggregate`).

### REST API ile İlişki

Bu ETL betiği toplu/offline veri yükleme içindir. Aynı tabloya canlı erişim
`app/routers/sensors.py` üzerinden `/api/sensors` ön ekiyle sağlanır
(rol-aware RBAC; tüm uçlar Bearer JWT ister):

- `GET /api/sensors/` — sensörleri listele (rol-aware sayfalama)
- `GET /api/sensors/{sensor_id}` — tek sensör detayı
- `POST /api/sensors/` — sensör ekle (farmer + admin)
- `DELETE /api/sensors/{sensor_id}` — sensör sil (farmer + admin)
- `POST /api/sensors/readings` — okuma kaydet
- `GET /api/sensors/{sensor_id}/readings` — sensör okumalarını listele

---

## 📊 Program Mimarisi

### 1. Modüler Yapı

```
sensor_integration.py
├── Kütüphane İthalatları
├── Sabitler ve Konfigürasyon
├── VERİ ÜRETİMİ (Data Generation)
│   └── generate_sample_raw_data()
├── VERİ TEMİZLEME (Data Cleaning - ETL)
│   ├── clean_moisture_data()
│   ├── clean_temperature_data()
│   ├── clean_timestamp_data()
│   ├── remove_incomplete_rows()
│   └── execute_etl_pipeline()
├── VERİTABANI İŞLEMLERİ (Database Operations)
│   ├── ensure_database_exists()
│   ├── save_data_to_database()
│   └── insert_data_row_by_row()
├── RAPORLAMA (Reporting)
│   ├── print_data_summary()
│   └── print_database_results()
└── ANA PROGRAM (main())
```

### 2. Kod İlkeleri

- ✅ **Clean Code:** Her fonksiyonun tek bir sorumluluğu (SRP)
- ✅ **Modülerlik:** Fonksiyonlar tekrar kullanılabilir ve test edilebilir
- ✅ **Docstring:** Her fonksiyonun kapsamlı dokümantasyonu
- ✅ **Hata Yönetimi:** Try-except blokları ile güvenli işlemler
- ✅ **Türkçe Yorumlar:** Anlaşılabilirlik için Türkçe açıklamalar

---

## 🔄 Veri İşleme Akışı

### Adım 1: Ham Veri Üretimi (Data Generation)
```python
def generate_sample_raw_data(num_records: int = 20) -> pd.DataFrame
```

**Üretilen Veriler:**
- **Nem Değerleri:** Geçerli (%30-90), Hatalı (%150, -50), Eksik (NaN)
- **Sıcaklık Değerleri:** Geçerli (20-26°C), Hatalı (-99°C, 150°C, 999°C), Eksik (NaN)
- **Timestamp (`reading_timestamp`):** Güncel tarih/saatler (saatlik geriye doğru)
- **Sensör ID (`sensor_id`):** 1-4 arası rastgele (`np.random.randint(1, 5)`)
- **Derinlik (`depth_cm`):** 15, 30, 45, 60 cm
- **Elektriksel İletkenlik (`electrical_conductivity`):** 0.8-4.0 dS/m arası

### Adım 2: Veri Temizleme (ETL Pipeline)

#### a) Nem Verileri Temizleme
```python
MOISTURE_MIN_PERCENT = 0
MOISTURE_MAX_PERCENT = 100
```
- %0-100 aralığı dışında olan değerler → NaN
- Hatalı örnek: 150%, -50%, 200% → NaN

#### b) Sıcaklık Verileri Temizleme
```python
TEMPERATURE_MIN_C = -10
TEMPERATURE_MAX_C = 60
```
- Gerçekçi toprak sıcaklığı aralığı: -10°C ile 60°C
- Hatalı örnek: -99°C, 150°C, 999°C → NaN

#### c) Timestamp Temizleme
- `reading_timestamp` sütununu datetime'a dönüştür (`errors="coerce"`)
- Eksik zaman damgalarını şimdiki zamana (UTC now) ayarla

#### d) Eksik Satırları Kaldırma
Kritik alanlar eksik olan satırlar silinir:
`sensor_id`, `moisture_percent`, `soil_temperature_c`

### Adım 3: Veritabanına Kayıt
```python
df.to_sql(
    "soil_moisture_readings",
    con=engine,
    if_exists="append",  # Mevcut veriyi korur
    index=False,
    method="multi",       # Toplu ekleme
)
```
Toplu kayıt başarısız olursa `insert_data_row_by_row()` ile satır satır fallback yapılır.

### Adım 4: Raporlama
- Ham veri istatistikleri
- Temizleme işlemi detayları
- Veritabanı kayıt sonuçları

---

## 🚀 Hızlı Başlangıç

### 1. Adım: Programı Çalıştır

```bash
cd Smart_Farming_Data_Analysis_Platform
python scripts/sensor_integration.py
```

**Ne Olur?**
- Ham sensör verisi üretilir (20 satır)
- Veri temizleme ve doğrulama yapılır
- Temizlenmiş veriler veritabanına kaydedilir
- Detaylı rapor gösterilir

**Beklenen Çıktı (özet):**
```
✓ 12 satır başarıyla kaydedildi (%60 tutma oranı)
✓ 8 satır hatalı/eksik bulunup silindi
```

### 2. Adım: Verileri Doğrula

```bash
python scripts/verify_sensor_data.py
```

**Ne Gösterir?**
- Veritabanındaki tüm kayıtlar
- İstatistikler (ortalama, min, max, std. sapma)
- Veri kalitesi kontrolleri
- ⭐ Kalite puanı (ideal: %100)

---

## ✅ Program Çalıştırma Sonuçları

### Örnek Çıktı

```
╔══════════════════════════════════════════════════════════╗
║  SFDAP - SENSÖR VERİ ENTEGRASYON PROGRAMI              ║
║  Toprak Nem Sensörleri Veri Temizleme & Kayıt          ║
╚══════════════════════════════════════════════════════════╝

🔧 Veritabanı ayarlanıyor...
✓ Veritabanı şeması başarıyla yüklendi
✓ Veritabanı hazır

📝 Ham sensör verileri üretiliyor...
✓ 20 satırlık ham veri oluşturuldu

📋 ETL ARDIŞIK DÜZENI BAŞLATILIYOR...
   ├─ Başlangıç satır sayısı: 20
   ├─ ✓ Nem verileri temizlendi
   ├─ ✓ Sıcaklık verileri temizlendi
   ├─ ✓ Timestamp verileri temizlendi
   └─ ✓ Eksik satırlar kaldırıldı (8 satır)

============================================================
📊 VERİ TEMİZLEME RAPORu
============================================================

📥 HAM VERİ İSTATİSTİKLERİ:
   ├─ Toplam satır: 20
   ├─ Eksik nem değerleri: 3
   ├─ Eksik sıcaklık değerleri: 3
   └─ Eksik timestamp değerleri: 0

📤 TEMİZLENMİŞ VERİ İSTATİSTİKLERİ:
   ├─ Başarıyla temizlenen satırlar: 12
   ├─ Hatalı/eksik olması nedeniyle silinen: 8
   ├─ Tutma oranı: %60.0
   └─ Eksik veri yok: ✓

📈 TEMİZLENMİŞ VERİ ÖZET İSTATİSTİKLERİ:
   ├─ Nem (%), ortalama: 53.62
   ├─ Nem (%), min-max: 28.70 - 88.30
   ├─ Sıcaklık (°C), ortalama: 23.22
   ├─ Sıcaklık (°C), min-max: 20.30 - 26.10
   └─ Sensör çeşitliliği: 4 sensör

💾 Temizlenmiş veriler veritabanına kaydediliyor...

============================================================
💾 VERİTABANI KAYIT RAPORu
============================================================

✅ BAŞARILI İŞLEMLER:
   └─ Kayıtlı satır sayısı: 12

📊 ÖZETLEMESİ:
   ├─ Toplam satır: 12
   ├─ Başarı oranı: %100.0
   └─ Veritabanı güncellemesi: ✓ Tamamlandı

============================================================

✅ İŞLEM BAŞARIYLA TAMAMLANDI!
```

### Analiz

| Metrik | Değer | Yorum |
|--------|-------|-------|
| **Başlangıç Satırları** | 20 | Ham veri sayısı |
| **Temizlenen Satırlar** | 12 | Geçerli veriler |
| **Silinmiş Satırlar** | 8 | Hatalı/eksik veriler |
| **Tutma Oranı** | %60.0 | Veri kalitesi göstergesi |
| **Nem Ortalaması** | 53.62% | Gerçekçi toprak nem |
| **Sıcaklık Ortalaması** | 23.22°C | İlişkisel sıcaklık |
| **Sensör Çeşitliliği** | 4 sensör | İyi coğrafi dağılım |
| **Veritabanı Başarısı** | %100 | Hatasız kayıt |

> Değerler örnek/temsilidir; üretim her çalıştırmada rastgele veri ürettiği için
> tam sayılar değişebilir.

---

## 📊 Veri Temizleme Kriterleri

| Kriter | Aralık | Hatalı Örnekler |
|--------|--------|-----------------|
| **Nem (%)** | 0 - 100 | 150%, -50%, 200% |
| **Sıcaklık (°C)** | -10 - 60 | -99°C, 150°C, 999°C |
| **Timestamp** | Geçerli tarih | - |
| **Eksik Veriler** | YOK | NaN, None |

---

## ⚙️ Konfigürasyon

### Veritabanı Konumu
```python
# sensor_integration.py içinde
PROJECT_ROOT = current_dir.parent
DATABASE_PATH = PROJECT_ROOT / "database" / "sfdap.db"
```

### Doğrulama Aralıklarını Değiştirme
```python
# Nem aralığı (varsayılan: 0-100%)
MOISTURE_MIN_PERCENT = 0      # min
MOISTURE_MAX_PERCENT = 100    # max

# Sıcaklık aralığı (varsayılan: -10 - 60°C)
TEMPERATURE_MIN_C = -10       # min
TEMPERATURE_MAX_C = 60        # max
```

### Ham Veri Sayısını Değiştirme
Varsayılan 20 satırdır. Daha fazla üretmek için `main()` içindeki çağrıyı düzenleyin:
```python
raw_data = generate_sample_raw_data(num_records=40)
```

---

## 💾 Veritabanı Sorguları

### Tüm Verileri Görüntüle
```sql
SELECT * FROM soil_moisture_readings ORDER BY reading_timestamp DESC;
```

### İstatistikler
```sql
SELECT
    COUNT(*) as kayit_sayisi,
    AVG(moisture_percent) as ort_nem,
    MIN(moisture_percent) as min_nem,
    MAX(moisture_percent) as max_nem,
    AVG(soil_temperature_c) as ort_sicaklik
FROM soil_moisture_readings;
```

### Sensör Başına Ölçümler
```sql
SELECT sensor_id, COUNT(*) as olcum_sayisi
FROM soil_moisture_readings
GROUP BY sensor_id;
```

### Son 5 Ölçüm
```sql
SELECT * FROM soil_moisture_readings
ORDER BY reading_timestamp DESC
LIMIT 5;
```

---

## 🔍 Hata Yönetimi

### Hata Türleri ve Çözümleri

#### 1. Veritabanı Bağlantı Hatası
```python
except SQLAlchemyError as e:
    print(f"⚠ Veritabanı hatası: {e}")
    # Satır satır kaydetme fallback (insert_data_row_by_row)
```

#### 2. Yol (Path) Hatası
- `pathlib.Path` ile platformlar arası uyumlu yol oluşturma
- `PROJECT_ROOT` referanslı göreli yol kullanımı

#### 3. Veri Tipi Hataları
- Timestamp dönüşümleri: `errors="coerce"` ile tutarsız formatları işle
- NaN işleme: `dropna()` ile eksik satırları kaldır

---

## 🐛 Sorun Giderme

### Hata: "Veritabanı dosyası bulunamadı"
```bash
# Veritabanını oluştur
python -c "import sqlite3; sqlite3.connect('database/sfdap.db').close()"

# Programı çalıştır
python scripts/sensor_integration.py
```

### Hata: "Tablo bulunamadı"
Şema eksik. Program otomatik yüklemelidir; manuel yükleme için:
```bash
sqlite3 database/sfdap.db < database/sfdap_schema.sql
```

### Hata: "ModuleNotFoundError: pandas/numpy/sqlalchemy"
```bash
pip install -r requirements.txt
```

---

## 📈 İşlem Adımları (Detaylı)

```
1. VERİ ÜRETİMİ
   └─ 20 satırlık ham sensör verisi
      - ~12 satır geçerli
      - ~8 satır hatalı/eksik

2. ETL ARDIŞIK DÜZENI
   ├─ Nem temizliği (0-100%)
   ├─ Sıcaklık temizliği (-10-60°C)
   ├─ Timestamp normalizasyonu
   └─ Eksik satırları kaldırma

3. VERİTABANINA KAYIT
   ├─ Append modu (var olan veriyi korur)
   ├─ Toplu işlem (method="multi")
   └─ Hata toleransı (satır satır fallback)

4. RAPORLAMA
   ├─ Ham veri istatistikleri
   ├─ Temizleme özeti
   └─ Veritabanı sonuçları
```

---

## 📚 Betik İçerik Özeti

### sensor_integration.py
**Satır:** ~507 | **Fonksiyon:** 12
**Görevi:** Veri üretme, temizleme, kaydetme, raporlama

### verify_sensor_data.py
**Satır:** ~227 | **Fonksiyon:** 7
**Görevi:** Veritabanı doğrulama, istatistik, kalite kontrolü

---

## ✅ Kontrol Listesi

- [x] Veritabanı bağlantısı çalışıyor
- [x] Veritabanı şeması yüklü
- [x] Ham veri üretimi başarılı
- [x] ETL temizliği işe yaradı (~%60 tutma)
- [x] Veritabanı kaydı başarılı
- [x] Tüm değerler geçerli aralıkta
- [x] Eksik veri yok

---

## 📞 Faydalı Komutlar

### Veritabanı İçeriğini SQLite ile Kontrol Et
```bash
sqlite3 database/sfdap.db
sqlite> SELECT COUNT(*) FROM soil_moisture_readings;
sqlite> .tables
sqlite> .schema soil_moisture_readings
sqlite> .exit
```

### CSV'ye Dışa Aktar
```bash
sqlite3 database/sfdap.db
sqlite> .mode csv
sqlite> .output readings.csv
sqlite> SELECT * FROM soil_moisture_readings;
sqlite> .exit
```

### Python REPL'de Kontrol
```python
import pandas as pd
import sqlite3

conn = sqlite3.connect("database/sfdap.db")
df = pd.read_sql_query("SELECT * FROM soil_moisture_readings", conn)
print(df.head(10))
print(df.describe())
```

---

## 📝 Teknik Detaylar

### Kullanılan Kütüphaneler
```python
import pandas as pd          # Veri işleme
import numpy as np           # Sayısal hesaplamalar
from sqlalchemy import create_engine, text  # Veritabanı
from pathlib import Path     # Dosya yolu yönetimi
from datetime import datetime, timedelta, UTC  # Zaman işlemleri
```

### Performans
- **Veri İşleme:** O(n) karmaşıklık
- **Veritabanı Kayıt:** Toplu işlem (`method="multi"`)
- **Bellek Kullanımı:** DataFrame kopyalama minimize edildi

---

## 📈 Geliştirme Önerileri

### Kısa Vadede
1. **Veri Doğrulama:** JSON şema doğrulaması ekle
2. **Loglama:** `logging` modülü ile kayıt al
3. **Konfigürasyon:** `.env` dosyasından ayarlar oku

### Orta Vadede
1. **Veri Kalitesi:** İstatistiksel anomali tespiti
2. **Hata İyileştirme:** Outlier değerlerini winsorize et
3. **Batch İşleme:** Büyük veri setleri için partition sistemi

### Uzun Vadede
1. **Makine Öğrenmesi:** Anomali tespiti ve tahmin modelleri
2. **Gerçek Zamanlı İşleme:** Kuyruk tabanlı akış entegrasyonu
3. **İzleme:** Metrik/uyarı altyapısı

---

## 📚 Kaynaklar

- [Pandas Documentation](https://pandas.pydata.org/docs/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [SQLite](https://www.sqlite.org/)
- [ETL — Wikipedia](https://en.wikipedia.org/wiki/Extract,_transform,_load)
- [SFDAP Veritabanı Şeması](./sfdap_schema.sql)

---

## ✍️ Sürüm Tarihi

| Sürüm | Tarih | Notlar |
|-------|-------|--------|
| 1.0 | 2026-04-08 | İlk versiyon - Temel ETL fonksiyonları |
| 1.1 | 2026-06-07 | Hızlı başlangıç kılavuzu birleştirildi; güncel kod/şema ile uyumlandı |

---

**Durum:** ✅ Üretim Hazır
