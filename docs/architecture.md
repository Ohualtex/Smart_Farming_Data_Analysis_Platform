# 🏗️ SFDAP — Sistem Mimarisi

> Bu döküman SFDAP'ın yapı taşlarını ve veri akışını teknik kişiler için
> detaylandırır. README'deki mermaid diyagramının açıklamalı versiyonu.

---

## 📐 Üst Düzey Mimari

```mermaid
graph TB
    subgraph "İstemci Katmanı"
        Browser[🌐 Tarayıcı / Mobil]
        Sensor[📡 IoT Sensörler<br/>Cycle 7+]
        ExtAPI[🌤️ OpenWeatherMap API]
    end

    subgraph "Sunucu Katmanı (FastAPI)"
        Static[Static SPA<br/>frontend/index.html]
        Auth[🔐 Auth Middleware<br/>X-API-Key + JWT]
        RateLimit[🚦 SlowAPI Rate Limiter]
        ReqLog[📝 Request Logger]
        Routers[11 Router<br/>41 Endpoint]
        Services[İş Mantığı<br/>weather, fertilizer, ml_eval]
        Tasks[⏰ APScheduler<br/>Daily weather fetch]
        MQTT[📨 MQTT Listener<br/>Cycle 7]
    end

    subgraph "ML Katmanı"
        Irrigation[🌾 RandomForest<br/>Sulama Tahmini]
        CNN[🦠 CNN<br/>Bitki Hastalığı<br/>Cycle 7]
        Eval[📊 model_eval helpers]
    end

    subgraph "Veri Katmanı"
        DB[(SQLite / PostgreSQL<br/>14 Tablo)]
        Migration[🗄️ Alembic Migration]
        Seed[🌱 Seed Data<br/>81 il × 7500+ kayıt]
    end

    Browser -->|HTTPS| Static
    Browser -->|REST/JSON| RateLimit
    Sensor -->|MQTT| MQTT
    ExtAPI -->|HTTPS| Tasks

    RateLimit --> Auth
    Auth --> ReqLog
    ReqLog --> Routers
    Routers --> Services
    Services --> DB
    Services --> Irrigation
    Services --> CNN
    Tasks --> Services
    MQTT --> DB

    Migration --> DB
    Seed --> DB

    style Browser fill:#3b82f6,color:#fff
    style Sensor fill:#f59e0b,color:#fff
    style DB fill:#22c55e,color:#fff
    style Irrigation fill:#8b5cf6,color:#fff
    style CNN fill:#ef4444,color:#fff
```

---

## 📦 Modül Yapısı

```
app/
├── main.py                    # FastAPI giriş — middleware + router register + lifespan
├── config.py                  # Pydantic-settings (12-factor config)
├── database.py                # SQLAlchemy engine + session + naming convention
│
├── core/
│   └── logger.py              # Loguru kurulumu (LOG_FORMAT=json opsiyonu shiftFinal)
│
├── models/
│   └── models.py              # 14 ORM tablosu (User, Farm, Field, Sensor, ...)
│
├── schemas/
│   └── schemas.py             # 30+ Pydantic request/response modeli
│
├── routers/                   # 11 router, 41 endpoint
│   ├── health.py              # Sığ sağlık (load balancer için)
│   ├── metrics.py             # Derin sağlık (DB+scheduler+ML+freshness+alerts)
│   ├── sensors.py             # Sensör CRUD + readings
│   ├── weather.py             # Hava durumu CRUD + dış API + clean
│   ├── irrigation.py          # ML tahmin + program + auto-log
│   ├── fertilizer.py          # NPK öneri + takvim
│   ├── plants.py              # Bitki sağlığı (URL + CNN multipart)
│   ├── analytics.py           # Toplu istatistik + compare + PDF/Excel export
│   ├── alerts.py              # SystemAlert CRUD (severity filtre)
│   ├── model_performance.py   # Log + summary + timeseries + compare + drift
│   └── auth.py                # Register/login/me/logout (skeleton, Cycle 8 JWT)
│
├── services/                  # İş mantığı
│   ├── weather_service.py     # OpenWeatherMap entegrasyonu + temizleme
│   ├── fertilizer_service.py  # 17 bitki NPK ihtiyaç hesabı
│   ├── report_service.py      # PDF (FPDF) + Excel (openpyxl)
│   ├── data_quality.py        # IQR outlier + missing fill + sensor validation
│   └── mqtt_listener.py       # IoT stream subscriber (Cycle 7 skeleton)
│
├── ml/
│   ├── irrigation_model.py    # RandomForest sulama (sklearn 1.8)
│   ├── plant_disease_model.py # CNN sarıcı (Cycle 7 skeleton, ONNX placeholder)
│   ├── eval.py                # MAE/RMSE/F1/cross-validate helpers
│   └── models/                # *.pkl dosyaları (gitignored)
│
├── middleware/
│   ├── auth.py                # X-API-Key Security
│   ├── rate_limiter.py        # SlowAPI (decorator'lar Cycle 8'de bağlanacak)
│   ├── request_logger.py      # Her isteği loguru'ya yazar
│   └── exceptions.py          # SFDAPError + global handler
│
└── tasks/
    └── scheduler.py           # APScheduler (gece 02:00 hava durumu çek)
```

---

## 🔄 Tipik İstek Akışı

### Senaryo: Çiftçi sulama tahmini istiyor

```mermaid
sequenceDiagram
    participant U as Kullanıcı (Browser)
    participant API as FastAPI
    participant ML as IrrigationOptimizer
    participant DB as SQLite/PostgreSQL

    U->>API: POST /api/irrigation/predict
    Note right of API: RateLimiter ✓
    Note right of API: RequestLogger
    API->>ML: predict(soil_moisture=30, ...)
    ML->>ML: scaler.transform(features)
    ML->>ML: model.predict()
    ML-->>API: 28.4 L
    API->>DB: INSERT ModelPerformanceLog
    API-->>U: {recommended_water_liters: 28.4, ...}
```

### Senaryo: Dashboard ana sayfa açılıyor

```mermaid
sequenceDiagram
    participant U as Tarayıcı
    participant API as FastAPI
    participant DB as DB

    U->>API: GET /dashboard/ → static index.html
    U->>API: GET /api/health (durum kontrolü)
    U->>API: GET /api/sensors/?limit=100
    U->>API: GET /api/weather/
    U->>API: GET /api/analytics/summary?days=30
    Note over API,DB: 5 ayrı sorgu paralel
    API-->>U: JSON response × 5
    U->>U: Chart.js render
    Note over U: Cycle 7+: Filiz boots (3 sn sonra selam)
```

---

## 🗄️ Veri Modeli — 14 ORM Tablosu

```mermaid
erDiagram
    User ||--o{ Farm : owns
    Farm ||--o{ Field : has
    Farm ||--o{ WeatherData : observes
    Farm ||--o{ SystemAlert : triggers
    Field ||--o{ Sensor : contains
    Field ||--o{ IrrigationSchedule : scheduled
    Field ||--o{ SoilAnalysis : tested
    Field ||--o{ CropPlanting : planted
    Field ||--o{ FertilizerRecommendationLog : recommended
    Field ||--o{ PlantHealthImage : photographed
    Sensor ||--o{ SoilMoistureReading : produces
    CropType ||--o{ CropPlanting : species
    CropType ||--o{ FertilizerRecommendationLog : species

    User { int id PK; string email UK; string password_hash; string role }
    Farm { int id PK; int user_id FK; string city; string region; float lat; float lng }
    Field { int id PK; int farm_id FK; float area_hectares; string soil_type; int crop_id FK }
    Sensor { int id PK; int field_id FK; string sensor_type; string serial_number UK; string status }
    SoilMoistureReading { int id PK; int sensor_id FK; datetime ts; float moisture; float temp }
    WeatherData { int id PK; int farm_id FK; datetime recorded_at; float temp; float humidity }
    IrrigationSchedule { int id PK; int field_id FK; datetime scheduled; int duration_min; string status }
    PlantHealthImage { int id PK; int field_id FK; string image_url; string diagnosis; float confidence }
    SystemAlert { int id PK; int farm_id FK; string severity; string message; bool is_resolved }
    ModelPerformanceLog { int id PK; string model_name; text prediction; float accuracy_score }
    SoilAnalysis { int id PK; int field_id FK; float ph; float n; float p; float k }
    CropPlanting { int id PK; int field_id FK; int crop_id FK; date planting_date }
    CropType { int id PK; string name; float ph_min; float ph_max; int growth_days }
    FertilizerRecommendationLog { int id PK; int field_id FK; int crop_id FK; float n_kg; float p_kg; float k_kg }
```

---

## 🔁 Otomatik İş Akışları

### APScheduler periyodik görevler

| Görev | Trigger | Açıklama |
|:--|:--|:--|
| `fetch_daily_weather` | Cron `02:00` | Tüm 81 ilden OpenWeatherMap'e istek + DB'ye yaz |
| `aggregate_old_readings` | Haftalık (Cycle 7+) | 30+ günlük sensör okumalarını günlük özet tabloya taşı |
| `model_drift_check` | Günlük (Cycle 8+) | Tüm aktif modeller için drift endpoint'ini çağır |

### Auto-logging

| Tetikleyici | Hedef Tablo | Notlar |
|:--|:--|:--|
| `POST /api/irrigation/predict` | `ModelPerformanceLog` | model_name='irrigation_rf', input + output JSON |
| `POST /api/plants/health-images/analyze` | `PlantHealthImage` + `ModelPerformanceLog` | (Cycle 7'de plant_disease_cnn auto-log) |

---

## 🔐 Güvenlik Katmanları

```
┌─────────────────────────────────────────────────────────┐
│  1. CORS                  (settings.CORS_ORIGINS)       │
├─────────────────────────────────────────────────────────┤
│  2. Rate Limiter          (slowapi, decorator Cycle 8)  │
├─────────────────────────────────────────────────────────┤
│  3. Request Logger        (loguru, her istek için)      │
├─────────────────────────────────────────────────────────┤
│  4. Auth Middleware                                      │
│     - X-API-Key  (POST/DELETE)                          │
│     - JWT Bearer (Cycle 8'de full)                      │
├─────────────────────────────────────────────────────────┤
│  5. Pydantic Validation   (request body schema)         │
├─────────────────────────────────────────────────────────┤
│  6. SQLAlchemy ORM        (parameterized queries)       │
├─────────────────────────────────────────────────────────┤
│  7. Global Exception      (custom error format)         │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 Deploy Topolojisi (Cycle 8 hedef)

```mermaid
graph LR
    Internet[🌍 İnternet]
    LB[⚖️ Nginx<br/>HTTPS + Reverse Proxy]
    App1[🐍 FastAPI<br/>uvicorn worker 1]
    App2[🐍 FastAPI<br/>uvicorn worker 2]
    App3[🐍 FastAPI<br/>uvicorn worker 3]
    PG[(🐘 PostgreSQL)]
    Redis[(🔴 Redis<br/>Rate limit + JWT blacklist)]
    Sentry[📊 Sentry]
    Prom[📈 Prometheus + Grafana]

    Internet -->|443| LB
    LB --> App1
    LB --> App2
    LB --> App3
    App1 --> PG
    App2 --> PG
    App3 --> PG
    App1 --> Redis
    App1 -.->|err| Sentry
    App1 -.->|metric| Prom
```

---

## 📊 Performans Hedefleri

| Endpoint | Hedef p95 | Mevcut |
|:--|:--:|:--:|
| `GET /api/health` | < 10 ms | ✓ |
| `GET /api/sensors/?limit=100` | < 100 ms | ✓ |
| `GET /api/analytics/summary` | < 500 ms | ⚠️ N+1 sorgu (Cycle 8 fix) |
| `POST /api/irrigation/predict` | < 100 ms | ~50 ms ✓ |
| `GET /api/health/deep` | < 200 ms | ~60 ms ✓ |

---

## 🔮 Cycle 7+ Genişlemeler

```mermaid
graph LR
    subgraph "Mevcut"
        A1[FastAPI Backend]
        A2[Static SPA]
        A3[Sentetik Seed]
    end

    subgraph "Cycle 7"
        B1[CNN Bitki Sağlığı]
        B2[Auth UI]
        B3[İzleme Paneli]
        B4[MQTT IoT Stream]
    end

    subgraph "Cycle 8 (Üretim Core)"
        C1[JWT + bcrypt Auth Backend]
        C2[Alembic Migration]
        C3[Rate Limit Decorator]
        C4[N+1 Fix]
        C5[nginx + Let's Encrypt]
    end

    subgraph "shiftFinal (Cila & Gözlemlenebilirlik bridge)"
        D1[Sentry + Prometheus]
        D2[Frontend Bundling + a11y]
        D3[Backup + DB Pool]
        D4[Edge Tests + Coverage 95%+]
    end

    subgraph "Cycle 9 (Final Teslim)"
        E1[Final Rapor]
        E2[Sunum]
        E3[Test Validasyon]
    end

    A1 --> B1
    A1 --> B2
    A1 --> B4
    A2 --> B3
    B1 --> C1
    B2 --> C1
    B4 --> C2
    C1 --> D1
    C3 --> D1
    C5 --> D2
```

---

## 📚 İlgili Dökümanlar

- [`README.md`](../README.md) — proje genel bakış, kurulum, kullanım
- [`projeakisi.md`](../projeakisi.md) — cycle bazlı görev dağılımı
- [`CONTRIBUTORS.md`](../CONTRIBUTORS.md) — ekip + cycle metrikleri
- [`docs/api/API_Kullanim_Kilavuzu.md`](api/API_Kullanim_Kilavuzu.md) — API kullanım rehberi
- [`docs/demo_script.md`](demo_script.md) — sunum demo senaryosu
