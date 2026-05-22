# 🌾 SFDAP — Akıllı Tarım Veri Analizi Platformu

Çiftlik sensör verileri, hava durumu, sulama, gübreleme ve bitki sağlığı için entegre bir veri analizi ve karar destek platformu. Backend: FastAPI + SQLAlchemy. Frontend: tek-sayfa SPA (Vite) + Leaflet harita.

[![CI](https://github.com/Ohualtex/Smart_Farming_Data_Analysis_Platform/actions/workflows/ci.yml/badge.svg)](https://github.com/Ohualtex/Smart_Farming_Data_Analysis_Platform/actions)
[![Security](https://github.com/Ohualtex/Smart_Farming_Data_Analysis_Platform/actions/workflows/security.yml/badge.svg)](https://github.com/Ohualtex/Smart_Farming_Data_Analysis_Platform/actions/workflows/security.yml)
[![A11y](https://github.com/Ohualtex/Smart_Farming_Data_Analysis_Platform/actions/workflows/a11y.yml/badge.svg)](https://github.com/Ohualtex/Smart_Farming_Data_Analysis_Platform/actions/workflows/a11y.yml)
![Python 3.12+](https://img.shields.io/badge/Python-3.12+-blue)
![Coverage 95%](https://img.shields.io/badge/Coverage-95%25-brightgreen)
![Tests 622+32](https://img.shields.io/badge/Tests-622%20backend%20%2B%2032%20frontend-success)

---

## ⚡ Hızlı Başlangıç

```bash
git clone https://github.com/Ohualtex/Smart_Farming_Data_Analysis_Platform.git
cd Smart_Farming_Data_Analysis_Platform
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env                                # default'lar dev için hazır
python database/seed_data.py                        # demo veri (opsiyonel)
make run                                            # uvicorn → http://localhost:8000
```

Açılan adresler:
- **Dashboard:** http://localhost:8000/dashboard/
- **Swagger API:** http://localhost:8000/docs
- **Health probe:** http://localhost:8000/api/health/deep

---

## 👥 Kullanıcı Rolleri

Sistem dört farklı kullanıcı türünü destekler — her rol kendi dashboard görünümü ve API kapsamıyla gelir.

| Rol | Erişim kapsamı | Tipik kullanım |
|:--|:--|:--|
| 🧑‍🌾 **Çiftçi** | Yalnız kendi çiftliği, tarlaları, sensörleri | Tarla başına sulama önerisi, yaprak hastalığı tespiti, gübre takvimi |
| 🛠️ **Geliştirici** | API key + Swagger + test endpoint'leri | Sistem entegrasyonu, IoT cihaz bağlama, fuzz/load test |
| 🏛️ **Genel Gözetmen** | Tüm çiftliklere read-only, harita + analytics | Sistem-geneli gözetim ve raporlama (tüm çiftlikler, salt-okunur) |
| 👑 **Admin** | Tüm sistem + kullanıcı yönetimi + audit log | Operasyonel kontrol, rol atama, kritik alert yönetimi |

> **`rebuild` branch — aktif geliştirme:** 4-rollü RBAC, rol-spesifik dashboard'lar, eyleme yönelik akışlar ve onboarding burada inşa ediliyor. Detaylı plan: [`docs/REBUILD_ROADMAP.md`](docs/REBUILD_ROADMAP.md).

---

## 🏗️ Mimari

```
   [SPA: HTML + Vite + Chart.js + Leaflet]
                    ⇅
   [FastAPI routers] → [services] → [SQLAlchemy ORM] → [SQLite / PostgreSQL]
            │
            ├─ JWT bearer + bcrypt + jti blacklist
            ├─ 4-rollü RBAC (rebuild branch)
            ├─ Rate limiting (slowapi)
            ├─ Defense-in-depth headers (CSP / HSTS / XFO / XCTO / Referrer / Permissions)
            ├─ Sentry + Prometheus + structured JSON log
            └─ APScheduler (haftalık archive, günlük hava verisi fetch)
```

**Ölçek:** 15 router · ~65 endpoint · 15 ORM tablo · çiftçi-odaklı demo seed (birkaç çiftçi · çoklu çiftlik/tarla · 17 bitki türü referansı).

**Diyagram + ER şeması:** [`docs/architecture.md`](docs/architecture.md) · [`database/sfdap_schema.sql`](database/sfdap_schema.sql)

---

## 📡 API

- **Swagger UI:** http://localhost:8000/docs (15 router, OpenAPI 3.1 contract)
- **OpenAPI JSON:** http://localhost:8000/openapi.json
- **Endpoint + auth + örnek istekler:** [`docs/api/API_Kullanim_Kilavuzu.md`](docs/api/API_Kullanim_Kilavuzu.md)

---

## 🧪 Test ve Kalite

| Kategori | Değer | Komut |
|:--|:--|:--|
| Backend test | **622** geçer | `make test` |
| Frontend test | **32** geçer (Vitest + jsdom) | `cd frontend && npm test` |
| Coverage | **%95.04** (eşik %80) | `make test` |
| Lint + format | Ruff temiz (17 kural grubu) | `make lint && make format` |
| Source security | bandit medium+ → 0 issue | `make audit` |
| Dependency CVE | pip-audit (haftalık cron) | `make audit` |
| Property-based fuzz | Schemathesis (auth-aware GET/POST/PATCH/DELETE) | `make fuzz` |
| A11y | axe-core WCAG 2.1 AA strict | `make a11y` |
| Local CI parity | lint + test + audit | `make ci` |

**CI/CD:** 4 GitHub Actions workflow — `ci.yml` (lint + test + migrations + fuzz + frontend-test), `security.yml` (bandit + pip-audit), `a11y.yml` (axe-core).

Kapsamlı kalite denetim raporu: [`docs/QUALITY_AUDIT.md`](docs/QUALITY_AUDIT.md)

---

## 🌐 Production Deploy

Docker + nginx reverse proxy + Let's Encrypt SSL şablonu. Kurulum adımları: [`docs/setup/PROD_DEPLOY.md`](docs/setup/PROD_DEPLOY.md)

```bash
docker compose up -d nginx api                          # API + reverse proxy
docker compose --profile letsencrypt run --rm certbot \ # SSL cert
  certonly --webroot -w /var/www/certbot ...
docker compose --profile postgres up -d db              # PostgreSQL'e geçiş
docker compose exec api alembic upgrade head            # Migration uygula
```

Production guard'ları (`app/config.py`): `ENVIRONMENT=production` iken default API_KEY / SECRET_KEY / wildcard veya localhost CORS origin'ler fail-fast hata fırlatır.

---

## 📋 Sprint Durumu

- **Şu an:** `rebuild` branch — REBUILD sprint (18 – 30 May 2026, solo)
- **Akademik teslim:** 7 Haziran 2026
- **Aktif yol haritası:** [`docs/REBUILD_ROADMAP.md`](docs/REBUILD_ROADMAP.md) — 7 faz × 13 gün
- **Geçmiş cycle'lar + ekip dağılımı:** [`projeakisi.md`](projeakisi.md)

---

## 📚 Anahtar Dokümanlar

| Doküman | Açıklama |
|:--|:--|
| [`CHANGELOG.md`](CHANGELOG.md) | Sürüm notları (Keep a Changelog formatında) |
| [`docs/REBUILD_ROADMAP.md`](docs/REBUILD_ROADMAP.md) | Aktif rebuild planı (7 faz × 13 gün) |
| [`docs/FINAL_REPORT.md`](docs/FINAL_REPORT.md) | Cycle 9 akademik teslim raporu |
| [`docs/architecture.md`](docs/architecture.md) | Sistem mimarisi + Mermaid diyagramları |
| [`docs/api/API_Kullanim_Kilavuzu.md`](docs/api/API_Kullanim_Kilavuzu.md) | API kullanım rehberi |
| [`docs/setup/PROD_DEPLOY.md`](docs/setup/PROD_DEPLOY.md) | Production deploy kılavuzu |
| [`docs/CYCLE_8_RETROSPECTIVE.md`](docs/CYCLE_8_RETROSPECTIVE.md) | Cycle 8 retrospective |
| [`docs/QUALITY_AUDIT.md`](docs/QUALITY_AUDIT.md) | Kalite denetim raporu |
| [`docs/demo_script.md`](docs/demo_script.md) | Sunum demo akışı |

---

## 👥 Ekip

5 kişilik öğrenci ekibi: Scrum Master + 4 geliştirici. Detaylı katkı dağılımı için: [`CONTRIBUTORS.md`](CONTRIBUTORS.md) · cycle bazlı görev tablosu: [`projeakisi.md`](projeakisi.md)

## 📜 Lisans

MIT — bkz. [`LICENSE`](LICENSE)
