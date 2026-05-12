# SFDAP Sensör Veri Entegrasyon - Hızlı Başlangıç Kılavuzu

## 📌 Dosya Yapısı

```
scripts/
├── sensor_integration.py                    # Ana entegrasyon programı
└── verify_sensor_data.py                    # Veri doğrulama aracı

docs/database/
├── SENSOR_INTEGRATION_DOCUMENTATION.md      # Detaylı dokümantasyon
└── sensor_readme.md                         # Bu dosya
```

---

## 🚀 Hızlı Başlangıç

### 1. Adım: Programı Çalıştır

```bash
cd Smart_Farming_Data_Analysis_Platform
python scripts/sensor_integration.py
```

**Ne Olur?**
- Ham ısıl sensör verisi üretilir (20 satır)
- Veri temizleme ve doğrulama yapılır
- Temizlenmiş veriler veritabanına kaydedilir
- Detaylı rapor gösterilir

**Beklenen Çıktı:**
```
✓ 12 satır başarıyla kaydedildi (%60 tutma oranı)
✓ 8 satır hatalı/eksik bulunup silindi
```

---

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

## 📊 Veri Temizleme Kriterlerine

| Kriter | Aralık | Hatalı Örnekler |
|--------|--------|-----------------|
| **Nem (%)** | 0 - 100 | 150%, -50%, 200% |
| **Sıcaklık (°C)** | -10 - 60 | -99°C, 150°C, 999°C |
| **Timestamp** | Geçerli tarih | - |
| **Eksik Veriler** | YOK | NaN, None |

---

## 🔍 Program Parametreleri

### Nem Verileri
```python
MOISTURE_MIN_PERCENT = 0
MOISTURE_MAX_PERCENT = 100
```

### Sıcaklık Verileri
```python
TEMPERATURE_MIN_C = -10
TEMPERATURE_MAX_C = 60
```

### Ham Veri Sayısı
```bash
python sensor_integration.py  # 20 satır varsayılan
```

**Değiştirmek için:** Kodu düzenle ve `generate_sample_raw_data(40)` çağrı

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

## ⚙️ Konfigürasyon

### Veritabanı Konumu
```python
# sensor_integration.py içinde
DATABASE_PATH = PROJECT_ROOT / "database" / "sfdap.db"
```

### Doğrulama Aralıklarını Değiştirme

```python
# Nem aralığı (default: 0-100%)
MOISTURE_MIN_PERCENT = 0      # min
MOISTURE_MAX_PERCENT = 100    # max

# Sıcaklık aralığı (default: -10 - 60°C)
TEMPERATURE_MIN_C = -10       # min
TEMPERATURE_MAX_C = 60        # max
```

---

## 🐛 Sorun Giderme

### Hata: "Veritabanı dosyası bulunamadı"

**Çözüm:**
```bash
# Veritabanını oluştur
python -c "import sqlite3; sqlite3.connect('database/sfdap.db').close()"

# Programı çalıştır
python scripts/sensor_integration.py
```

### Hata: "Tablo bulunamadı"

**Çözüm:** Şema eksik. Program otomatik olarak yüklemelidir:
```bash
# Şemayı manuel olarak yükle
sqlite3 database/sfdap.db < database/sfdap_schema.sql
```

### Hata: "ModuleNotFoundError: pandas/numpy/sqlalchemy"

**Çözüm:**
```bash
pip install -r requirements.txt
```

---

## 📈 İşlem Adımları (Detaylı)

```
1. VERİ ÜRETİMİ
   └─ 20 satırlık ham sensör verisi
      - 12 satır geçerli
      - 8 satır hatalı/eksik

2. ETL ARDIŞIK DÜZENI
   ├─ Nem temizliği (0-100%)
   ├─ Sıcaklık temizliği (-10-60°C)
   ├─ Timestamp normalizasyonu
   └─ Eksik satırları kaldırma

3. VERITABANINA KAYIT
   ├─ Append modu (var olan veriyi korur)
   ├─ Toplu işlem (hızlı)
   └─ Hata toleransı (satır satır fallback)

4. RAPORLAMA
   ├─ Ham veri istatistikleri
   ├─ Temizleme özeti
   └─ Veritabanı sonuçları
```

---

## 📚 Dosya İçerik Özeti

### sensor_integration.py
**Satır:** ~450 | **Fonksiyon:** 12
**Görevi:** Veri üretme, temizle, kaydetme, raporlama

### verify_sensor_data.py
**Satır:** ~300 | **Fonksiyon:** 8
**Görevi:** Veritabanı doğrulama, istatistik, kalite kontrolü

### SENSOR_INTEGRATION_DOCUMENTATION.md
**Sayfa:** ~15 | **Konular:** Mimarı, detaylar, kaynak kodu

---

## ✅ Kontrol Listesi

- [x] Veritabanı bağlantısı çalışıyor
- [x] Veritabanı şeması yüklü
- [x] Ham veri üretimi başarılı
- [x] ETL temizliği işe yaradı (%60 tutma)
- [x] Veritabanı kayıt %100 başarılı
- [x] Veri kalitesi mükemmel (100%)
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

conn = sqlite3.connect('database/sfdap.db')
df = pd.read_sql_query("SELECT * FROM soil_moisture_readings", conn)
print(df.head(10))
print(df.describe())
```

---

## 🎓 Öğrenme Kaynakları

| Konu | Kaynak |
|------|--------|
| Pandas | [pandas.pydata.org](https://pandas.pydata.org) |
| SQLAlchemy | [sqlalchemy.org](https://www.sqlalchemy.org) |
| SQLite | [sqlite.org](https://www.sqlite.org) |
| ETL | [Wikipedia ETL](https://en.wikipedia.org/wiki/Extract,_transform,_load) |

---

## 📋 Teknik Özellikler

- **Dil:** Python 3.8+
- **Veritabanı:** SQLite 3
- **CLI:** PowerShell / Terminal
- **Platform:** Windows/Linux/macOS

---

## 🎉 Başarı Göstergeleri

Programı başarıyla çalıştırdığınızda:

✅ 12 satırlık geçerli veri
✅ %100 veritabanı başarı
✅ Sıfır eksik değer
✅ Tüm değerler geçerli aralıkta
✅ Mükemmel veri kalitesi

---

## 📝 Sürüm

**v1.0** - 2026-04-08
Durum: ✅ Üretim Hazır

---

**Sorular?** Dokümantasyon dosyasını kontrol edin: `SENSOR_INTEGRATION_DOCUMENTATION.md`
