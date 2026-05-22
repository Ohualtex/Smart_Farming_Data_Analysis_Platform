# 📑 SFDAP — Final Rapor

> **Akıllı Tarım Veri Analizi Platformu** (Smart Farming Data Analysis Platform)
> **Akademik teslim:** 7 Haziran 2026
> **Cycle 9 ana çıktısı.** Bu doküman shiftFinal sırasında erken iskelet olarak başlatıldı; Cycle 9'da ekipçe doldurulacak.

---

## 📋 İçindekiler

1. [Proje Özeti](#1-proje-özeti)
2. [Hedefler ve Kapsam](#2-hedefler-ve-kapsam)
3. [Geliştirme Süreci — 9 Cycle](#3-geliştirme-süreci--9-cycle)
4. [Mimari](#4-mimari)
5. [Veri Modeli ve Veritabanı](#5-veri-modeli-ve-veritabanı)
6. [API Endpoint'leri](#6-api-endpointleri)
7. [Makine Öğrenimi Bileşenleri](#7-makine-öğrenimi-bileşenleri)
8. [Frontend ve Kullanıcı Deneyimi](#8-frontend-ve-kullanıcı-deneyimi)
9. [Güvenlik](#9-güvenlik)
10. [Test, Coverage ve CI/CD](#10-test-coverage-ve-cicd)
11. [Üretim Hazırlığı](#11-üretim-hazırlığı)
12. [Ekip Katkı Matrisi](#12-ekip-katkı-matrisi)
13. [Karşılaşılan Zorluklar ve Çözümler](#13-karşılaşılan-zorluklar-ve-çözümler)
14. [Gelecek Çalışmalar](#14-gelecek-çalışmalar)
15. [Kaynaklar ve Referanslar](#15-kaynaklar-ve-referanslar)

---

## 1. Proje Özeti

> 🚧 **TODO Cycle 9 — Emirhan:** 1-2 paragraf — sistemin amacı, hedef kullanıcı (çiftçi/kooperatif), temel yetenekler.
> *Mevcut README "Hızlı Başlangıç" bölümünden yararlanılabilir.*

**Tek satır:** SFDAP, sensör ve hava durumu verilerini ML modelleriyle birleştirerek çiftçilere sulama, gübreleme ve bitki sağlığı önerileri sunan kapsamlı bir veri analizi ve karar destek platformudur.

**Ölçek:** Çiftçi-odaklı demo seed — 5 kullanıcı (3 çiftçi + admin + gözetmen), 3 çiftlik (farklı bölgeler), 6 tarla, 6 sensör, ~90 sensör okuması, hava/sulama/hastalık/toprak/uyarı kayıtları. (Üretim ölçeği kullanıcı sayısıyla doğrusal büyür; sistem 81-il "ulusal" iddiasından vazgeçti.)

## 2. Hedefler ve Kapsam

### Hedef persona

**Çiftçi Ahmet** — 47 yaşında, Konya'da 8 hektarlık çiftliği var, 4 tarlada
buğday + ayçiçeği, 6 toprak nem sensörü kullanıyor. iPhone'undan tarlada
bağlanıyor; bilgisayar bilgisi orta. Sistem Ahmet'in 5 sorusuna cevap
vermeli:

1. **"Tarlam susuz mu, ne zaman sulayayım?"**
2. **"Bu yaprakta hastalık var mı?"**
3. **"Gübre ne zaman, ne kadar?"**
4. **"Komşulara göre durumum nasıl?"**
5. **"Bir sorun çıkarsa haberim olacak mı?"**

İkincil persona: **sistem gözetmeni** (admin/overseer rolü) — tüm çiftliklerde
read-only gözetim için harita + analytics + raporlama panosu.

### İşlevsel hedefler

- 💧 ML tabanlı sulama önerisi (RandomForest) + onaylama akışı (`/api/irrigation/schedules`)
- 🌱 NPK tabanlı gübreleme önerisi + kayıt (`FertilizerRecommendationLog`)
- 🦠 CNN tabanlı yaprak hastalığı analizi (heuristic + ONNX-ready) + tarla bağlamlı kayıt
- 📡 IoT/MQTT sensör stream + 30 günden eski okumaların aylık aggregate'e arşivlenmesi
- 🔔 Per-user bildirim akışı (toprak nemi düşüklüğü, hastalık kontrolü hatırlatması)
- 🗺️ Gözetmen panosu: sistemdeki çiftliklerin dağılım haritası + bölge bazlı analytics

### İşlevsel olmayan hedefler

- **RBAC**: farmer kendi verisini, admin tüm sistemi görür
- Coverage ≥ %80 (gerçekleşen: %95+)
- API yanıt süresi < 500 ms (gerçekleşen: ~12 ms TestClient)
- Defense-in-depth response header'lar (CSP, HSTS, XFO, XCTO, Referrer, Permissions)
- Production-grade auth (JWT + bcrypt + `jti` blacklist) + rate limit + TLS
- PostgreSQL'e geçiş kapasitesi (`pool_size`/`max_overflow` env-tunable)

### Kapsam dışı (Cycle 10+ roadmap)

- E-posta/SMS bildirim gönderimi (alerts dashboard'da görünür ama push yok)
- Mobil native uygulama (PWA roadmap'te)
- Çoklu-tenant SaaS (kurumsal/kooperatif paylaşımı)
- Gerçek CNN model eğitimi (PlantVillage dataset)

## 3. Geliştirme Süreci — 9 Cycle

> 🚧 **TODO Cycle 9 — Miraç:** Her cycle için 2-3 cümle özet ekle. Şimdilik iskelet.

| Cycle | Tarih | Tema | Anahtar Çıktı |
|:--|:--|:--|:--|
| 1 | 24 Şub – 10 Mart | Proje Temelleri | Repo + teknoloji araştırması + gereksinim doc |
| 2 | 11 – 24 Mart | Veri Planlama | Schema tasarımı, veri kaynakları |
| 3 | 25 Mart – 1 Nis | Tasarım | API tasarımı, DB şeması, UI wireframe |
| 4 | 2 – 13 Nis | Geliştirme | FastAPI iskeleti, sensör entegrasyonu, weather pipeline, ML sulama, Chart.js dashboard |
| 5 | 14 – 27 Nis | Test + Pre-prod | CI/CD, %80 coverage, Alembic, mega seed (81 il), gübre öneri, API güvenlik |
| 6 | 28 Nis – 3 May | İleri özellikler | shiftSession bridge, model performans dashboard, drift detection, raporlama (PDF/Excel) |
| 7 | 3 – 10 May | İzleme + Gelişmiş | Filiz maskotu, Auth UI, Plants UI, Alerts panel, MQTT stream, plant_disease CNN |
| 8 | 10 – 12 May | Üretim Hazırlığı (core) | Rate limit, N+1 fix, JWT auth, Alembic 14-tablo migration, nginx + Let's Encrypt |
| shiftFinal | 13 – 17 May | Cila + Gözlemlenebilirlik | Sentry, Prometheus, structured logging, Vite bundling, a11y, backup/restore, edge tests, security headers, farms router, Türkiye haritası, Vitest scaffold |
| REBUILD | 18 – 30 May | Kullanıcı-Odaklı Yeniden Yapılandırma *(solo, Miraç)* | RBAC + per-user data isolation, "Çiftliğim" dashboard, tarla detay sayfası, eylem akışları, bildirim, onboarding |
| 9 | 1 – 7 Haz | Final Rapor + Sunum | **Bu doküman** + sunum slaytları + Q&A + akademik teslim |

**Detay:** Her cycle için ayrı retrospective var (Cycle 8: [`CYCLE_8_RETROSPECTIVE.md`](CYCLE_8_RETROSPECTIVE.md)).

## 4. Mimari

> 🚧 **TODO Cycle 9 — Miraç:** `docs/architecture.md`'den Mermaid diyagramları + açıklama paragrafları aktar.

**Üst düzey:**
- **Frontend katmanı:** Tek dosyalı SPA (`frontend/index.html` ≈ 3 100 satır + Vite scaffold) — shiftFinal A3'te a11y/skeleton refactor + Vite build pipeline iskeleti eklendi; ES module split Cycle 9 sonrası kademeli
- **API katmanı:** FastAPI Gateway → 11 router × 43 endpoint (pagination count endpoint'leri dahil)
- **İş katmanı:** Servisler (`weather_service`, `fertilizer_service`, `mqtt_listener`, `sensor_archiver`, `report_service`, `data_quality`)
- **ML katmanı:** RandomForest (sulama) + heuristic+ONNX (bitki hastalığı) + APScheduler periyodik görevler
- **Veri katmanı:** SQLAlchemy 2.0 ORM, SQLite (dev) / PostgreSQL (prod), Alembic migration
- **Dış sistemler:** OpenWeatherMap API, MQTT broker, Let's Encrypt

**Mermaid graph:** [`docs/architecture.md`](architecture.md)

## 5. Veri Modeli ve Veritabanı

**15 ORM tablosu** ([`app/models/models.py`](../app/models/models.py)):

`User`, `Farm`, `Field`, `CropType`, `Sensor`, `SoilMoistureReading`, `WeatherData`, `IrrigationSchedule`, `PlantHealthImage`, `SystemAlert`, `ModelPerformanceLog`, `SoilAnalysis`, `CropPlanting`, `FertilizerRecommendationLog`, `SensorReadingMonthlyAggregate` *(Cycle 8 archiving)*

**Alembic migration zinciri:**
1. `9021458f6b9f` — initial schema (14 tablo, Cycle 8 #4)
2. `4d1a1503f306` — sensor_reading_monthly_aggregates (Cycle 7 slip kapanışı)

**Schema detayı:** [`docs/database/Veritabani_Semasi_Tasarimi.md`](database/Veritabani_Semasi_Tasarimi.md)

## 6. API Endpoint'leri

**~47 endpoint × 12 router:**

| Router | Endpoint | Anahtar Yetenek |
|:--|:--:|:--|
| `auth` | 4 | JWT bearer + bcrypt (Cycle 8 #3); `jti` blacklist (shiftFinal `dec2e82`) |
| `farms` | 3 | **Cycle 9 prep:** list/detail + nested fields + per-farm soil analyses |
| `sensors` | 7 | CRUD + readings + **count (pagination)** |
| `weather` | 6 | CRUD + OpenWeatherMap fetch + clean |
| `irrigation` | 4 | ML predict + schedule CRUD + **count (pagination)** |
| `fertilizer` | 3 | NPK recommend (17 bitki) |
| `plants` | 3 | Health image URL + CNN multipart |
| `analytics` | 3 | Summary + compare + export (PDF/Excel) |
| `alerts` | 4 | SystemAlert CRUD + severity filter |
| `model_performance` | 7 | Log + summary + timeseries + drift detection |
| `metrics` | 3 | /health, /health/deep |
| `health` | 1 | Sığ load balancer probe |

**Pagination pattern (sensors + irrigation):** `?skip=0&limit=50` formatında sayfa-temelli erişim. Frontend `/count` endpoint'inden toplam kayıt sayısını alır, `◀ Önceki / Sonraki ▶` butonlarıyla sayfaları gezdirir (50 kayıt/sayfa).

**Detay:** [`docs/api/API_Kullanim_Kilavuzu.md`](api/API_Kullanim_Kilavuzu.md), Swagger UI: `http://localhost:8000/docs`

## 7. Makine Öğrenimi Bileşenleri

> 🚧 **TODO Cycle 9 — Ayşe:** Model performans metrikleri tablosu (accuracy, MAE), eğitim setleri, drift detection sonuçları.

### 7.1 Sulama Optimizasyon Modeli
- **Algoritma:** RandomForestRegressor (sklearn 1.8.0)
- **Girdi:** soil_moisture, soil_temperature, humidity, temperature, precipitation
- **Çıktı:** önerilen su miktarı (litre), aciliyet seviyesi
- **Eğitim:** 1000 sentetik örnek, deterministic seed=42
- **Persisted:** `app/ml/models/irrigation_model.pkl` + `scaler.pkl`

### 7.2 Bitki Hastalığı Tespiti
- **Mod 1 (heuristic):** Pillow HSV renk analizi → 8 sınıf (healthy, leaf_spot, powdery_mildew, rust, blight, mosaic_virus, bacterial_wilt, anthracnose)
- **Mod 2 (ONNX-ready):** Model dosyası yüklendiğinde otomatik geçer; CNN inference için iskelet hazır
- **Endpoint:** `POST /api/plants/health-images/analyze` (multipart, max 5MB)

### 7.3 Model Performans İzleme
- Her ML tahmininden sonra `ModelPerformanceLog` kaydı (sessiz auto-log)
- Drift detection: son N gün vs baseline → eşik üstü ise `SystemAlert` (medium severity)

## 8. Frontend ve Kullanıcı Deneyimi

> 🚧 **TODO Cycle 9 — Ecenur:** Ekran görüntüleri + sayfa-sayfa anlatım.

**Mevcut yapı:** Tek dosya SPA, ~3 100 satır, 9 sayfa, dark/light tema, Chart.js, vanilla JS.

**Filiz maskotu** (Cycle 7 — Miraç):
- Inline SVG, idle/blink/mood animasyonları
- 65+ Türkçe tarım ipucu
- Gündüz happy / gece sleepy mood
- Tıklama tepkileri (kalp + sinirli)

**shiftFinal A3 (Ecenur — `02d1359`):**
- **Vite scaffold:** `package.json` + `vite.config.js` (dev :5173, FastAPI :8000 proxy); ES module split Cycle 9 sonrası
- **A11y:** skip-to-content link, `<main id="main-content" role="main" tabindex="-1">`, sidebar `<nav aria-label="Ana menü">`, `aria-current="page"`, hamburger `aria-controls`+`aria-expanded`, `<th scope="col">`+sr-only caption, decorative icon `aria-hidden`, toast container live region, `:focus-visible` outline
- **Skeleton loaders:** 4 JS helper (`_skeletonCards`, `_skeletonRows`, `_skeletonBlock`, `_setBusy`); 8 hedef element için fetch öncesi iskelet + `aria-busy`. `@media (prefers-reduced-motion: reduce)` → animation:none
- **Tests:** 28 yeni a11y testi (`test_frontend_a11y.py`)

**axe-core CI (Ayşe — shiftFinal `7e49bef`):** `.github/workflows/a11y.yml`, WCAG 2.0 + 2.1 A/AA tarama, haftalık cron.

## 9. Güvenlik

**Çok katmanlı savunma:**
| Katman | Mekanizma | Cycle |
|:--|:--|:--:|
| Yetkilendirme | `X-API-Key` header (writes) | 4 |
| Yetkilendirme | JWT bearer (HS256) + bcrypt | 8 |
| Hız sınırlama | slowapi 30/min STRICT + 10/min AUTH (17 endpoint) | 8 |
| TLS | nginx reverse proxy + Let's Encrypt | 8 |
| **Response header'lar** | **CSP + HSTS (prod) + XFO + XCTO + Referrer-Policy + Permissions-Policy** | **shiftFinal** |
| CORS | env-driven origin listesi + production guard (`*`/localhost yasak) | 5 + shiftFinal |
| Production fail-fast | default secret + güvensiz CORS engellenir | 5 + shiftFinal |
| Source taraması | bandit medium+ severity (0 issue) | 8 |
| Dependency taraması | pip-audit (CI, haftalık cron) | 8 |
| Logout | JWT `jti` blacklist (RFC 7519 §4.1.7) | 8 + shiftFinal |
| `/metrics` discovery | `X-Robots-Tag: noindex, nofollow` | shiftFinal |

## 10. Test, Coverage ve CI/CD

```
Test sayısı:        462 backend (29 dosya) + 14 frontend (Vitest)
                    246 → 313 → 350 → 365 (A2) → 372 (A4) → 400 (A3)
                    → 425 (Ayşe ilk paket) → 446 (auth-aware POST/PATCH/
                    DELETE fuzz `61c64e4` + 7. int64 fix `4a0308a`)
                    → 462 (Cycle 9 prep: `farms` router 13 test)
Coverage:           %95.04
Linter:             Ruff (17 kural grubu) — All checks passed
Source security:    Bandit medium+ — 0 issue
API fuzz:           Schemathesis property-based — 25 GET + auth-aware
                    POST/PATCH/DELETE write endpoints (`61c64e4`),
                    strict OpenAPI contract conformance (`c683da0`)
A11y:               axe-core CLI WCAG 2.0 + 2.1 A/AA — strict mode
                    (`f2e9bf8`), CI haftalık + PR tarama
CI workflows:       3 (.github/workflows/ci.yml + security.yml + a11y.yml)
Pre-commit hooks:   ruff v0.13, bandit 1.8, trim/EOF/yaml/large-files,
                    merge-conflict, detect-private-key
```

**CI pipeline (`ci.yml`):**
1. **Lint** (Ruff check + format)
2. **Test** (pytest + HTML + XML coverage)
3. **Migrations** (alembic upgrade head smoke)
4. **Fuzz** (Schemathesis property-based API fuzz, shiftFinal Ayşe)

**Security pipeline (`security.yml`, haftalık + PR):**
1. **Bandit** (Python source security)
2. **pip-audit** (dependency CVE)

**A11y pipeline (`a11y.yml`, haftalık + PR — shiftFinal Ayşe):**
1. **axe** — FastAPI bg + `@axe-core/cli` WCAG 2.0 + 2.1 A/AA tarama; JSON rapor 30 gün artifact

**Detay:** [`docs/QUALITY_AUDIT.md`](QUALITY_AUDIT.md)

## 11. Üretim Hazırlığı

**Production-ready bileşenler (Cycle 8 sonu):**
- Docker + multi-stage Dockerfile
- docker-compose: api + nginx + certbot (Let's Encrypt) + postgres (opt-in profile)
- Alembic migration zinciri (boş DB → `alembic upgrade head` = 15 tablo)
- env-driven config (12-factor uyumlu)
- HTTPS termination + ACME challenge
- Rate limiting + brute-force koruması
- 30 günden eski sensör okumalarını arşivleyen haftalık cron

**Deployment kılavuzu:** [`docs/setup/PROD_DEPLOY.md`](setup/PROD_DEPLOY.md)

## 12. Ekip Katkı Matrisi

| Üye | Cycle 1 | Cycle 2 | Cycle 3 | Cycle 4 | Cycle 5 | Cycle 6 | Cycle 7 | Cycle 8 | shiftFinal | Cycle 9 |
|:--|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| **Miraç Duran** | Proje temelleri + teknoloji araştırması | DB yapı planı | API tasarım | ML sulama modeli | CI/CD + integration testler | 81 il expand + analytics dashboard + DX cleanup | Filiz maskot + UX cilası | 5 production-core + 6 bonus | Code quality polish + **security hardening + farms router + jti audit fix + Türkiye haritası + Vitest scaffold** | **REBUILD solo refactor** ([REBUILD_ROADMAP](REBUILD_ROADMAP.md)) + final rapor + sunum koordinasyonu |
| **Emirhan Günay** | Proje analizi | (—) | DB şema | Sensör entegrasyon | Alembic + seed data | Veri temizleme iyileştirme | MQTT + (archiving Cycle 8'e kaydı) | (archiving Miraç tarafından) | Backup + DB pool | Final rapor yazımı |
| **Ayşe E. Çekici** | Gereksinim toplama | (—) | UI/UX wireframe | Weather pipeline | Gübre öneri sistemi | ML değerlendirme | CNN bitki sağlığı | (Tier A1 ✅ Miraç bonus) | Edge case tests + auth integration | Sunum slaytları üretimi |
| **Ecenur Üner** | Dev ortamı | Veri toplama planı | (—) | Chart.js dashboard | Dashboard modern + responsive | Veri hattı izleme | Auth UI + Plants UI + Alerts panel | (—) | Vite bundling + a11y + skeleton | Sunum görsel tasarımı |
| **Mehmet S. Tayşi** | Veri seti ön işleme | Veri analizi + model seçim | (—) | Temel veri API | API güvenlik (rate limit + CORS) | Model performans altyapı | Health/Metrics + alerts CRUD | (—) | Sentry + Prometheus + structured logs | Sunum hazırlık + Q&A senaryoları |

> **Cycle 9 not:** Ekip yalnız sunum + rapor üretir; teknik geliştirme **REBUILD branch'inde Miraç solo** yürütür. Cycle 9 hücreleri buna göre güncellendi.

## 13. Karşılaşılan Zorluklar ve Çözümler

**Cycle bazlı kısa liste:**
- **Cycle 4:** Pydantic v1 → v2 geçişi, FastAPI lifespan API'si
- **Cycle 5:** Coverage hedefi %80'i tutturma — eksik integration testler
- **Cycle 6:** 81 il mega seed data — gerçekçi diurnal pattern üretme
- **Cycle 7:** Filiz maskot inline SVG kompozisyonu — animasyon timing
- **Cycle 8:** bcrypt 5↔passlib 1.7.4 uyumsuzluğu, alembic versions/ git-tracking sorunu, naming refactor (8.5 → shiftFinal)
- **shiftFinal:** 4 ayrı production-risk bug yakalanıp düzeltildi (aşağıda detayı).

### shiftFinal sprintinde yakalanan bug'lar

**1. `int64` overflow ailesi (8 ayrı bug, 2 dalga)**

*Belirti:* Schemathesis fuzz testleri rastgele `2^63`'e yakın int değerleri
üretiyor; backend bunları SQLite INTEGER (signed-64bit) sütunlarına yazmaya
çalıştığında `OverflowError: Python int too large to convert to SQLite
INTEGER` fırlatıyor → 500 server error.

*Kök neden:* Pydantic v2 default `int` türü Python'un sınırsız integer'ına
karşılık geliyor; SQLite (PostgreSQL `BIGINT` de aynı sınırı paylaşır)
2^63-1 üstünü kabul etmiyor.

*Düzeltme:*
- **6 bug** (Ayşe, `7e49bef`): GET sorgu parametrelerinde `MAX_SKIP =
  1_000_000` Query constraint'i (`sensors.py`, `irrigation.py`); >1M skip
  artık 422 graceful dönüyor.
- **7. bug** (`4a0308a`): POST body'lerdeki FK int alanları için ortak
  `SqliteSafeInt = Annotated[int, Field(le=2^63-1, ge=-2^63)]` alias
  (`app/schemas/schemas.py`) — 6 Create schema'ya uygulandı.
- **8. bug — JWT `jti` collision** (`dec2e82`): `_create_token` `iat`'i
  saniye-precision integer yazıyor; aynı `sub` + aynı saniyede iki token
  payload'ı byte-identical → encode edilince *aynı JWT string*'i veriyor.
  Test suite'inde `TestLogout` ve `test_full_auth_lifecycle` ardışık
  koştuğunda ilk logout ikinci login'in token'ını da blacklist'liyor (production'da düşük olasılık ama mümkün edge).
  Fix: token payload'a `uuid.uuid4().hex` ile `jti` claim'i (RFC 7519
  §4.1.7); blacklist token-string yerine `jti` ile çalışıyor. Geriye
  uyumluluk: `jti`'siz eski token'lar "never-blacklisted" sayılır.

**2. Trackpad inertia: kontrolsüz harita zoom (`8ff0234`)**

*Belirti:* Türkiye haritası sayfasında trackpad ile büyütüp küçültürken
"3-4 atlama" oluyordu; tek iki-parmak swipe = 3+ zoom adımı, kullanım
"öldürücü" hale geliyordu.

*Kök neden:* macOS trackpad bir iki-parmak swipe için 1-2 saniyelik
inertia kuyruğunda 30+ wheel event ateşliyor. Leaflet'in built-in
`scrollWheelZoom` handler'ı `wheelDebounceTime=100ms` ile bunları ~10
burst'e indiriyordu — yine de yetersiz, her burst bir zoom adımı
demek.

*Düzeltme:* `scrollWheelZoom: false` ile Leaflet'in kendi handler'ı
tamamen kapatıldı; yerine custom `wheel` listener: tek event = ±1 zoom
step + 250ms cooldown. Bir trackpad jesti artık tek zoom step yapıyor,
inertia kuyruğundaki geri kalan 30 event sessiz drop ediliyor.

**3. JWT blacklist test sızıntısı (`2950672` — conftest fix)**

*Belirti:* `test_full_auth_lifecycle` tam suite'te 401, tek başına 200.
Random test ordering altında flaky.

*Kök neden:* `_BLACKLISTED_JTIS` modül-seviyesi global; `TestLogout`
test'lerinden kalan jti'ler edge-case test'lerine sızıyordu (özellikle
jti'siz iki test arası).

*Düzeltme:* `tests/conftest.py` `client` fixture'ı her test öncesi
`_BLACKLISTED_JTIS.clear()` çağırıyor — test isolation hijyeni.

**4. Production CORS allowlist (`2950672`)**

*Belirti:* Dev ortamı için ayarlı `CORS_ORIGINS="http://localhost:..."`
production deploy'a kayarsa attacker-controlled localhost iframe credential
exfil yapabilir; mevcut `_validate_production` sadece API_KEY/SECRET_KEY
default sentinel'lerini kontrol ediyordu.

*Düzeltme:* `_validate_production` artık `CORS_ORIGINS` listesinde
wildcard `*` veya `localhost`/`127.0.0.1` görünce `RuntimeError`
fırlatıyor — fail-fast.

> Tüm 4 maddenin kapsamlı testleri `tests/test_jti_blacklist.py`,
> `tests/test_security_headers.py` ve `tests/test_edge_cases.py` içinde
> yaşıyor (toplam **475+ pytest** + **32 Vitest** test).

## 14. Gelecek Çalışmalar

**Bilinen teknik borçlar (Cycle 9 ve sonrası için):**
- `bcrypt 5.0` geçişi (passlib yeni sürümünü bekliyoruz)
- RBAC (role-based access control) — kullanıcı bazlı izolasyon
- Refresh token + JWT blacklist Redis'e taşıma
- Frontend Vitest birim test scaffold'u — şu an sadece axe-core E2E var
- pip-audit lokal venv subprocess hatası (CI'da temiz, dev makine env sorunu)
- `.venv` recreate yardımcısı — eski mutlak path shebang'leri kaldıktan
  sonra Python script'leri (`bandit`, `pip-audit`) `python -m` üzerinden
  çağrılmak zorunda

**shiftFinal sırasında kapatılanlar:**
- ✅ Frontend ES module split — `frontend/index.html`'in inline CSS/JS'i
  `src/styles/main.css` + `src/main.js`'e ayrıldı (`8f5920e`)
- ✅ axe-core CI strict mode — `continue-on-error: false`'a alındı +
  WCAG AA kontrast hataları düzeltildi (`f2e9bf8`)
- ✅ Schemathesis fuzz POST/PATCH/DELETE genişletme — auth-aware (`61c64e4`)
- ✅ Strict OpenAPI contract conformance — schema/status/content-type/
  no-5xx (`c683da0`)
- ✅ `SqliteSafeInt` Create-schema FK bound'u — fuzz 7. int64 bug (`4a0308a`)
- ✅ JWT `jti` blacklist — `_create_token` `iat` saniye-precision
  collision'ı; logout 8. audit bug (`dec2e82`)
- ✅ Frontend Vitest scaffold — 14 birim test, jsdom env, CI'da
  `frontend-test` job (`466dfab`)
- ✅ Cycle 9 prep: `farms` router (list + detail + per-farm soil) —
  schema-only kalan `Farm`/`Field`/`SoilAnalysis` modelleri için GET
  endpoint'leri (commit pending bu batch'te)
- ✅ `database/sfdap_schema.sql` Alembic head'den regenerate; drift
  kaldı (`make schema-dump` target eklendi)

**Olası ileri özellikler:**
- Gerçek CNN dataset eğitimi (PlantVillage)
- Mobil arayüz (React Native veya Flutter)
- Multi-tenant SaaS modeli (kooperatif/Bakanlık)
- Tahminsel hava durumu (5-7 günlük) ML modeli
- Coğrafi heatmap görselleştirmesi (Türkiye haritası)

## 15. Kaynaklar ve Referanslar

- [`README.md`](../README.md) — proje üst düzey tanıtımı
- [`projeakisi.md`](../projeakisi.md) — sprint bazlı görev dağılımı
- [`CONTRIBUTORS.md`](../CONTRIBUTORS.md) — ekip + metrik tablosu
- [`docs/architecture.md`](architecture.md) — sistem mimarisi
- [`docs/QUALITY_AUDIT.md`](QUALITY_AUDIT.md) — Cycle 8 sonu kalite denetimi
- [`docs/CYCLE_8_RETROSPECTIVE.md`](CYCLE_8_RETROSPECTIVE.md) — Cycle 8 retrospective
- [`docs/setup/PROD_DEPLOY.md`](setup/PROD_DEPLOY.md) — üretim deploy kılavuzu
- [`docs/api/API_Kullanim_Kilavuzu.md`](api/API_Kullanim_Kilavuzu.md) — API kullanım rehberi
- [`docs/demo_script.md`](demo_script.md) — sunum demo akışı
- [`docs/database/Veritabani_Semasi_Tasarimi.md`](database/Veritabani_Semasi_Tasarimi.md) — DB şema detayı
- [`docs/research/`](research/) — Cycle 1-2 araştırma raporları

**Akademik kaynaklar:**
> 🚧 **TODO Cycle 9:** Kullanılan kütüphane referansları (FastAPI, SQLAlchemy, scikit-learn, ONNX, Chart.js, ...), ilgili makaleler, dataset kaynakları.

---

**Yazan:** Miraç Duran (iskelet — Cycle 8 sonu, 11 Mayıs 2026)
**Tamamlanması beklenen:** 7 Haziran 2026 (Cycle 9 son günü, akademik teslim)
**Format:** Bu Markdown kaynağı sunum öncesi PDF'e dönüştürülecek (Pandoc veya `analytics/export?format=pdf`).
