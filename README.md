# 🌾 Akıllı Tarım Veri Analizi Platformu (SFDAP)

Çiftçilerin tarımsal verimliliğini en üst düzeye çıkarmak amacıyla toprak sensörleri, hava durumu verileri ve bitki sağlığı görüntülerini entegre bir şekilde analiz eden kapsamlı bir veri analizi ve karar destek platformudur.

---

## 🚀 Hızlı Başlangıç

### Gereksinimler
- Python 3.12+
- Git

### Kurulum

```bash
# 1. Repoyu klonla
git clone https://github.com/Ohualtex/Smart_Farming_Data_Analysis_Platform.git
cd Smart_Farming_Data_Analysis_Platform

# 2. Sanal ortam oluştur
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# 3. Bağımlılıkları yükle
pip install -r requirements.txt

# 4. Ortam değişkenlerini ayarla
copy .env.example .env
# .env dosyasını düzenle

# 5. API'yi başlat
uvicorn app.main:app --reload
```

API çalışınca şu adreslerde erişebilirsin:
- 📡 **API:** http://localhost:8000
- 📖 **Swagger Dokümantasyon:** http://localhost:8000/docs
- 🌾 **Dashboard:** Ecenur_Uner/index.html (tarayıcıda aç)

---

## 🌟 Temel Özellikler

| Özellik | Açıklama |
|:--------|:---------|
| 💧 Sulama Optimizasyonu | ML modeli ile toprak nemi ve hava verisi analizi |
| 🌱 Akıllı Gübreleme | NPK analizi bazlı öneri sistemi |
| 🦠 Hastalık Tespiti | CNN modeli ile bitki sağlığı görüntü analizi |
| 📊 Görselleştirme | Gerçek zamanlı dashboard ve grafikler |
| 🔐 API Güvenliği | API Key tabanlı kimlik doğrulama |
| 🌤️ Veri Pipeline | Hava durumu veri temizleme ve dönüştürme |

---

## 🔐 API Kimlik Doğrulama

Yazma (POST/DELETE) endpoint'leri `X-API-Key` header'ı gerektirir. Okuma (GET) endpoint'leri herkese açıktır.

```bash
# Korumalı endpoint'lere erişim örneği
curl -X POST http://localhost:8000/api/sensors/ \
  -H "X-API-Key: dev-api-key" \
  -H "Content-Type: application/json" \
  -d '{"field_id": 1, "sensor_type": "soil_moisture", "serial_number": "S-001"}'
```

---

## 📡 API Endpoint Listesi

### Health Check
| Method | Endpoint | Açıklama | Auth |
|:-------|:---------|:---------|:----:|
| GET | `/api/health` | Sistem durumu kontrolü | ❌ |

### Sensör Verileri
| Method | Endpoint | Açıklama | Auth |
|:-------|:---------|:---------|:----:|
| GET | `/api/sensors/` | Tüm sensörleri listele | ❌ |
| POST | `/api/sensors/` | Yeni sensör ekle | ✅ |
| GET | `/api/sensors/{id}` | Sensör detayı | ❌ |
| DELETE | `/api/sensors/{id}` | Sensör sil | ✅ |
| POST | `/api/sensors/readings` | Okuma verisi ekle | ✅ |
| GET | `/api/sensors/{id}/readings` | Sensör okumaları | ❌ |

### Hava Durumu
| Method | Endpoint | Açıklama | Auth |
|:-------|:---------|:---------|:----:|
| GET | `/api/weather/` | Hava durumu verileri | ❌ |
| POST | `/api/weather/` | Hava verisi ekle | ✅ |
| GET | `/api/weather/latest/{farm_id}` | Son hava durumu | ❌ |
| POST | `/api/weather/fetch/{farm_id}` | **Dış API'den veri çek** | ❌ |
| GET | `/api/weather/stats/{farm_id}` | **İstatistikler** | ❌ |
| POST | `/api/weather/clean` | **Veri temizleme testi** | ❌ |

### Sulama Optimizasyonu (ML)
| Method | Endpoint | Açıklama | Auth |
|:-------|:---------|:---------|:----:|
| POST | `/api/irrigation/predict` | **ML sulama tahmini** | ❌ |
| GET | `/api/irrigation/schedules` | Sulama takvimi | ❌ |
| POST | `/api/irrigation/schedules` | Sulama planı oluştur | ✅ |

### Bitki Sağlığı
| Method | Endpoint | Açıklama | Auth |
|:-------|:---------|:---------|:----:|
| GET | `/api/plants/health-images` | Bitki görselleri | ❌ |
| POST | `/api/plants/health-images` | Görsel yükle | ✅ |

---

## 🛠️ Kullanılan Teknolojiler

| Katman | Teknoloji |
|:-------|:---------|
| Backend / API | Python, FastAPI, Uvicorn |
| Veritabanı | SQLAlchemy, SQLite (dev) / PostgreSQL (prod) |
| Makine Öğrenimi | Scikit-learn, NumPy, Pandas |
| Veri Doğrulama | Pydantic |
| Frontend | HTML5, CSS3, JavaScript, Chart.js |
| HTTP Client | httpx (dış API entegrasyonu) |
| Versiyon Kontrol | Git, GitHub |

---

## 📦 Proje Yapısı

```
Smart_Farming_Data_Analysis_Platform/
├── app/
│   ├── main.py              # FastAPI giriş noktası
│   ├── config.py            # Ayar yönetimi
│   ├── database.py          # Veritabanı bağlantısı
│   ├── models/              # SQLAlchemy ORM modelleri
│   ├── schemas/             # Pydantic şemaları
│   ├── routers/             # API endpoint'leri
│   ├── services/            # İş mantığı servisleri
│   │   └── weather_service.py  # Hava durumu pipeline
│   ├── middleware/           # Güvenlik katmanı
│   │   └── auth.py          # API Key doğrulama
│   └── ml/                  # Makine öğrenimi modelleri
├── database/
│   └── sfdap_schema.sql     # Veritabanı şeması
├── Ecenur_Uner/
│   └── index.html           # Dashboard arayüzü
├── tests/                   # Test dosyaları
├── requirements.txt         # Python bağımlılıkları
└── .env.example             # Ortam değişkenleri şablonu
```

---

## 📋 Sprint Planı

| Cycle | Tarih | Durum |
|:------|:------|:-----:|
| Cycle 1 | 5 - 12 Mart | ✅ Tamamlandı |
| Cycle 2 | 12 - 21 Mart | ✅ Tamamlandı |
| Cycle 3 | 21 Mart - 2 Nisan | ✅ Tamamlandı |
| Cycle 4 | 2 - 13 Nisan | 🔄 Devam Ediyor |

Detaylı görev dağılımı için [projeakisi.md](projeakisi.md) dosyasına bakınız.

