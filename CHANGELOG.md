# Changelog

Bu proje [Keep a Changelog](https://keepachangelog.com/tr/1.1.0/) formatını ve
[Semantic Versioning](https://semver.org/spec/v2.0.0.html) sözleşmesini izler.

Sürümler proje cycle'larına eşlenir: Cycle 5 → 0.5, Cycle 6 → 0.6, Cycle 7 → 0.7,
Cycle 8 → 0.8, `shiftFinal` bridge sprint → 0.9. Cycle 9 (akademik teslim) → 1.0.

---

## [Unreleased] — `shiftFinal` (13 – 19 Mayıs 2026)

Cycle 8 sonrası bridge sprint — cila ve gözlemlenebilirlik. Sprint açık,
ek commit'ler bu bölüme eklenmeye devam edecek.

### Added
- **Production security hardening (A-batch)**: yeni
  `SecurityHeadersMiddleware` her response'a 5 (dev) / 6 (prod)
  defense-in-depth header ekler:
  - `Content-Security-Policy` — default-src 'self', script-src
    Chart.js + Leaflet CDN allowlist, frame-ancestors 'none'
    (`'unsafe-inline'` geçici — `main.js` ES module split sonrası
    daraltılacak)
  - `Strict-Transport-Security` (yalnız production)
  - `X-Frame-Options: DENY`
  - `X-Content-Type-Options: nosniff`
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `Permissions-Policy` — geolocation/microphone/camera/payment/
    usb/magnetometer/gyroscope/accelerometer hepsi `()`
  - `X-Robots-Tag: noindex, nofollow` (sadece `/metrics`)
- **CORS production guard genişletildi**: `_validate_production` artık
  CORS_ORIGINS içinde wildcard `*` veya `localhost`/`127.0.0.1`
  gördüğünde fail-fast RuntimeError fırlatır (önceden sadece
  API_KEY/SECRET_KEY default'ları kontrol ediliyordu).
- **`tests/test_security_headers.py`** — 13 test (8 header behaviour
  + 5 CORS production guard senaryosu).
- **`tests/conftest.py`** — `client` fixture'ı artık her test öncesi
  `_BLACKLISTED_JTIS.clear()` çağırarak JWT blacklist state
  kontaminasyonunu önler.
- **Türkiye haritası dashboard sayfası (Cycle 9 prep)**: Leaflet 1.9.4
  ile 81 il × 81 çiftlik coğrafi dağılım haritası. Sidebar'da yeni
  "🗺️ Harita" nav item, `<section id="page-map">` Leaflet container
  + 7 coğrafi bölge için renk kodu legend, OpenStreetMap tile layer,
  bölge bazlı `L.circleMarker`, çiftlik adı + il + alan popup'ı.
  Veri kaynağı: yeni `GET /api/farms/?limit=500` endpoint'i.
  `frontend/src/styles/main.css` map-legend + popup tema uyumu (dark
  mode dahil) için ek stiller.
- **`farms` router (Cycle 9 prep)**: schema-only kalan `Farm`/`Field`/
  `SoilAnalysis` modelleri için GET endpoint'leri:
  - `GET /api/farms/` — region + city filter + skip/limit pagination
  - `GET /api/farms/{farm_id}` — nested fields ile detay (selectinload
    ile N+1 önlendi)
  - `GET /api/farms/{farm_id}/soil` — çiftliğin tüm tarlalarındaki
    toprak analizleri (analiz tarihine göre desc)
  - 13 birim test (`tests/test_farms.py`) + `app/schemas/schemas.py`
    `FarmResponse` / `FarmDetailResponse` / `FieldSummary` /
    `SoilAnalysisResponse` Pydantic modelleri.
- **`make schema-dump` target**: `database/sfdap_schema.sql`'i Alembic
  head'den otomatik regenerate eder (geçici SQLite + `.schema` dump).
  Schema dosyası 23 Nisan tarihliydi — 4 yeni tablo (`soil_analyses`,
  `crop_plantings`, `fertilizer_recommendations`,
  `sensor_reading_monthly_aggregates`) eksikti; bu batch'te 245 satıra
  güncellendi.
- **Frontend Vitest birim test scaffold'u**: `frontend/src/lib/skeleton.js`
  (main.js'teki 4 a11y helper'ının ESM mirror'ı — drift TODO Cycle 9
  frontend split'inde kapanacak), `vitest.config.js` (jsdom env),
  `frontend/tests/skeleton.test.js` (14 test — HTML contract + aria-busy
  toggle). CI'a `frontend-test` job eklendi (`ci.yml`).
- **Gözlemlenebilirlik stack'i** (`e6259ae`): Sentry SDK (FastAPI + Starlette
  + SQLAlchemy + Logging integration, `send_default_pii=False`),
  Prometheus middleware (4 metric: request count/duration histogram, model
  prediction count, active alerts gauge), structured JSON logging
  (`LOG_FORMAT=json|text`), per-request UUID + `X-Request-ID` header.
- **Frontend Vite scaffold + erişilebilirlik paketi** (`02d1359`): Vite 5
  build/dev server, FastAPI proxy, 4 skeleton loader helper (`_skeletonCards`,
  `_skeletonRows`, `_skeletonBlock`, `_setBusy`), skip-to-content link,
  ARIA live regions, `aria-current`/`aria-controls`/`aria-expanded` sync,
  keyboard-friendly sensor rows, `:focus-visible` outline.
- **Yedekleme/geri yükleme + DB pool tuning** (`2a889f8`): `scripts/backup.sh`
  (SQLite `.backup` + PostgreSQL `pg_dump --format=custom`),
  `scripts/restore.sh` (interaktif `EVET` onay + auto safety backup),
  `BACKUP_DIR`/`RETENTION_DAYS` env, Makefile target'ları,
  `pool_size/max_overflow/pool_pre_ping/pool_recycle` env-konfigurable.
- **Schemathesis API fuzz** (`7e49bef`, `61c64e4`): 25 GET + auth-aware
  POST/PATCH/DELETE endpoint'leri property-based test, `MAX_SKIP=1_000_000`
  Query constraint, global `IntegrityError → 409` exception handler.
- **axe-core a11y CI** (`7e49bef`, `f2e9bf8`): WCAG 2.1 AA full scan,
  strict mode, JSON artifact 30 gün retention, Pazartesi 07:00 cron.
- **Strict OpenAPI contract conformance** (`c683da0`): schema/status/
  content-type/no-5xx kontratı, response body schema doğrulama.
- **Type annotation + docstring polish** (`7d9884d`, `cfe1046`): ANN001/
  ANN201 (return + argument type), D101/D102 (class + method docstring)
  Pydantic schemas + ORM models.

### Changed
- **`frontend/index.html` split** (`8f5920e`): inline `<style>` →
  `src/styles/main.css`, inline `<script>` → `src/main.js`. Daha küçük
  inline HTML, daha kolay test edilebilir JS.
- **CI lockfile gate** (`0f325d5`): `npm install` → `npm ci`,
  `package-lock.json` artık commit'leniyor.
- **Sprint board doc senkronu** (`a284450`, `c01ef27`): `projeakisi.md`
  in-progress sprint ile ve Miraç polish paketinin pre-sprint
  kapanışıyla hizalandı.
- **In-code author/cycle/sprint atıfları kaldırıldı** (`f3e9715`):
  kaynak kod artık `# Cycle X — Y kişi` gibi atıflar içermiyor;
  bağlam `projeakisi.md` ve git history'de yaşıyor.

### Fixed
- **6 int64 overflow bug** (`7e49bef`): `sensors.py`/`irrigation.py`'de
  Query param `skip` int64 üst sınırını aşınca SQLite `OverflowError`
  → 500 dönüyordu. `MAX_SKIP=1_000_000` Query constraint eklendi;
  artık 422 graceful.
- **7. int64 overflow bug** (`4a0308a`): Schemathesis fuzz
  `POST /api/weather/` body'de `farm_id=9_223_372_036_854_775_808`
  (= 2^63) gönderdi → SQLite INSERT crash. `SqliteSafeInt =
  Annotated[int, Field(le=2^63-1, ge=-2^63)]` alias 6 FK field'a
  (Sensor/SensorReading/Weather/Irrigation/SystemAlert) uygulandı.
- **WCAG AA kontrast hataları** (`f2e9bf8`): axe-core strict mode
  geçişinde tespit edilen renk kontrastı düşüklükleri düzeltildi.
- **Residual ruff hits** (`9a103d4`): `database/seed_data.py` 3 ×
  PERF401 + 1 ERA001, `scripts/weather_processing.py` + `scripts/
  verify_sensor_data.py` DTZ005 (`datetime.now(UTC)` migrasyonu),
  legacy `docs/testing/*` arşivi için per-file-ignore.

### Security
- **OpenAPI input contract** sıkılaştırması — fuzz/contract test'ler
  artık her POST/PATCH/DELETE'i kontrat dışı yanıt için kovalıyor.

---

## [0.8.0] — Cycle 8: Üretim Çekirdeği (Mayıs 2026)

Production deploy hazırlığı: auth, secret hygiene, ML evaluation,
%95 coverage, security audit toolchain.

### Added
- **JWT auth + bcrypt** (`603c264`): bearer token, password hashing,
  24h TTL.
- **Alembic ilk migration** (`d6c3e22`): 14 tablonun tamamını kapsayan
  autogenerate baseline.
- **Nginx + Let's Encrypt reverse proxy** (`b139154`): HTTPS production
  deploy şablonu, otomatik sertifika alma, opsiyonel PostgreSQL profili.
- **Slowapi rate limit** (`05000a9`): tüm write endpoint'leri rate
  limited; `Retry-After` + `X-RateLimit-*` header'lar.
- **Sensör arşivleme** (`fca5e7c`): `SensorReadingMonthlyAggregate` +
  APScheduler haftalık Sunday 03:30 cron, idempotent merge.
- **Security audit toolchain** (`d011017`): `bandit` (Python source CWE)
  + `pip-audit` (PyPI advisory CVE) GitHub Actions workflow,
  PR + push + Pzt 06:00 cron + manuel.
- **Edge-case test bundle** (`c0a40b0`): 1MB JSON, unicode/emoji
  injection, oversized image upload, SQL injection deneme stringi.
- **Slider-based pagination** (`290ff7e`): "ilk 20" / "son 20" yerine
  50/sayfa slider.

### Changed
- **Tier-1 polish batch** (`cfe752b`): `_clean_tr` for-loop →
  `str.translate` + modül-seviyesi `_TR_ASCII_MAP`; `model_performance`
  magic numbers → isimli sabitler; Pillow 14 hazırlığı (`hsv.getdata()`
  → `np.asarray(...).reshape(-1, 3)`).
- **Ruff rule set genişletildi** (`d011017`): DTZ, ERA, PT, RET, C4,
  PIE, PERF, TRY, S subset kümeleri aktif.
- **N+1 query fix** (`db0b144`): `/analytics/summary` 1+2N → 2 query.

### Fixed
- **Production stability** (`6de038d`): scheduler bug, hardcoded
  secrets, env-driven CORS.

### Security
- **Production validator** (`cfe752b`): default secret'larla production
  başlatma engellendi; dev/staging permissive.

---

## [0.7.0] — Cycle 7: İzleme & Raporlama (Nisan – Mayıs 2026)

### Added
- **PDF/Excel rapor export** (`e639f53`): FPDF + pandas, `ReportService`,
  `/analytics/export/{pdf,excel}` endpoint'leri.
- **Historical comparison endpoints** (`e639f53`).
- **MQTT entegrasyonu** (`785b3f5`): `paho-mqtt`, sensor stream
  simülatörü.
- **Plant disease model** (`2ee9e8c`): HSV-tabanlı heuristic CNN +
  ONNX hazır yapı.
- **Auth + Plants + Alerts sayfaları** (`107e85e`): frontend (Ecenur).
- **17 bitki gübreleme** (`feab97a`): NPK önerisi 17 bitki türüne
  genişletildi.
- **Docker + Makefile + pre-commit** (`1772717`).
- **Drift detection + deep health + metrics** (`7f236d9`):
  `shiftSession` (Cycle 6) kapanış paketi.

### Changed
- **Frontend UX cila** (`d6a1607`, `e215862`, `eb420bc`, `14bdbab`):
  Filiz maskotu, count-up animasyonu, hover glow, badge pulse,
  saatlik selamlamalar, çiftçi-dostu dil, scroll-table, jargon arınma.
- **Python 3.12 migrasyonu** (`ed68129`): `datetime.UTC` + UP017.

---

## [0.6.0] — Cycle 6: İleri Modeller & Ölçeklendirme (Nisan 2026)

### Added
- **Analytics dashboard** (`1fb0d77`, `b00ff95`).
- **Loguru + APScheduler** (`0bf6941`): structured logging + background
  task scheduler.
- **Ulusal ölçek** (`89924df`): 81 il, 7500+ kayıt mega veritabanı,
  3 yeni tablo.
- **Function-based layout** (`7909667`): proje function-based mimariye
  reorganize edildi.

---

## [0.5.0] — Cycle 5: API Güvenlik & Veri Hazırlığı (Mart – Nisan 2026)

### Added
- **Rate limit + logging + exception handling** (`2cee3a5`).
- **Alembic migration + seed data** (`14ae1b8`): 3 çiftlik / 10 sensör /
  300+ okuma, DB index optimizasyonu.
- **Dashboard SPA + integration tests** (`0c1d390`): 114 test, %91
  coverage.

---

## [0.4.0] ve öncesi — Temel Mimari (Şubat – Mart 2026)

Cycle 1–4'te proje temelleri atıldı: gereksinim toplama, veri seti
analizi, UI/UX tasarımı, ilk API altyapısı, sulama optimizasyon modeli,
dashboard UI. Detay: [`projeakisi.md`](projeakisi.md).
