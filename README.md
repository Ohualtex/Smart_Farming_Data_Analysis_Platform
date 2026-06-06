# 🌾 SFDAP — Akıllı Tarım Veri Analizi Platformu

Çiftlik sensör verileri, hava durumu, sulama, gübreleme ve bitki sağlığı için entegre bir **veri analizi ve karar destek platformu**. Çiftçi tarlasını izler, doğru zamanda sular, hastalığı erken yakalar; gözetmen ve yönetici sistem geneline bakar.

**Backend:** FastAPI + SQLAlchemy 2.0 · **Frontend:** vanilla JS ESM tek-sayfa SPA + Leaflet harita · **ML:** scikit-learn (sulama) + görüntü-tabanlı bitki sağlığı.

[![CI](https://github.com/Ohualtex/Smart_Farming_Data_Analysis_Platform/actions/workflows/ci.yml/badge.svg)](https://github.com/Ohualtex/Smart_Farming_Data_Analysis_Platform/actions/workflows/ci.yml)
[![Security](https://github.com/Ohualtex/Smart_Farming_Data_Analysis_Platform/actions/workflows/security.yml/badge.svg)](https://github.com/Ohualtex/Smart_Farming_Data_Analysis_Platform/actions/workflows/security.yml)
[![A11y](https://github.com/Ohualtex/Smart_Farming_Data_Analysis_Platform/actions/workflows/a11y.yml/badge.svg)](https://github.com/Ohualtex/Smart_Farming_Data_Analysis_Platform/actions/workflows/a11y.yml)
![Python 3.12+](https://img.shields.io/badge/Python-3.12+-blue)
![Coverage 95%](https://img.shields.io/badge/Coverage-95%25-brightgreen)
![Tests](https://img.shields.io/badge/Tests-650%20backend%20%2B%2059%20frontend-success)
![Version 1.0.0](https://img.shields.io/badge/version-1.0.0-blue)
![License MIT](https://img.shields.io/badge/license-MIT-green)

---

## 📑 İçindekiler

- [Özellikler](#-özellikler)
- [Hızlı Başlangıç](#-hızlı-başlangıç)
- [Demo Hesaplar](#-demo-hesaplar)
- [Teknoloji Yığını](#️-teknoloji-yığını)
- [Kullanıcı Rolleri](#-kullanıcı-rolleri)
- [Mimari](#️-mimari)
- [Proje Yapısı](#-proje-yapısı)
- [Veri Modeli](#-veri-modeli)
- [API](#-api)
- [Test ve Kalite](#-test-ve-kalite)
- [Geliştirme](#-geliştirme)
- [Production Deploy](#-production-deploy)
- [Proje Durumu](#-proje-durumu)
- [Anahtar Dokümanlar](#-anahtar-dokümanlar)
- [Ekip & Lisans](#-ekip)

---

## ✨ Özellikler

| Alan | Yetenek |
|:--|:--|
| 🌱 **Tarla & sensör yönetimi** | Çiftlik → tarla → sensör hiyerarşisi; toprak nemi/sıcaklık okumaları; 30 günden eski ham veri aylık özetlere otomatik arşivlenir |
| 💧 **Sulama önerisi (ML)** | scikit-learn `RandomForestRegressor` — 5 özellikten (nem, toprak sıcaklığı, hava nemi/sıcaklığı, yağış) önerilen su miktarı + güven skoru; tahminler `ModelPerformanceLog`'a yazılır |
| 🦠 **Bitki hastalığı tespiti** | Yaprak fotoğrafından (JPG/PNG/WebP, ≤5 MB) görüntü analizi — 8 sınıf (healthy, leaf_spot, powdery_mildew, rust, blight, mosaic_virus, bacterial_wilt, anthracnose). ONNX CNN desteği hazır; model dosyası yoksa HSV renk-analizi sezgisel moda düşer |
| 🌿 **Gübreleme** | Toprak analizi + bitki türüne göre N-P-K önerisi ve 5 fazlı gübre takvimi — **17 bitki türü** desteği |
| 🌤️ **Hava durumu** | OpenWeatherMap entegrasyonu (API key yoksa demo veri); günlük otomatik fetch + temizleme/enterpolasyon pipeline'ı |
| 🚨 **Uyarılar & analitik** | Sensör anomalisi / hava / model-drift uyarıları; çiftlik-geneli raporlar; PDF (fpdf2) + Excel (openpyxl) dışa aktarım |
| 🗺️ **Harita** | Leaflet + OpenStreetMap; 7 coğrafi bölge renk kodlu çiftlik dağılımı (Türkiye) |
| 🤖 **Filiz asistanı** | Rol-aware ipucu havuzlu, ifade/mood animasyonlu maskot |
| 🌅 **Hoşgeldin ekranı** | Gün-gece temalı (güneş/ay, bulut/yıldız) karşılama; toprağa gömülü Filiz animasyonu |
| 🔐 **4-rollü RBAC** | farmer / developer / overseer / admin — sahiplik kapsamı + yazma kısıtı + admin kullanıcı yönetimi |

---

## ⚡ Hızlı Başlangıç

```bash
git clone https://github.com/Ohualtex/Smart_Farming_Data_Analysis_Platform.git
cd Smart_Farming_Data_Analysis_Platform
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env                                # ⚠️ ZORUNLU — default'lar dev için hazır
python database/seed_data.py                        # demo veri (opsiyonel)
make run                                            # uvicorn → http://localhost:8000
```

> **⚠️ `.env` adımı zorunlu** — `.env` dosyası `.gitignore`'da olduğu için clone'la gelmez. `cp .env.example .env` atlanırsa `_validate_production` fail-fast hatası alınabilir (özellikle `docker compose` ile).

Açılan adresler:
- **Dashboard:** http://localhost:8000/dashboard/
- **Swagger API:** http://localhost:8000/docs
- **Health probe:** http://localhost:8000/api/health/deep

---

## 🔑 Demo Hesaplar

`python database/seed_data.py` çalıştırıldığında aşağıdaki demo hesaplar oluşur (yalnız yerel/demo amaçlı):

| Rol | E-posta | Şifre |
|:--|:--|:--|
| 👑 Admin | `admin@demo.test` | `123456` |
| 🏛️ Gözetmen | `overseer@demo.test` | `123456` |
| 🛠️ Geliştirici | `developer@demo.test` | `123456` |
| 🧑‍🌾 Çiftçi *(ana persona)* | `ahmet@demo.test` | `123456` |
| 🧑‍🌾 Çiftçi | `ayse@demo.test` | `123456` |
| 🧑‍🌾 Çiftçi | `mehmet@demo.test` | `123456` |

> Dashboard'da **Giriş Yap** → bu kimlik bilgileriyle oturum aç. Bunlar yalnızca demo seed hesaplarıdır; **production'da kullanılmamalıdır**.

---

## 🛠️ Teknoloji Yığını

| Katman | Teknolojiler |
|:--|:--|
| **Backend** | FastAPI · Uvicorn · SQLAlchemy 2.0 · Pydantic v2 · Alembic |
| **Veritabanı** | SQLite (dev/demo) · PostgreSQL 16 (prod profili) |
| **ML / veri** | scikit-learn (RandomForest sulama) · Pillow + onnxruntime (bitki sağlığı) · pandas · numpy |
| **Frontend** | Vanilla JS (ES modülleri) · Chart.js 4 · Leaflet 1.9 (CDN) · Vite (yalnız dev/build aracı) |
| **Entegrasyon** | OpenWeatherMap · paho-mqtt (sensör akışı) · APScheduler (cron işler) |
| **Raporlama** | fpdf2 (PDF) · openpyxl (Excel) |
| **Güvenlik** | JWT (python-jose) + bcrypt · slowapi (rate limit) · CSP/HSTS/XFO defense-in-depth header'lar |
| **Gözlemlenebilirlik** | Sentry · Prometheus · yapılandırılmış JSON log |
| **Kalite** | pytest + coverage · Ruff · bandit · pip-audit · Schemathesis · Vitest · axe-core |
| **Deploy** | Docker (multi-stage) · nginx (TLS reverse proxy) · docker compose (postgres/letsencrypt profilleri) |

---

## 👥 Kullanıcı Rolleri

Sistem dört kullanıcı türünü destekler — her rol kendi dashboard görünümü ve API kapsamıyla gelir (`app/middleware/rbac.py`).

| Rol | Erişim kapsamı | Tipik kullanım |
|:--|:--|:--|
| 🧑‍🌾 **Çiftçi** (`farmer`) | Yalnız kendi çiftliği, tarlaları, sensörleri (read + write) | Tarla başına sulama önerisi, yaprak hastalığı tespiti, gübre takvimi |
| 🛠️ **Geliştirici** (`developer`) | Tüm sistem read-only + test endpoint'leri | Sistem entegrasyonu, IoT cihaz bağlama, fuzz/load test |
| 🏛️ **Gözetmen** (`overseer`) | Tüm çiftliklere read-only + harita & analitik | Sistem-geneli gözetim ve raporlama (salt-okunur) |
| 👑 **Admin** (`admin`) | Tüm sistem + kullanıcı yönetimi + rol atama | Operasyonel kontrol, kritik uyarı yönetimi |

**Yazma yetkisi** yalnız `farmer` ve `admin`'de (`require_write`); `overseer` ve `developer` salt-okunurdur. `admin`, `overseer`, `developer` sahiplik/scope filtresinden muaftır (sistem-geneli okuma).

---

## 🏗️ Mimari

```
   [SPA: HTML + ESM (Vanilla JS) + Chart.js + Leaflet]   ← CDN + ham ESM (build'siz servis)
                    ⇅  /api  (JWT bearer)
   [FastAPI routers] → [services] → [SQLAlchemy ORM] → [SQLite / PostgreSQL]
            │
            ├─ JWT bearer + bcrypt + jti blacklist
            ├─ 4-rollü RBAC (ownership scope + write guard)
            ├─ Rate limiting (slowapi: 30/min write · 10/min auth)
            ├─ Defense-in-depth header'lar (CSP / HSTS / XFO / XCTO / Referrer / Permissions)
            ├─ Sentry + Prometheus + yapılandırılmış JSON log
            └─ APScheduler (her gece hava fetch · haftalık sensör arşivleme)
```

**Ölçek:** 16 router · **66 endpoint** · 15 ORM tablo · 4 Alembic migration · çiftçi-odaklı demo seed (birkaç çiftçi · çoklu çiftlik/tarla · 17 bitki türü).

> **Frontend notu:** Üretimde Vite bundle servis edilmez — FastAPI `frontend/` kökünü `/dashboard` altına mount eder, tarayıcı ham ES modüllerini (`src/main.js` + `src/lib/*`) ve Chart.js/Leaflet'i CDN'den yükler. Vite yalnızca yerel geliştirme (`:5173` proxy) ve test/build aracıdır.

**Diyagram + ER şeması:** [`docs/architecture.md`](docs/architecture.md) · [`database/sfdap_schema.sql`](database/sfdap_schema.sql)

---

## 📂 Proje Yapısı

```
app/
├── main.py              # FastAPI app: middleware + router include + static mount
├── config.py            # pydantic-settings; production fail-fast guard'lar
├── routers/             # 16 router · 66 endpoint (farms, fields, sensors, irrigation, …)
├── services/            # iş mantığı (weather, fertilizer, sensor_archiver, report, mqtt, …)
├── ml/                  # irrigation_model (RandomForest) · plant_disease_model · eval
├── models/models.py     # 15 SQLAlchemy ORM tablosu
├── schemas/             # Pydantic v2 request/response şemaları
├── middleware/          # auth · rbac · exceptions (SFDAPError) · rate_limiter · security_headers
└── tasks/scheduler.py   # APScheduler cron işleri
frontend/
├── index.html           # markup (inline style/script yok)
├── src/main.js          # SPA giriş noktası
├── src/lib/*.js         # 8 modül (api, router, map, charts, render, skeleton, utils, ui_helpers)
└── src/styles/*.css     # 10 modül (variables → … → welcome → filiz → theme)
alembic/versions/        # 4 migration (initial → aggregate → RBAC → FK index)
database/                # seed_data.py · turkey_data.py · sfdap_schema.sql (DDL dump)
tests/                   # 38 pytest dosyası + Schemathesis fuzz
docs/                    # mimari, API, ML, kurulum, test, planlama dokümanları
.github/workflows/       # ci.yml · security.yml · a11y.yml
```

---

## 🗃️ Veri Modeli

15 ORM tablosu (`app/models/models.py`), işlevsel gruplar:

- **Kimlik & sahiplik:** `users` (4-rol RBAC) · `farms` · `fields` · `crop_types`
- **Sensör & ölçüm:** `sensors` · `soil_moisture_readings` · `sensor_reading_monthly_aggregates` (arşiv)
- **Tarımsal veri:** `weather_data` · `irrigation_schedules` · `soil_analyses` · `crop_plantings` · `fertilizer_recommendations`
- **Sağlık & gözlem:** `plant_health_images` · `system_alerts` · `model_performance_logs`

Tüm FK id alanları SQLite int64 taşma-koruması (`SqliteSafeInt`) ile sınırlanır. DB-side `CHECK` constraint `users.role`'ü 4 geçerli değere kısıtlar.

---

## 📡 API

- **Swagger UI:** http://localhost:8000/docs (16 router, OpenAPI 3.1 sözleşmesi)
- **OpenAPI JSON:** http://localhost:8000/openapi.json
- **Endpoint + auth + örnek istekler:** [`docs/api/API_Kullanim_Kilavuzu.md`](docs/api/API_Kullanim_Kilavuzu.md)

Hatalar tutarlı **SFDAPError zarfı** ile döner: `{error_code, message, detail}` (örn. `404/NOT_FOUND`, `403/FORBIDDEN`, `409/CONFLICT`). FastAPI doğrulama hataları (422) OpenAPI sözleşmesini korur.

---

## 🧪 Test ve Kalite

| Kategori | Değer | Komut |
|:--|:--|:--|
| Backend test | **650** (586 + 64 Schemathesis fuzz) | `make test` |
| Frontend test | **59** (Vitest + jsdom) | `cd frontend && npm test` |
| Coverage | **%95** (CI eşiği %80) | `make test` |
| Lint + format | Ruff temiz (17 kural grubu) | `make lint && make format` |
| Source security | bandit (medium+) → 0 issue | `make audit` |
| Dependency CVE | pip-audit (haftalık cron) | `make audit` |
| Property-based fuzz | Schemathesis (auth-aware GET/POST/PATCH/DELETE) | `make fuzz` |
| A11y | axe-core WCAG 2.0/2.1 A+AA | `make a11y` |
| Local CI parity | lint + test + audit | `make ci` |

**CI/CD:** 3 GitHub Actions workflow — `ci.yml` (lint + test [Python 3.11 & 3.12 matrisi] + migrations + fuzz + frontend-test), `security.yml` (bandit + pip-audit), `a11y.yml` (axe-core).

> Coverage **eşiği** %80'dir; %95 ölçülen güncel değerdir (eşik aşılmadıkça badge garanti edilmez).

Kapsamlı kalite denetim raporu: [`docs/QUALITY_AUDIT.md`](docs/QUALITY_AUDIT.md)

---

## 💻 Geliştirme

```bash
make run         # uvicorn --reload (127.0.0.1:8000)
make test        # pytest + coverage
make lint        # ruff check
make format      # ruff format
make audit       # bandit + pip-audit
make fuzz        # schemathesis property-based fuzz
make a11y        # axe-core (çalışan sunucu gerektirir)
make ci          # lint + test + audit (CI paritesi)
make migrate     # alembic upgrade head
make schema-dump # database/sfdap_schema.sql'i head'den yeniden üret
```

Frontend dev sunucusu (HMR + `/api` proxy): `cd frontend && npm install && npm run dev` → http://localhost:5173

---

## 🌐 Production Deploy

Docker + nginx reverse proxy + Let's Encrypt SSL şablonu. Adımlar: [`docs/setup/PROD_DEPLOY.md`](docs/setup/PROD_DEPLOY.md)

```bash
cp .env.example .env                                    # ⚠️ ÖNCE: tüm key'ler burada
# Prod için: .env'de ENVIRONMENT=production + gerçek API_KEY/SECRET_KEY/CORS_ORIGINS
docker compose up -d nginx api                          # API + reverse proxy
docker compose --profile letsencrypt run --rm certbot \ # SSL cert
  certonly --webroot -w /var/www/certbot ...
docker compose --profile postgres up -d db              # PostgreSQL'e geçiş
docker compose exec api alembic upgrade head            # Migration uygula
```

`ENVIRONMENT=production` iken `app/config.py` default API_KEY / SECRET_KEY ve wildcard/localhost CORS origin'leri için fail-fast hata fırlatır. `.env` yoksa compose `development` + dev sentinel key'leriyle başlar.

---

## 📋 Proje Durumu

- **Sürüm:** 1.0.0 (Cycle 9 — akademik teslim)
- **Branch akışı:** `rebuild` sprint'i `main`'e merge edildi; güncel polish çalışması feature branch'lerde (örn. `feature/welcome-screen`) yürür ve PR ile `main`'e alınır.
- **Yol haritası & geçmiş:** [`docs/REBUILD_ROADMAP.md`](docs/REBUILD_ROADMAP.md) · cycle bazlı görev tablosu [`projeakisi.md`](projeakisi.md)

---

## 📚 Anahtar Dokümanlar

| Doküman | Açıklama |
|:--|:--|
| [`CHANGELOG.md`](CHANGELOG.md) | Sürüm notları (Keep a Changelog) |
| [`docs/architecture.md`](docs/architecture.md) | Sistem mimarisi + Mermaid diyagramları |
| [`docs/REBUILD_ROADMAP.md`](docs/REBUILD_ROADMAP.md) | Rebuild planı (7 faz) |
| [`docs/FINAL_REPORT.md`](docs/FINAL_REPORT.md) | Akademik teslim raporu |
| [`docs/api/API_Kullanim_Kilavuzu.md`](docs/api/API_Kullanim_Kilavuzu.md) | API kullanım rehberi |
| [`docs/database/Veritabani_Semasi_Tasarimi.md`](docs/database/Veritabani_Semasi_Tasarimi.md) | Veritabanı şema tasarımı |
| [`docs/ml/Makine_Ogrenimi_Rehberi.md`](docs/ml/Makine_Ogrenimi_Rehberi.md) | ML modelleri rehberi |
| [`docs/frontend/Frontend_Kılavuzu.md`](docs/frontend/Frontend_Kılavuzu.md) | Frontend mimari kılavuzu |
| [`docs/setup/PROD_DEPLOY.md`](docs/setup/PROD_DEPLOY.md) | Production deploy kılavuzu |
| [`docs/QUALITY_AUDIT.md`](docs/QUALITY_AUDIT.md) | Kalite denetim raporu |
| [`docs/demo_script.md`](docs/demo_script.md) | Sunum demo akışı |

---

## 👥 Ekip

5 kişilik öğrenci ekibi: Scrum Master + 4 geliştirici. Katkı dağılımı: [`CONTRIBUTORS.md`](CONTRIBUTORS.md) · cycle bazlı görev tablosu: [`projeakisi.md`](projeakisi.md)

## 📜 Lisans

MIT — bkz. [`LICENSE`](LICENSE)
