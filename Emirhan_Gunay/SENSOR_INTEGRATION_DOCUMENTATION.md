# SFDAP Sensör Veri Entegrasyon Modülü - Dokümantasyon

## 📋 Proje Özeti

**Proje Adı:** Smart Farming Data Analysis Platform (SFDAP) - Sensör Veri Entegrasyon  
**Modül:** Toprak Nem Sensörleri Veri Temizleme & Veritabanına Kayıt  
**Dosya:** `sensor_integration.py`  
**Tarih:** 2026-04-08  
**Yazar:** Emirhan Gunay

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
- **Veritabanı:** SQLite (sfdap.db)
- **Tablo:** `soil_moisture_readings`
- **Python Sürümü:** 3.8+

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
def generate_sample_raw_data(num_records=20) -> pd.DataFrame
```

**Üretilen Veriler:**
- **Nem Değerleri:** Geçerli (%30-90), Hatalı (%150, -50), Eksik (NaN)
- **Sıcaklık Değerleri:** Geçerli (20-26°C), Hatalı (-99°C, 150°C, 999°C), Eksik (NaN)
- **Timestamp:** Güncel tarih/saatler
- **Sensör ID:** 1-4 arası rastgele
- **Derinlik:** 15, 30, 45, 60 cm

### Adım 2: Veri Temizleme (ETL Pipeline)

#### a) Nem Verileri Temizleme
```python
MOISTURE_MIN_PERCENT = 0
MOISTURE_MAX_PERCENT = 100
```
- %0-100 aralığı dışında olan değerler → NaN
- Hatalı örnek: 150%, -50% → NaN

#### b) Sıcaklık Verileri Temizleme
```python
TEMPERATURE_MIN_C = -10
TEMPERATURE_MAX_C = 60
```
- Gerçekçi toprak sıcaklığı aralığı: -10°C ile 60°C
- Hatalı örnek: -99°C, 150°C, 999°C → NaN

#### c) Timestamp Temizleme
- Timestamp sütununu datetime'a dönüştür
- Eksik zaman damgalarını şimdiki zamana ayarla

#### d) Eksik Satırları Kaldırma
Kritik alanlar (sensor_id, moisture_percent, soil_temperature_c) eksik olanları sil

### Adım 3: Veritabanına Kayıt
```python
df.to_sql(
    'soil_moisture_readings',
    if_exists='append',  # Mevcut veriyi korur
    method='multi'        # Toplu ekleme
)
```

### Adım 4: Raporlama
- Ham veri istatistikleri
- Temizleme işlemi detayları
- Veritabanı kayıt sonuçları

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

---

## 🔍 Hata Yönetimi

### Hata Türleri ve Çözümleri

#### 1. Veritabanı Bağlantı Hatası
```python
except SQLAlchemyError as e:
    print(f"⚠ Veritabanı hatası: {e}")
    # Satır satır kaydetme fallback
```

#### 2. Yol (Path) Hatası
- Windows uyumu: backslash → forward slash dönüşümü
- Relative path kullanımı

#### 3. Veri Tipi Hataları
- Timestamp dönüşümler: `errors='coerce'` ile tutarsız formatları işle
- NaN işleme: `dropna()` ile eksik satırları kaldır

---

## 📈 Geliştirme Önerileri

### Kısa Vadede
1. **Veri Doğrulama:** JSON şema doğrulaması ekle
2. **Loglama:** `logging` modülü ile kayıt al
3. **Konfigürasyon:** `.env` dosyasından ayarlar oku

### Orta Vadede
1. **Veri Kalitesi:** İstatistiksel anomali tespiti
2. **Hata İyileştirme:** Outlier değerlerini düzümü/winsorize et
3. **Batch İşleme:** Büyük veri setleri için partition sistemi

### Uzun Vadede
1. **Makine Öğrenmesi:** Anomali tespiti ve tahmin modelleri
2. **Gerçek Zamanlı İşleme:** Kafka/RabbitMQ entegrasyonu
3. **Monitöring:** ELK Stack veya Prometheus uyarıları

---

## 🚀 Kullanım

### Çalıştırma

```bash
cd Smart_Farming_Data_Analysis_Platform
python Emirhan_Gunay/sensor_integration.py
```

### Çıktı Dosyaları

- **Veritabanı:** `database/sfdap.db`
- **Tablo:** `soil_moisture_readings`

### Veritabanı Sorgusu (Kontrol)

```sql
SELECT COUNT(*) as kayit_sayisi FROM soil_moisture_readings;
SELECT AVG(moisture_percent) as ort_nem FROM soil_moisture_readings;
SELECT * FROM soil_moisture_readings ORDER BY reading_timestamp DESC LIMIT 5;
```

---

## 📝 Teknik Detaylar

### Kullanılan Kütüphaneler

```python
import pandas as pd          # Veri işleme
import numpy as np          # Sayısal hesaplamalar  
from sqlalchemy import create_engine, text  # Veritabanı
from pathlib import Path    # Dosya yolu yönetimi
from datetime import datetime, timedelta  # Zaman işlemleri
```

### Tasarım Kalıpları

1. **Builder Pattern:** ETL pipeline yapısı
2. **Strategy Pattern:** Farklı temizleme stratejileri
3. **Error Handler Pattern:** Hata yönetimi

### Performans

- **Veri İşleme:** O(n) karmaşıklık
- **Veritabanı Kayıt:** Toplu işlem (method='multi')
- **Bellek Kullanımı:** DataFrame kopyalama minimize edildi

---

## ✨ Öne Çıkan Özellikler

### 1. Kapsamlı Temizleme
- Nem değerleri doğrulanması
- Sıcaklık değerleri doğrulanması
- Timestamp normalizasyonu
- Eksik veri yönetimi

### 2. Detaylı Raporlama
- Ham veri istatistikleri
- Temizleme öncesi/sonrası karşılaştırma
- Veritabanı işlem sonuçları
- Görsel çıktı (emoji, çizgiler)

### 3. Hata Toleransı
- Kısmi başarı durumunda satır satır kaydetme
- Bağlantı hatalarında fallback mekanizması
- Kullanıcı tarafından durdurulabilirlik

### 4. Ölçeklenebilirlik
- Modüler fonksiyonlar
- Parameterize edilebilir sabitler
- Batch işleme desteği

---

## 📚 Kaynaklar

- [Pandas Documentation](https://pandas.pydata.org/docs/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Clean Code Principles](https://en.wikipedia.org/wiki/Code_smell)
- [SFDAP Veritabanı Şeması](../database/sfdap_schema.sql)

---

## ✍️ Sürüm Tarihi

| Sürüm | Tarih | Notlar |
|-------|-------|--------|
| 1.0 | 2026-04-08 | İlk versiyon - Temel ETL fonksiyonları |

---

**Son Güncelleme:** 2026-04-08  
**Durum:** ✅ Üretim Hazır
