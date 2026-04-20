# 🌾 Akıllı Tarım Veri Analizi Platformu (SFDAP)

Çiftçilerin tarımsal verimliliğini en üst düzeye çıkarmak amacıyla toprak sensörleri, hava durumu verileri ve bitki sağlığı görüntülerini entegre bir şekilde analiz eden kapsamlı bir veri analizi ve karar destek platformudur.

[![CI](https://github.com/Ohualtex/Smart_Farming_Data_Analysis_Platform/actions/workflows/ci.yml/badge.svg)](https://github.com/Ohualtex/Smart_Farming_Data_Analysis_Platform/actions)
![Python 3.12+](https://img.shields.io/badge/Python-3.12+-blue)
![Coverage 91%](https://img.shields.io/badge/Coverage-91%25-brightgreen)
![Tests 114](https://img.shields.io/badge/Tests-114%20passed-success)

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
pip install -r requirements-dev.txt   # Geliştirme araçları

# 4. Ortam değişkenlerini ayarla
copy .env.example .env

# 5. Demo verilerini yükle (opsiyonel)
python database/seed_data.py

# 6. API'yi başlat
uvicorn app.main:app --reload
```

API çalışınca şu adreslerde erişebilirsin:
- 📡 **API:** http://localhost:8000
- 📖 **Swagger Docs:** http://localhost:8000/docs
- 📊 **Dashboard:** http://localhost:8000/dashboard

---

## 🌟 Temel Özellikler

| Özellik | Açıklama |
|:--------|:---------|
| 💧 Sulama Optimizasyonu | ML modeli ile toprak nemi ve hava verisi analizi |
| 🌱 Akıllı Gübreleme | NPK analizi bazlı 8 bitki türü için öneri sistemi |
| 🦠 Hastalık Tespiti | CNN modeli ile bitki sağlığı görüntü analizi |
| 📊 Dashboard | Dark tema SPA, Chart.js grafikleri, responsive |
| 🔐 API Güvenliği | API Key auth, rate limiting, request logging |
| 🌤️ Veri Pipeline | Hava durumu veri temizleme ve dönüştürme |
| 🗄️ Migration | Alembic veritabanı migration altyapısı |

---

## 🔐 API Kimlik Doğrulama

Yazma (POST/DELETE) endpoint'leri `X-API-Key` header'ı gerektirir. Okuma (GET) endpoint'leri herkese açıktır.

```bash
curl -X POST http://localhost:8000/api/sensors/ \
  -H "X-API-Key: dev-api-key" \
  -H "Content-Type: application/json" \
  -d '{"field_id": 1, "sensor_type": "soil_moisture", "serial_number": "S-001"}'
```

---

## 📡 API Endpoint'leri

### Health & Root
| Method | Endpoint | Açıklama | Auth |
|:-------|:---------|:---------|:----:|
| GET | `/` | API bilgisi | ❌ |
| GET | `/api/health` | Sistem durumu | ❌ |

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
| POST | `/api/weather/fetch/{farm_id}` | Dış API'den veri çek | ❌ |
| GET | `/api/weather/stats/{farm_id}` | İstatistikler | ❌ |
| POST | `/api/weather/clean` | Veri temizleme | ❌ |

### Sulama (ML)
| Method | Endpoint | Açıklama | Auth |
|:-------|:---------|:---------|:----:|
| POST | `/api/irrigation/predict` | ML sulama tahmini | ❌ |
| GET | `/api/irrigation/schedules` | Sulama takvimi | ❌ |
| POST | `/api/irrigation/schedules` | Sulama planı oluştur | ✅ |

### Gübreleme
| Method | Endpoint | Açıklama | Auth |
|:-------|:---------|:---------|:----:|
| GET | `/api/fertilizer/crops` | Desteklenen bitkiler | ❌ |
| POST | `/api/fertilizer/recommend` | NPK gübreleme önerisi | ❌ |
| POST | `/api/fertilizer/schedules` | Gübreleme takvimi | ❌ |

### Bitki Sağlığı
| Method | Endpoint | Açıklama | Auth |
|:-------|:---------|:---------|:----:|
| GET | `/api/plants/health-images` | Bitki görselleri | ❌ |
| POST | `/api/plants/health-images` | Görsel yükle | ✅ |

---

## 🧪 Test ve Kalite

```bash
# Tüm testleri çalıştır
pytest tests/ -v

# Coverage raporlu
pytest tests/ --cov=app --cov-report=term-missing

# Linting
ruff check app/ tests/
ruff format app/ tests/
```

| Metrik | Değer |
|:-------|:------|
| Toplam Test | 114 |
| Coverage | %91 |
| Linting | Ruff (All checks passed) |
| CI/CD | GitHub Actions (Ruff + Pytest) |

---

## 🛠️ Teknoloji Stack

| Katman | Teknoloji |
|:-------|:---------|
| Backend / API | Python, FastAPI, Uvicorn |
| Veritabanı | SQLAlchemy, SQLite (dev) / PostgreSQL (prod) |
| Migration | Alembic |
| Makine Öğrenimi | Scikit-learn, NumPy, Pandas |
| Veri Doğrulama | Pydantic v2 |
| Güvenlik | SlowAPI (rate limiting), Custom middleware |
| Frontend | HTML5, CSS3, JavaScript, Chart.js |
| HTTP Client | httpx |
| CI/CD | GitHub Actions, Ruff, Pytest |

---

## 📦 Proje Yapısı

```
Smart_Farming_Data_Analysis_Platform/
├── app/
│   ├── main.py              # FastAPI giriş noktası
│   ├── config.py            # Ayar yönetimi (pydantic-settings)
│   ├── database.py          # SQLAlchemy engine & session
│   ├── models/              # ORM modelleri (9 tablo)
│   ├── schemas/             # Pydantic şemaları
│   ├── routers/             # API endpoint'leri
│   │   ├── sensors.py       # Sensör CRUD
│   │   ├── weather.py       # Hava durumu + dış API
│   │   ├── irrigation.py    # ML sulama tahmini
│   │   ├── fertilizer.py    # NPK gübreleme önerisi
│   │   ├── plants.py        # Bitki sağlığı
│   │   └── health.py        # Health check
│   ├── services/            # İş mantığı
│   │   ├── weather_service.py    # Veri pipeline
│   │   └── fertilizer_service.py # Gübreleme hesaplama
│   ├── middleware/           # Güvenlik katmanı
│   │   ├── auth.py          # API Key doğrulama
│   │   ├── exceptions.py    # Custom error handler'lar
│   │   ├── rate_limiter.py  # SlowAPI rate limiting
│   │   └── request_logger.py # Request logging
│   └── ml/
│       └── irrigation_model.py  # RandomForest sulama modeli
├── alembic/                 # DB migration konfigürasyonu
├── database/
│   ├── sfdap_schema.sql     # SQL şeması
│   └── seed_data.py         # Demo veri scripti
├── Ecenur_Uner/
│   └── index.html           # SPA Dashboard
├── tests/                   # 114 test (9 dosya)
├── .github/workflows/       # CI/CD pipeline
├── requirements.txt         # Production bağımlılıkları
├── requirements-dev.txt     # Development bağımlılıkları
├── pyproject.toml           # Proje konfigürasyonu
└── .env.example             # Ortam değişkenleri şablonu
```

---

## 👥 Ekip

| Üye | Görev Alanı |
|:----|:-----------|
| Miraç Duran | Proje yönetimi, teknoloji araştırması, integration testler |
| Ayşe Eslem Çekici | UI/UX wireframe, gübreleme servisi |
| Ecenur Üner | Dashboard, veri görselleştirme |
| Emirhan Günay | Veritabanı tasarımı, sensör entegrasyonu, seed data |
| Mehmet Sait Tayşı | API geliştirme, güvenlik, rate limiting |

---

## 📋 Sprint Planı

| Cycle | Tarih | Durum |
|:------|:------|:-----:|
| Cycle 1 | 5 – 12 Mart | ✅ Tamamlandı |
| Cycle 2 | 12 – 21 Mart | ✅ Tamamlandı |
| Cycle 3 | 21 Mart – 2 Nisan | ✅ Tamamlandı |
| Cycle 4 | 2 – 13 Nisan | ✅ Tamamlandı |
| Cycle 5 | 13 – 30 Nisan | ✅ Tamamlandı |

Detaylı görev dağılımı için [projeakisi.md](projeakisi.md) dosyasına bakınız.
