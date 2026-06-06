# Changelog

Bu proje [Keep a Changelog](https://keepachangelog.com/tr/1.1.0/) formatını ve
[Semantic Versioning](https://semver.org/spec/v2.0.0.html) sözleşmesini izler.

Sürümler proje cycle'larına eşlenir: Cycle 5 → 0.5, Cycle 6 → 0.6, Cycle 7 → 0.7,
Cycle 8 → 0.8, `shiftFinal` bridge sprint → 0.9. Cycle 9 (akademik teslim) → 1.0.

---

## [Unreleased]

_Henüz yayınlanmamış değişiklik yok._

## [1.0.0] — 2026-06-07 — Cycle 9 akademik teslim

`shiftFinal` bridge sprint 17 Mayıs'ta kapandı (`v0.9.0-pre-rebuild`
tag'i atıldı). 18 Mayıs'ta `rebuild` branch'inde REBUILD sprint başladı;
çiftçi-odaklı yeniden yapılandırmanın 6 fazı + 81-il iddiası temizliği
tamamlandı. Ardından `main` üzerinde cila turları (fixroll), hoşgeldin
(welcome) ekranı + gün-gece temalı giriş akışı ve repo-geneli doküman
senkronu yapıldı. **1.0.0**, Cycle 9 akademik teslim sürümüdür
(`pyproject.toml` ile hizalı).

---

### REBUILD Faz 2-6 + 81-il temizliği (19-22 May 2026, ✅)

Faz 1 (RBAC) sonrası çiftçi-odaklı ürün akışının tamamı. Demo persona
"Çiftçi Ahmet"in 5 sorusu artık uçtan uca cevaplanıyor.

#### Faz 2 — "Çiftliğim" dashboard (`6ccf441`, `45f5e39`)
- `GET /api/dashboard/summary` — rol-aware tek-ekran özet (scope `user`|`system`):
  son 24sa toprak nemi (dry/optimal/wet), son sulama, açık uyarı sayım+severity,
  son hastalık tanısı. 7 query × 1 round-trip.
- Frontend: 4 metric kart + hero stats; `apiAuth()` Bearer helper, header
  user-badge (rol-renkli), `/me` `owned_farms_count`; Hesabım sayfası +
  `PATCH /api/auth/me/password` (current-password doğrulamalı).

#### Faz 3 — Tarla detay sayfası (`2f307a5`, `b1290dd`)
- `GET /api/fields/{id}` (aggregated: çekirdek+çiftlik+crop+sensörler[son okuma]+
  sulama/hastalık/toprak geçmişi+açık uyarılar) + `/readings` (nem trend serisi).
- Frontend: "Tarlalarım" + parametrik `#field/{id}` detay; yaprak foto upload →
  tanı demo akışının merkezi.
- Bonus: Faz 1'den beri flaky `test_tampered_jwt_rejected` deterministik düzeltildi
  (payload tampering; son-char base64url eşdeğerliği kök nedeni).

#### Faz 3.5 — Ön panel (auth gate) + admin kullanıcı yönetimi (`ad5d8a5`, ...)
- Giriş yapmadan app görünmez: full-screen `#landing` (login öncelikli, kayıt
  gizli toggle); `_applyAuthGate` tek kaynak.
- Admin-only kullanıcı yönetimi: `GET/POST/DELETE /api/auth/users`,
  `PATCH /users/{id}/password` (admin reset). Liste `password_hash` sızdırmaz,
  `owned_farms_count` group-by N+1 önler. Self-delete + çiftlik-sahibi delete 409.
  Frontend admin "Kullanıcılar" sayfası (rol değiştir/şifre/sil/oluştur).

#### Faz 4 — Eyleme yönelik CRUD UI (`c738eb1`, `3ddd018`, `55880b1`)
- Çiftlik/Tarla CRUD: `POST/PATCH/DELETE /api/farms/{id}` + `/api/fields`
  (cascade guard: tarlalı çiftlik / sensörlü tarla → 409).
- **irrigation.py Faz 1 RBAC açığı kapatıldı** — `POST /schedules` X-API-Key →
  Bearer + field ownership; `GET /schedules` artık auth+scope'lu. Yeni
  `PATCH /schedules/{id}/status` (pending→completed/cancelled).
- Frontend: çiftlik/tarla ekle-düzenle-sil formları; sulama önerisini "Onayla
  ve programa ekle"; durum butonları.

#### Faz 5 — Per-user bildirim akışı (`fd9907b`, `f5d060e`)
- `POST /api/alerts/check` — kapsamdaki tarlaları tara, dedup'lı otomatik uyarı
  üret (düşük nem → low_moisture[kritik<%20], 14g hastalık yoksa → disease_reminder).
- Frontend: header 🔔 bildirim çanı (açık uyarı sayısı + dropdown + hızlı çöz +
  "Kontrol et").

#### Faz 6 — Onboarding + per-user demo seed (`ed7f1c2`, `cd02640`)
- `POST /api/onboarding/demo` — boş hesaba tek-tık örnek çiftlik zinciri
  (idempotent; çiftliği varsa 409).
- Frontend: boş hesap onboarding banner ("İlk çiftliğimi ekle" / "Demo verisi yükle").

#### 81-il / ulusal-ölçek iddiası temizliği (`37ae17e` + docs)
- "81 il / 7500+ kayıt / bakanlık paneli" ileriye-dönük çerçeve **çiftçi-odaklı**
  yapıya çekildi (Swagger, README, FINAL_REPORT özet/persona, frontend UI).
- `database/seed_data.py` mega 81-il seed → çiftçi-odaklı demo seed (5 kullanıcı,
  3 çiftlik, 6 tarla). Geçmiş cycle kayıtları kasıtlı korundu.

#### Verification (Faz 6 sonu)
- **pytest 622/622** · ruff check+format temiz · bandit medium+ 0 · **vitest 32/32**.
- Her faz uvicorn smoke ile uçtan uca doğrulandı (RBAC matrisi + akışlar).

---

### REBUILD Faz 1 — 4-rol RBAC + per-user data isolation (18 May 2026, ✅)

Çift commit ile teslim edildi:
`5a48c21` (Adım 1-8: altyapı + farms + sensors) ve `c2051c8` (Adım 9-14:
kalan 6 router + alerts audit fix). 14 adım × 2 commit, 23 dosya,
+1,426 / -426 satır. Hedef: her endpoint'in `farmer` rolü için
kendi `User.id`'sine bağlı veri ile sınırlandırılması; `developer`/
`overseer` tüm sistemi okur; `admin` sistem genelinde tam yetkili.

#### Added
- **`USER_ROLES = ("farmer", "developer", "overseer", "admin")` + `DEFAULT_USER_ROLE = "farmer"`**
  (`app/models/models.py`): rol enumeration'ı tek kaynak olarak modeller
  modülünde. `User.role` kolonu `nullable=False`, `server_default="farmer"`,
  `index=True` hardenedi.
- **Alembic migration `b1c2d3e4f5a6_rbac_role_check_constraint_and_index.py`**:
  `batch_alter_table` ile SQLite-uyumlu CHECK constraint (`role IN
  ('farmer','developer','overseer','admin')`), `ix_users_role` index,
  NULL/empty role'leri `farmer`'a backfill. PostgreSQL'de native
  `ALTER TABLE ... ADD CONSTRAINT` kullanır.
- **`app/middleware/rbac.py`** (yeni): RBAC helper modülü.
  - `_BYPASS_ROLES = frozenset({"admin", "overseer", "developer"})` —
    okuma için per-user filter atlanır.
  - `_WRITE_ROLES = frozenset({"admin", "farmer"})` — sadece bu iki
    rol DB'ye yazabilir; overseer/developer read-only.
  - `scope_to_user(query, user, model, fk="user_id")` — generic
    per-user filter.
  - `assert_farm_ownership(db, farm_id, user)` /
    `assert_field_ownership(db, field_id, user)` /
    `assert_sensor_ownership(db, sensor_id, user)` — kayıt-bazlı
    sahiplik doğrulama (404 vs. 403 ayrımı korunur).
  - `scope_sensors_to_user(query, user)` — sensor → field → farm →
    user.id zinciri için optimize JOIN.
  - `is_write_allowed(user) -> bool`.
- **`PATCH /api/auth/users/{id}/role`** — admin-only role değişimi.
  Self-demotion guard (409 Conflict): admin kendi rolünü farmer'a
  düşüremez. `UserRoleUpdateRequest` Pydantic schema, `UserRole =
  Literal["farmer", "developer", "overseer", "admin"]` type alias
  (runtime `assert set(UserRole.__args__) == set(USER_ROLES)`).
- **`get_current_user_or_403`** alias + `current_user_optional` +
  `require_role(*roles)` FastAPI Depends factory (auth.py).
- **`CurrentUserResponse` genişletildi**: `phone` + `owned_farms_count`
  alanları. `/api/auth/me` artık `func.count(Farm.id)` ile çiftlik
  sayısını single-query döndürür.
- **`tests/conftest.py` rol fixture'ları**: `anon_client`, `farmer_client`,
  `developer_client`, `overseer_client`, `admin_client`. Her biri
  `_make_role_client(client, db, role)` helper'ı üzerinden ayrı user
  oluşturur ve Bearer token'i headers'a ekler. Base `client` fixture
  artık default admin user yaratır ve `Farm(id=1)` + `Field(id=1)`'i
  `region="__internal__"` ile ön-seed eder — legacy testler
  (`field_id=1`, `farm_id=1` hardcoded) RBAC sonrası 404 dönmesin diye.
- **`tests/test_rbac_fixtures.py`** (yeni) — 7 fixture smoke test
  (anon 401, her rol için `/me` doğrulama, multi-rol tek session).
- **`tests/test_farms.py`** — 23 test: 13 mevcut testin `admin_client`'a
  migrasyonu + 10 yeni RBAC davranış testi (`TestAnonAccess`,
  `TestFarmerScope`, `TestOverseerAndDeveloperScope`).
- **`tests/test_sensors.py`** — 18 test, `admin_with_field` fixture'ı
  üzerinden RBAC ownership doğrulaması.

#### Changed
- **Tüm 8 router Bearer + RBAC'a geçirildi**:
  `farms` (Adım 7), `sensors` (Adım 8), `weather` (Adım 9),
  `irrigation` (Adım 10), `plants` (Adım 12), `alerts` (Adım 13),
  `analytics` (Adım 14). Eski `verify_api_key` Depends'leri kaldırıldı.
  _İstisna:_ `model_performance` (dev/ops metrik endpoint'leri) bilinçli olarak
  `X-API-Key` (`verify_api_key`) ile korunmaya devam eder.
  Write endpoint'leri `_require_write(user)` helper'ı ile koruma
  altında — overseer/developer 403 alır. Public kalan endpoint'ler:
  `GET /api/health`, `POST /api/irrigation/predict` (stateless ML),
  `/api/fertilizer/*` (stateless calculator — Faz 4'te
  `FertilizerRecommendationLog` persist ile ownership eklenecek).
- **Analytics router**: `/api/analytics/*` 3 endpoint admin/overseer/
  developer only; farmer için "Bugünün durumu" görünümü Faz 2'de
  ayrı `/api/dashboard/farmer` endpoint'i olarak gelecek.
- **`tests/test_auth.py` baştan yazıldı**: eski X-API-Key paradigm'i
  JWT RBAC'a çevrildi (6 test: `TestUnauthenticatedWriteBlocked`,
  `TestAdminWriteAuthorized`, `TestStillPublicEndpoints`).
- **6 dolaylı test dosyası**: `test_analytics.py`, `test_auth_backend.py`,
  `test_integration.py`, `test_plants.py`, `test_security.py`,
  `test_security_headers.py`, `test_weather_service.py` — hardcoded
  `farm_id=42/99/999` ve `field_id=42/7` değerleri default `1`'e
  çekildi (RBAC sonrası conftest default farm/field'a uyum).

#### Removed
- **`verify_api_key` legacy dependency** — X-API-Key header kontrolü
  Cycle 5'ten beri yardımcı koruma katmanıydı; JWT + RBAC tek-source
  yetki olduğu için son-kullanıcı router'larından kaldırıldı. Hâlâ
  deployment'larda environment variable olarak duruyor (geriye dönük
  config uyumluluğu); router'lar arasında yalnız `model_performance`
  (dev/ops metrik endpoint'leri) bunu bilinçli olarak okumaya devam eder.

#### Fixed
- **`PATCH /api/alerts/{alert_id}` `is_resolved: None` 500 audit bug**
  (Adım 13, `c2051c8`): Schemathesis fuzz `is_resolved=None` payload
  gönderdiğinde eski kod DB'ye NULL yazıyordu; `SystemAlertResponse.is_resolved`
  (`bool`) Pydantic validation 500 `ResponseValidationError`
  fırlatıyordu. Fix: `payload.model_dump(exclude_unset=True,
  exclude_none=True)` — explicit `None` değerler artık "no-op"
  sayılır, partial update kontratı "verilen alanlar" semantiğine
  sadık kalır. Aynı fix `severity=None` ve `message=None` için de geçerli.

#### Security
- **4-rol erişim kontrolü** — `farmer` rolündeki kullanıcı artık
  yalnız `farms.user_id == farmer.id` koşulunu sağlayan veri
  görür/yazar. `developer` ve `overseer` tüm sistemi okur ama
  yazamaz (read-only audit/integration). `admin` sistem genelinde
  tam yetkili. CHECK constraint + index DB-seviyesinde sızıntıyı
  engeller.
- **Admin self-demotion koruması** — `PATCH /users/{id}/role` admin'in
  kendi rolünü düşürmesini 409 Conflict ile reddeder; "sistem'de
  hiç admin kalmama" race condition'ı önlenir.

#### Verification
- **pytest**: 499/499 pass (önceki run'da flaky olan
  `test_tampered_jwt_rejected` da geçti — Adım 17 öncesi).
- **ruff**: `check` + `format --check` temiz.
- **bandit**: 0 issue.
- **Per-rol uvicorn smoke (Adım 17)**: port 8765'de canlı
  matriks — 4 rol × 23 senaryo. 23/23 etkili geçti (2 "fail"
  FastAPI'nin body validation'ı RBAC Depends'ten önce çalıştırmasından
  kaynaklı 422 vs. 403 sırasıydı; davranış doğru).
- **Schemathesis fuzz**: `PATCH /api/alerts/{id}` artık `is_resolved=None`
  payload'ı için 200 döner (önceden 500).

---

### shiftFinal kapanış entry'leri (13 – 17 Mayıs 2026)

Aşağıdaki blok shiftFinal bridge sprint'in kapanış commit'lerinden
derlenmiş orijinal entry setidir — `v0.9.0-pre-rebuild` tag'i bu
durumdaki HEAD'i (`95674ec` merge) işaret eder.

### Added
- **`docs/REBUILD_ROADMAP.md`** — kullanıcı-odaklı yeniden yapılandırma
  için 7-faz × 13-gün roadmap (REBUILD sprint, 18–30 May). Solo iş
  (Miraç); ekip Cycle 9'da yalnız sunum + rapor üretir. Faz 1
  (**4-rol RBAC**: farmer/developer/overseer/admin + per-user data
  isolation), Faz 2 (Çiftliğim dashboard + rol-spesifik görünümler),
  Faz 3 (Tarla detay sayfası), Faz 7 (doc + sunum) zorunlu. Geri-dönüş tag'i
  `v0.9.0-pre-rebuild`; branch `rebuild` (shiftFinal kapanışından
  ayrılır). Demo hedefi: Ahmet senaryosu (kayıt → demo seed → "Tarla A
  susuz" → sulama onay → yaprak foto → hastalık tanı → kayıt) 3.5 dakikada.
- **FINAL_REPORT §2 (Hedefler/Kapsam) persona-odaklı yeniden yazıldı** —
  hedef kullanıcı Çiftçi Ahmet açıkça tanımlandı, ikincil persona bakanlık
  analisti. RBAC + bildirim akışı işlevsel olmayan hedeflere eklendi.
  Kapsam dışı (Cycle 10+) listesi netleşti.
- **projeakisi.md REBUILD bölümü** — shiftFinal ile Cycle 9 arasına
  ayrı sprint olarak eklendi. shiftFinal kapanış-ifadesi yazıldı.
  Cycle 9 yeniden çerçevelendi: ekip görevleri **yalnız sunum + rapor**
  (Ayşe sunum slaytları, Ecenur görsel tasarım, Mehmet Q&A senaryoları,
  Emirhan final rapor yazımı). Teknik geliştirme yalnız REBUILD
  branch'inde, Miraç solo.
- **C-batch test derinleşmesi**: `tests/test_jti_blacklist.py` (9 test)
  jti payload kontratı, blacklist invalidation, legacy-token toleransı
  ve tampered signature reddini sabitliyor. `frontend/tests/map.test.js`
  (18 test) `lib/map.js`'in saf yardımcıları (`_escapeHtml`,
  `_farmPopupHtml`, `_markerOptions`, `REGION_COLORS` paleti) için XSS
  + region renk kontratı + DI smoke test'leri.
- **FINAL_REPORT §13 Karşılaşılan Zorluklar** bölümü dolduruldu —
  shiftFinal'da yakalanan 4 production-risk bug detaylı kök neden +
  düzeltme yazıldı (int64 overflow ailesi 8 bug, trackpad inertia,
  JWT blacklist test sızıntısı, production CORS guard).

### Changed
- **`main.js` → ES module entry-point (B-batch)**: `frontend/index.html`
  artık `<script type="module" src="src/main.js">` kullanıyor. Drift
  TODO kapandı:
  - `_skeletonCards / _skeletonRows / _skeletonBlock / _setBusy`
    main.js'ten silindi → `import { ... } from "./lib/skeleton.js"`
    tek kaynak (Vitest 14 testi zaten bu modülü izliyordu).
  - Türkiye haritası kodu (`REGION_COLORS`, `_ensureMapInstance`,
    custom wheel handler, `loadMap`) `frontend/src/lib/map.js`'e
    çıkarıldı (~170 satır). `loadMap({api})` ile dependency
    injection — testlerde fetch + Leaflet mock'lanabilir.
  - `main.js` sonunda **window-bridge**: `Object.assign(window, {...})`
    ile 12 inline `on*` handler hedefi (`navigate`, `toggleSidebar`,
    `loadSensors`, `loadIrrigation`, `predictIrrigation`,
    `recommendFertilizer`, `fertilizerSchedule`, `analyzePlantImage`,
    `loadAlerts`, `doLogin`, `doRegister`, `doLogout`) + 3 yardımcı
    (`showToast`, `resolveAlert`, `loadSensorDetail`) global'e expose
    edildi. ES module scope'ta function decl global'e gitmediği için
    bu köprü inline handler kontratını koruyor; tamamen event
    delegation'a geçince CSP `'unsafe-inline'` script-src'ten
    kaldırılabilir.
- `tests/test_frontend_a11y.py` güncellendi: skeleton helper kontrolü
  artık `src/lib/skeleton.js`'i (`export function`) tarar; yeni test
  `main.js`'in lib import satırını da doğrular.

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
