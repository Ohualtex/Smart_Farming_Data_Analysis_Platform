# 🔍 SFDAP Kalite Denetimi

> **Kapsam:** Tüm repo (`app/`, `tests/`, `alembic/`, `docs/`, `scripts/`, `frontend/`, CI).

Bu doküman, repo'nun mevcut kalite durumunu fotoğraflar ve hâlâ açık olan teknik borçları tier'larla önceliklendirir. Üretim çekirdeği (auth backend, rate limiting, migration, N+1 fix, HTTPS) tamamlandı; çapraz cila ve gözlemlenebilirlik paketleri (Sentry/Prometheus, frontend a11y/Vite, backup/restore, fuzz/axe-core CI) ardından geldi.

---

## 📊 Genel Sağlık Tablosu

> **Güncel snapshot:** fixroll v1-v7 sonrası (30 May 2026). Tarihsel
> progresyon parantez içinde korunmuştur.

| Boyut | Değer | Hedef | Durum |
|:--|:--:|:--:|:--:|
| **Test sayısı** | **650** backend + **59** frontend (425 → 485 shiftFinal → 622 REBUILD → 650 fixroll) | — | ✅ |
| **Coverage** | **%95** | %95+ | ✅ Hedef geçildi |
| **Ruff (genişletilmiş kural seti)** | 0 hata | 0 | ✅ |
| **Bandit (medium+ severity)** | 0 issue | 0 | ✅ |
| **pip-audit** | (CI) | 0 CVE | ⏳ CI'da koşar |
| **Schemathesis fuzz** | 25 GET endpoint × ~10 case = 250 fuzz çağrısı | 0 server error | ✅ Bug bulundu + fix'lendi |
| **axe-core CI** | WCAG 2.0 + 2.1 A/AA, weekly cron | 0 critical violation | ⏳ İlk run sonrası kalan warning'lar değerlendirilir |
| **CI/CD pipeline** | 3 workflow (ci + security + a11y) | — | ✅ |
| **CI job sayısı** | 4 (lint + test + migrations + fuzz) + 2 security + 1 a11y | — | ✅ |
| **Endpoint sayısı** | 66 (15 router; REBUILD dashboard/fields/onboarding + CRUD + RBAC) | — | ✅ |
| **ORM tablo sayısı** | 15 (initial 14 + aggregate) | — | ✅ |
| **Alembic migration zinciri** | 2 revision (initial + aggregate) | — | ✅ |
| **Frontend yapısı** | ES module split (`index.html` markup + `src/main.js` + `src/styles/main.css` + `src/lib/`) | bundling scaffold | ✅ Vite + a11y + skeleton |
| **Vite + axe-core CLI** | `frontend/package.json` scaffolded | — | ✅ |
| **Dış bağımlılık güncelliği** | 7 minor outdated | major-stable | 🟡 |

## 🛡️ Güvenlik Durumu

### Kullanılan tarayıcılar
| Araç | Kapsam | Tetikleyici |
|:--|:--|:--|
| **Ruff (S kuralları)** | Lokal + CI lint | Her commit |
| **Bandit** | `app/` Python source | pre-commit + CI security.yml |
| **pip-audit** | `requirements.txt` CVE | CI security.yml + haftalık cron |

### Bilinen kabuller (whitelisted)
- `S105` — `token_type = "bearer"` gibi protokol sabitleri
- `S106` — Test/dev API key argümanları
- `S311` — `random.*` kriptografik olmayan kullanımlar (synthetic data)

### Güvenlik mimarisi
- `X-API-Key` header — yazma endpoint'leri
- JWT (HS256) + bcrypt — kullanıcı auth backend
- Rate limit (slowapi, 30/min STRICT, 10/min AUTH) — 17 endpoint
- CORS — env-driven origin listesi
- `_validate_production` fail-fast — prod'da default secret kullanımı engellendi

---

## 🟢 Kapatılan Teknik Borçlar

| Borç | Önce | Sonra | Commit |
|:--|:--|:--|:--|
| Alembic boş migration | `pass` (12 tabloluk yanlış filename) | 14 tablo + aggregate (333+95 satır) | `d6c3e22` + new |
| Auth backend | sha256 + dict token | bcrypt + HS256 JWT + blacklist | `603c264` |
| Rate limiting | import edilmiş, bağlanmamış | 17 endpoint × decorator | `05000a9` |
| Analytics N+1 | 1 + 2N WeatherData query | 1 + 1 query (sabit) | `db0b144` |
| HTTPS termination | yok (port 8000 host'a açık) | nginx reverse proxy + Let's Encrypt | `b139154` |
| Coverage | %86 (zayıf: scheduler %50, mqtt %54) | %94.78 (90+ yeni test) | `cf35a63` + `15c154e` + Step 1/3 paketleri |
| Sensor archiving | yok | aylık aggregate + haftalık cron | `fca5e7c` |
| Audit dokümanı | yok | bu rapor | (yeni commit) |
| Tier 1 lint (DTZ005, ERA001, D100) | 2 ihlal | 0 | `4c796eb` |
| Ruff config | 8 kural seti | 17 kural seti (S, DTZ, TRY, vs) | (yeni commit) |
| Pre-commit hooks | trailing/EOF + ruff 0.3 | + bandit + ruff 0.13 + private-key detect | (yeni commit) |
| CI/CD | sadece lint + test | + security audit + migration smoke | (yeni commit) |

---

## 🟡 Açık ve Kapatılan Teknik Borçlar

### Tier A — Yüksek değer

| # | Konu | Durum |
|:--|:--|:--:|
| A1 | Coverage %95+ resmî tutuş | ✅ Karşılandı (%95.04); CI'da `fail_under=80` kilidi (gerçek değer %95+). |
| A2 | Sentry + Prometheus + structured logging | ✅ Tamamlandı (`e6259ae`) — Sentry, 4 Prometheus metric, JSON log + request_id. |
| A3 | Vite bundling + a11y (ARIA, WCAG AA) + skeleton loaders | ✅ Tamamlandı (`02d1359`) — Vite scaffold, 28 a11y testi, 4 JS skeleton helper, skip-link + landmark. |
| A4 | DB pool tuning + backup/restore script + cron | ✅ Tamamlandı (`2a889f8`) — pool tuning + `backup.sh`/`restore.sh` + Makefile + 7 test. |
| A5 | `_clean_tr` refactor + magic numbers → constants | ✅ Tamamlandı — `str.maketrans` + 5 constant. |
| A6 | Pillow 14 hazırlığı (`getdata` → numpy) | ✅ Tamamlandı — `np.asarray().reshape()`. |
| A7 | Schemathesis fuzz + axe-core CI + gerçek bug fix | ✅ Tamamlandı (`7e49bef`) — 25 GET endpoint fuzzlandı, `skip=int64_max` 500 bug'ı `MAX_SQLITE_INT`/`MAX_SKIP` ile fix'lendi, `.github/workflows/a11y.yml` eklendi. |

### Tier B — Orta değer

| # | Konu | Durum |
|:--|:--|:--:|
| B1 | `app/config.py` %78 coverage — production fail-fast path test | ✅ Tamamlandı (12 yeni test). |
| B2 | Frontend (`index.html`) — 2 972 satır tek dosya, monolitik | 🟡 Vite scaffold + a11y/skeleton refactor tamamlandı; ES module split kademeli devam edecek. |
| B3 | `ANN001/ANN201` — public API'lerde return/arg type hints eksik (~740 ihlal) | ⏳ Kademeli geçiş. |
| B4 | `D101/D102` — public class/method docstring eksik (~265 ihlal) | ⏳ Kademeli geçiş. |
| B5 | Edge case test paketi — 1MB JSON, unicode injection, oversized upload | ✅ Tamamlandı (26 yeni test). |
| B6 | API responses Türkçe karakter normalizasyonu (RUF001/2/3, 1400+ ihlal — büyük çoğunluk false positive) | ⏳ İleride değerlendirilecek. |
| B7 | Pagination `skip` ve path int parametrelerinde int64 overflow koruması | ✅ Tamamlandı — `MAX_SQLITE_INT` + `Path/Query(..., le=...)` constraint'leri. |

### Tier C — Düşük öncelik

| # | Konu | Sebep |
|:--|:--|:--|
| C1 | mypy / pyright integration | ANN tier B'de değerlendirildikten sonra. |
| C2 | Hadolint (Dockerfile lint) | Dockerfile küçük, manuel review yeterli. |
| C3 | ~~OpenAPI shape contract test (Schemathesis vb)~~ | ✅ Karşılandı — `tests/test_schemathesis_fuzz.py` + CI `fuzz` job. |
| C4 | ~~Frontend a11y axe-core CI integration~~ | ✅ Karşılandı — `.github/workflows/a11y.yml`. |
| C5 | ES module split (`index.html` → `src/*.js` + `src/*.css`) | Vite scaffold hazır; ileride ad-hoc bölünecek. |
| C6 | Frontend `package-lock.json` commit'i | CI'da `npm install --no-save` ile çalışıyor; ileride lock dosyası commit'lenebilir. |

---

## 📦 Dış Bağımlılık Durumu

### Üretim (`requirements.txt`)
| Paket | Mevcut | Latest | Not |
|:--|:--:|:--:|:--|
| fastapi | >=0.110 | 0.115 | OK, geriye uyumlu |
| sqlalchemy | >=2.0 | 2.0 | OK |
| pydantic | 2.13.3 | 2.13.4 | minor patch — opsiyonel |
| **bcrypt** | **4.3.0** | 5.0.0 | ⚠️ **passlib 1.7.4 ile uyumlu olduğu için 4.x'te kilit** |
| python-jose[cryptography] | 3.3+ | 3.5 | OK |
| passlib[bcrypt] | 1.7.4 | 1.7.4 | son sürüm |
| paho-mqtt | 2.1+ | 2.1 | OK |
| onnxruntime | 1.18+ | latest | OK |
| pillow | 10.3+ | latest | ⚠️ getdata 14'te deprecate (Tier A6) |

### Geliştirme (`requirements-dev.txt`)
| Paket | Mevcut | Sebep |
|:--|:--:|:--|
| ruff | >=0.13 | Modern kural setleri için 0.13'e yükseltildi |
| bandit[toml] | >=1.7.5 | Python source security scanner |
| pip-audit | >=2.7 | Dependency CVE scanner |
| pre-commit | >=3.6 | Stabil |
| pytest + pytest-cov | >=8.0 + >=4.1 | Stabil |

---

## 🤖 CI/CD Ekosistemi

### Workflow inventarı
| Dosya | Tetikleyiciler | Job'lar |
|:--|:--|:--|
| `.github/workflows/ci.yml` | push (main, cycle_8, shiftFinal), PR (main), manuel | `lint` (Ruff) → `test` (pytest + coverage) → `migrations` (alembic upgrade) → `fuzz` (Schemathesis property-based) |
| `.github/workflows/security.yml` | push (main, cycle_8, shiftFinal), PR (main), Pazartesi 06:00 cron, manuel | `bandit` + `pip-audit` |
| `.github/workflows/a11y.yml` | push (main, cycle_8, shiftFinal), PR (main), Pazartesi 07:00 cron, manuel | `axe` — FastAPI bg + axe-core WCAG 2.0 + 2.1 A/AA tarama; JSON rapor 30 gün artifact |

### Pre-commit ekosistemi (`.pre-commit-config.yaml`)
1. **pre-commit-hooks v5.0** — trailing-whitespace, end-of-file-fixer, check-yaml, check-added-large-files, check-merge-conflict, **detect-private-key**
2. **ruff-pre-commit v0.13** — lint + format (auto-fix)
3. **bandit 1.8** — security scan (medium severity, sadece `app/`)

### Coverage akışı
- HTML rapor → CI artifact (`coverage-report`, 14 gün retention)
- XML rapor → CI artifact (`coverage-xml`, Codecov uyumlu, 14 gün)
- Yerel terminal raporu → `term-missing` ile satır bazlı eksikler

### Migration smoke test
Her CI koşusunda boş bir SQLite DB üzerinde `alembic upgrade head` çalıştırılır. Bu, autogenerate'lenmiş migration'ların gerçekten çalışabilir olduğunu garanti eder.

---

## 🎯 shiftFinal Sprint Durumu (13–19 Mayıs)

A2 (observability), A3 (frontend), A4 (reliability) ve QA/fuzz paketleri tamamlandı (sırasıyla `e6259ae`, `02d1359`, `2a889f8`, `7e49bef`). Sprint 19 Mayıs'a kadar açık; kalan günler PR review, doc cila ve fırsat çıktığında ek geliştirmeler için kullanılıyor.

| Paket | Tier | İçerik | Durum |
|:--|:--:|:--|:--:|
| Observability | A2 | Sentry init, Prometheus middleware + 4 metric, JSON log formatter, request_id middleware | ✅ `e6259ae` |
| Frontend | A3 | Vite scaffold, a11y landmarks/ARIA/skeleton loaders, 28 yeni a11y testi | ✅ `02d1359` |
| Reliability | A4 | DB pool tuning, `backup.sh`/`restore.sh`, Makefile target'ları, 7 yeni test | ✅ `2a889f8` |
| QA / Fuzz | A7 | Schemathesis property-based fuzz (25 GET endpoint), axe-core CI workflow, 6 int64 overflow bug fix | ✅ `7e49bef` |

### 📂 Açık alanlar (kalan kapasite)

Temel paketler tamamlandıktan sonra ele alınabilecek iyileştirmeler:

- **Schemathesis fuzz genişletme** — POST/PATCH/DELETE write operasyonlarına auth-aware fuzz (şu an sadece GET coverage'da)
- **axe-core CI sertleştirme** — ilk run sonrası kalan WCAG warning'leri temizlenip `continue-on-error: false`'a alınması
- **Frontend ES module split** — Vite scaffold hazır; `index.html` inline CSS/JS'in `src/styles/*.css` + `src/main.js`'e bölünmesi
- **OpenAPI shape contract test** — şu an Schemathesis fuzz'ı server-error odaklı; response shape conformance ayrı kontrol olarak eklenebilir
- **Tier B3/B4** — public API'lerde `ANN001/ANN201` type hints + `D101/D102` docstring kademeli geçiş
- **Tier C5/C6** — frontend `package-lock.json` commit + module split adımları

---

## 📈 Repo Büyüme Trendi

> **Not:** Aşağıdaki trend shiftFinal kapanışına (17 May 2026) kadarki büyümeyi
> gösterir. **fixroll v1-v7 sonrası güncel (30 May):** 650 test · %95 coverage ·
> 66 endpoint · 15 ORM tablo · 4 CI workflow (+ frontend-test job).

```
Başlangıç  →  Üretim Çekirdeği  →  Cila & QA (shiftFinal)
─────────────────────────────────────────────────────────────────
Test         246    →  350               →  425     (+179 / +73%)
Coverage     %86    →  %95.04            →  %95.04  (+9.0 pp, hedef ✅)
LOC (app/)  ~3,300  →  ~4,803            →  ~5,400  (+~64%)
Endpoint     41     →  43                →  43      (+2 pagination)
ORM tablo    14     →  15                →  15      (+1 aggregate)
Migration    0      →  2                 →  2       (initial + aggregate)
CI workflow  1      →  2                 →  3       (+ security, + a11y)
CI job       2      →  3 + 2 sec         →  4 + 2 sec + 1 a11y  (fuzz + axe job)
Pre-commit   2 hook →  3 hook            →  3 hook  (+ bandit)
Ruff kural   8      →  17                →  17      (DTZ/ERA/PT/RET/C4/PIE/PERF/TRY/S)
Frontend     2,200  →  2,972             →  ~3,100  (+ a11y/skeleton, Vite scaffold)
Fuzz test    0      →  0                 →  25      (Schemathesis GET endpoint coverage)
A11y test    0      →  0                 →  28      (skip-link, landmarks, scope, aria-busy)
```

---

## 📚 İlgili Dosyalar

- [`projeakisi.md`](../projeakisi.md) — Cycle bazlı görev dağılımı
- [`docs/setup/PROD_DEPLOY.md`](setup/PROD_DEPLOY.md) — nginx + Let's Encrypt deploy
- [`docs/architecture.md`](architecture.md) — sistem mimarisi
- [`pyproject.toml`](../pyproject.toml) — Ruff + pytest + coverage config
- [`.pre-commit-config.yaml`](../.pre-commit-config.yaml) — pre-commit hooks
- [`.github/workflows/`](../.github/workflows/) — CI + security pipelines
