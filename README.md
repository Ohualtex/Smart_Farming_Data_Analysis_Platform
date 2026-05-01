# 🌾 Akıllı Tarım Veri Analizi Platformu (SFDAP)

Çiftçilerin tarımsal verimliliğini en üst düzeye çıkarmak amacıyla toprak sensörleri, hava durumu verileri ve bitki sağlığı görüntülerini entegre bir şekilde analiz eden kapsamlı bir veri analizi ve karar destek platformudur.

[![CI](https://github.com/Ohualtex/Smart_Farming_Data_Analysis_Platform/actions/workflows/ci.yml/badge.svg)](https://github.com/Ohualtex/Smart_Farming_Data_Analysis_Platform/actions)
![Python 3.9+](https://img.shields.io/badge/Python-3.9+-blue)
![Coverage 91%](https://img.shields.io/badge/Coverage-91%25-brightgreen)
![Tests 124](https://img.shields.io/badge/Tests-124%20passed-success)

---

## 🚀 Hızlı Başlangıç

### Gereksinimler
- Python 3.9+
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

# 6. API'yi başlat (Klasik Yöntem)
uvicorn app.main:app --reload

# VEYA Makefile ile (Önerilen)
make run

# VEYA Docker ile (Sadece Docker yüklüyse)
make docker-up
```

API çalışınca şu adreslerde erişebilirsin:
- 📡 **API:** http://localhost:8000
- 📖 **Swagger Docs:** http://localhost:8000/docs
- 📊 **Dashboard:** http://localhost:8000/dashboard

---

## 🌟 Temel Özellikler

| Özellik | Açıklama |
|:--------|:---------|
| 🌍 Ulusal Ölçek | Tüm Türkiye (81 il) için 7500+ kayıtlık mega veritabanı |
| 💧 Sulama Optimizasyonu | ML modeli ile toprak nemi ve hava verisi analizi |
| 🌱 Akıllı Gübreleme | NPK analizi ve toprak yapısı bazlı 15 bitki türü için öneri sistemi |
| 🦠 Hastalık Tespiti | CNN modeli ile bitki sağlığı görüntü analizi |
| 📊 Dashboard | Dark tema SPA, Chart.js grafikleri, responsive |
| 📈 Analitik Panosu | Bölge bazlı gruplanmış (7 bölge) veri görselleştirme ve içgörü |
| 🔐 API Güvenliği | API Key auth, rate limiting, request logging |
| 🌤️ Veri Pipeline | Hava durumu veri temizleme ve dönüştürme |
| 🗄️ Migration | Alembic veritabanı migration altyapısı (12 Tablo) |

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

### Analitik & Görselleştirme
| Method | Endpoint | Açıklama | Auth |
|:-------|:---------|:---------|:----:|
| GET | `/api/analytics/summary` | Toplu istatistik ve içgörü verileri | ❌ |
| GET | `/api/analytics/compare` | İki farklı tarih aralığını karşılaştırır | ❌ |
| GET | `/api/analytics/export` | Raporu PDF veya Excel formatında indirir | ❌ |

> `days` query parametresi ile süre filtrelenebilir (varsayılan: 30 gün). Sensör dağılımı, çiftlik bazlı hava karşılaştırması, sulama durumu, günlük trendler, NPK profilleri ve sensör okuma istatistiklerini döndürür.

---

## 🧪 Test ve Kalite

Makefile komutları ile tüm işlemleri kolayca yapabilirsiniz:

```bash
# Tüm testleri çalıştır (Coverage raporlu)
make test

# Linting ve Format Kontrolü
make lint
make format
```

| Metrik | Değer |
|:-------|:------|
| Toplam Test | 124 |
| Coverage | %91+ |
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
├── app/                         # Ana uygulama (FastAPI)
│   ├── main.py                  #   Giriş noktası & middleware konfigürasyonu
│   ├── config.py                #   Ayar yönetimi (pydantic-settings)
│   ├── database.py              #   SQLAlchemy engine & session
│   ├── core/                    #   Logger konfigürasyonu
│   ├── models/                  #   ORM modelleri (12 tablo)
│   ├── schemas/                 #   Pydantic veri doğrulama şemaları
│   ├── routers/                 #   API endpoint'leri
│   │   ├── sensors.py           #     Sensör CRUD
│   │   ├── weather.py           #     Hava durumu + dış API
│   │   ├── irrigation.py        #     ML sulama tahmini
│   │   ├── fertilizer.py        #     NPK gübreleme önerisi
│   │   ├── plants.py            #     Bitki sağlığı
│   │   ├── analytics.py         #     Analitik & görselleştirme verileri
│   │   └── health.py            #     Health check
│   ├── services/                #   İş mantığı katmanı
│   │   ├── weather_service.py   #     Hava durumu veri pipeline
│   │   └── fertilizer_service.py#     Gübreleme hesaplama motoru
│   ├── middleware/              #   Güvenlik & izleme katmanı
│   │   ├── auth.py              #     API Key doğrulama
│   │   ├── exceptions.py        #     Global exception handler (6 sınıf)
│   │   ├── rate_limiter.py      #     SlowAPI rate limiting
│   │   └── request_logger.py    #     Request logging
│   ├── ml/                      #   Makine öğrenimi modülleri
│   │   ├── irrigation_model.py  #     RandomForest sulama modeli
│   │   └── models/              #     Eğitilmiş model dosyaları (.pkl)
│   └── tasks/
│       └── scheduler.py         #   APScheduler periyodik görevler
│
├── frontend/                    # Web arayüzü (SPA Dashboard)
│   └── index.html               #   Dark mode, responsive, Chart.js (6 sayfa)
│
├── database/                    # Veritabanı yönetimi
│   ├── sfdap_schema.sql         #   SQL şeması
│   ├── seed_data.py             #   81 il kapsamlı mega seed data
│   └── turkey_data.py           #   Türkiye il/bölge/bitki referans verisi
│
├── alembic/                     # DB migration sistemi
├── tests/                       # 124 test (10 dosya, %91+ coverage)
├── .github/workflows/           # CI/CD pipeline (Ruff + Pytest)
│
├── docs/                        # Proje dokümantasyonu
│   ├── wireframes/              #   UI/UX wireframe tasarımları (6 ekran)
│   ├── api/                     #   API kullanım kılavuzu & Postman/Swagger
│   ├── database/                #   Veritabanı şeması & sensör entegrasyonu
│   ├── research/                #   Teknoloji araştırması & veri analizi
│   ├── requirements/            #   Gereksinim belgeleri
│   ├── setup/                   #   Geliştirme ortamı kurulum rehberi
│   └── planning/                #   Veri toplama & görselleştirme planları
│
├── scripts/                     # Yardımcı scriptler & prototipler
│   ├── weather_processing.py    #   Hava durumu veri işleme (bağımsız)
│   ├── sensor_integration.py    #   Sensör entegrasyon scripti
│   ├── verify_sensor_data.py    #   Sensör veri doğrulama
│   └── api_prototype.py         #   Erken dönem API prototipi
│
├── CONTRIBUTORS.md              # Ekip & katkı matrisi
├── projeakisi.md                # Sprint bazlı görev dağılımı
├── requirements.txt             # Production bağımlılıkları
├── requirements-dev.txt         # Development bağımlılıkları
├── pyproject.toml               # Proje konfigürasyonu
└── .env.example                 # Ortam değişkenleri şablonu
```

---

## 👥 Ekip

| Üye | Görev Alanı |
|:----|:-----------|
| Miraç Duran | Proje yönetimi, analitik dashboard, CI/CD, integration testler |
| Ayşe Eslem Çekici | UI/UX wireframe, gübreleme servisi, hava durumu pipeline |
| Ecenur Üner | Dashboard SPA, veri görselleştirme |
| Emirhan Günay | Veritabanı tasarımı, sensör entegrasyonu, seed data |
| Mehmet Sait Tayşı | API geliştirme, güvenlik, rate limiting |

Detaylı katkı matrisi için [CONTRIBUTORS.md](CONTRIBUTORS.md) dosyasına bakınız.

---

## 📋 Sprint Planı

| Cycle | Tarih | Durum |
|:------|:------|:-----:|
| Cycle 1 | 5 – 12 Mart | ✅ Tamamlandı |
| Cycle 2 | 12 – 21 Mart | ✅ Tamamlandı |
| Cycle 3 | 21 Mart – 2 Nisan | ✅ Tamamlandı |
| Cycle 4 | 2 – 13 Nisan | ✅ Tamamlandı |
| Cycle 5 | 13 – 28 Nisan | ✅ Tamamlandı |
| Cycle 6 | 28 Nisan – 3 Mayıs | 🔄 Devam Ediyor |
| Cycle 7 | 4 – 13 Mayıs | ⏳ Planlandı |

Detaylı görev dağılımı için [projeakisi.md](projeakisi.md) dosyasına bakınız.
