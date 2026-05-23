# 👥 Ekip & Katkı Matrisi

## Proje Ekibi

| Üye | Rol | Görev Alanları |
|:----|:----|:---------------|
| **Miraç Duran** | Scrum Master / Manager | Proje yönetimi, CI/CD, REBUILD pivot (çiftçi-odaklı saha aracı + 4-rol RBAC), analitik dashboard, integration testler |
| **Ayşe Eslem Çekici** | Geliştirici | UI/UX wireframe, gübreleme servisi, hava durumu pipeline, ML model değerlendirme |
| **Ecenur Üner** | Geliştirici | Dashboard SPA, veri görselleştirme, responsive tasarım, veri hattı izleme |
| **Emirhan Günay** | Geliştirici | Veritabanı tasarımı, sensör entegrasyonu, Alembic migration, seed data |
| **Mehmet Sait Tayşı** | Geliştirici | API geliştirme, güvenlik, rate limiting, dokümantasyon, model izleme |

---

## Cycle Bazlı Katkılar

### Cycle 1 — Proje Temelleri (24 Şub – 10 Mar)
- **Miraç**: Repo kurulumu, branch koruma, proje akış dokümanı, teknoloji araştırması
- **Emirhan**: Proje analizi ve kapsam tanımlama
- **Ayşe Eslem**: Gereksinim toplama ve belgeleme
- **Ecenur**: Geliştirme ortamı kurulumu
- **Mehmet Sait**: Veri seti incelemesi ve ön işleme

### Cycle 2 — Veri Planlama (11 – 24 Mar)
- **Miraç**: Veri yapısı ve saklama yöntemleri planı
- **Ecenur**: Veri kaynakları belirleme ve toplama planı
- **Mehmet Sait**: Veri seti analizi ve model seçimi

### Cycle 3 — Tasarım ve Mimari (25 Mar – 1 Nis)
- **Miraç**: API tasarımı ve dokümantasyon
- **Emirhan**: Veritabanı şeması oluşturma
- **Ayşe Eslem**: UI/UX wireframe tasarımı

### Cycle 4 — Geliştirme ve Entegrasyon (2 – 13 Nis)
- **Miraç**: Sulama optimizasyon ML modeli (RandomForest)
- **Emirhan**: Toprak sensörü veri entegrasyonu
- **Ayşe Eslem**: Hava durumu verisi temizleme ve dönüştürme pipeline
- **Ecenur**: Dashboard veri görselleştirme (Chart.js)
- **Mehmet Sait**: Temel veri erişim API (FastAPI + Swagger)

### Cycle 5 — Test ve İyileştirme (14 – 27 Nis)
- **Miraç**: CI/CD pipeline (GitHub Actions), test altyapısı, proje raporu
- **Emirhan**: Alembic migration sistemi, seed data, DB performans optimizasyonu
- **Ayşe Eslem**: Gübreleme öneri servisi (NPK), weather pipeline genişletme
- **Ecenur**: Dashboard modernizasyonu (dark mode, responsive, 6 sayfa SPA)
- **Mehmet Sait**: API güvenlik (rate limiting, auth, exception handling)

### Cycle 6 — Son Sprint (28 Nis – 3 May)
**Planlanan görevler** (`projeakisi.md`):
- **Miraç**: Analitik pano, 81 il genişletme, mega seed data, rapor export, repo profesyonelleştirme
- **Emirhan**: Veri temizleme iyileştirmeleri
- **Ayşe Eslem**: ML model değerlendirme ve optimizasyon
- **Ecenur**: Veri hattı izleme ve uyarı sistemi
- **Mehmet Sait**: Model performans izleme ve raporlama altyapısı

> **Not:** Cycle 6 deadline'ı (3 May) sonrasında bazı görevler `shiftSession`
> branch'inde tamamlandı/devam ediyor. Detaylı durum için `git log`
> üzerinden ekip commit'lerine bakınız.

### shiftSession — Borç Kapatma (3 May+)
- **Miraç**: Production stability fix'leri (scheduler, hardcoded secrets,
  env-driven CORS), ekip için skeleton router/helper'lar (alerts, metrics,
  model_performance, ML eval, data_quality), 52 yeni test
- **Miraç (Mehmet'ten devralarak)**: 🤖 **Model Performans İzleme &
  Raporlama Altyapısı** (Cycle 6 görevi) — `PATCH /{id}` (gerçek değer
  doldurma), `/timeseries/{model}` (günlük accuracy zaman serisi),
  `/compare` (multi-model karşılaştırma), `/drift/{model}` (otomatik
  SystemAlert ile drift tespiti), `irrigation/predict`'e otomatik log
  entegrasyonu, `/api/health/deep` zenginleştirme (DB latency, scheduler
  job listesi, data freshness, alert sayaçları), 10+ yeni test
- **Miraç**: Seed verisi gerçekçilik revizyonu (diurnal pattern, alert
  temizliği). Filiz maskotu + UX cilası lokal olarak hazır, Cycle 7
  içinde ayrı PR ile main'e alınacak.
- **Ecenur**: Veri hattı izleme modülü (script + dokümantasyon)
- *Diğer üyeler kendi Cycle 6 görevlerini devam ettirmekte*

### REBUILD Pivot — Çiftçi-Odaklı Geri Dönüş (Mayıs 2026)

**Pivot kararı:** Eski "ulusal/bakanlık paneli" çerçevesi bırakıldı; sistem
artık çiftçi-odaklı saha aracı + admin/gözetmen için sistem-geneli read-only
gözlem modu olarak konumlandırıldı. Detaylar: `REBUILD_ROADMAP.md`.

- **Miraç**: Pivot kararı + 7 faz uygulama.
  - **Faz 1-2**: Pivot doc + repo temizlik (81-il/ulusal iddialar
    forward-facing dosyalardan kaldırıldı; cycle geçmişi korundu).
  - **Faz 3**: Auth backend (JWT bearer + bcrypt + 4-rol model) +
    frontend Bearer helper + ön panel auth gate + hesabım/şifre UI.
  - **Faz 3.5**: Admin user-mgmt endpoint'leri (`/api/auth/users` CRUD,
    şifre sıfırlama) + frontend Kullanıcılar sayfası + tarla detay
    sayfası + leaf-upload akışı.
  - **Faz 4**: Çiftlik/tarla CRUD (`farms.py`/`fields.py` write) +
    RBAC ownership middleware + sulama onay/status akışı.
  - **Faz 5**: `POST /api/alerts/check` (tarama + dedup) + header
    bildirim çanı UI.
  - **Faz 6**: `POST /api/onboarding/demo` (per-user örnek veri) +
    boş hesap onboarding banner.
  - **Faz 7**: CHANGELOG/projeakisi REBUILD kayıtları, demo script,
    README sayı/rozet, FINAL_REPORT REBUILD bölümleri.
  - **fixroll_v1/v2**: Polish round'ları — farmer Raporlar gizleme,
    sensör add/del UI (#7), hero subtitle dynamic (#8a), Filiz
    rol-aware tip havuzları + isim kişiselleştirmesi (#8b), harita
    auto-zoom (#10), architecture.md REBUILD güncelleme (#23),
    CONTRIBUTORS REBUILD bölümü (#24).
- **Diğer üyeler**: REBUILD sprintinde aktif değil — önceki cycle'larda
  tamamlanan modülleri yukarıdaki bölümlerde listelendiği gibi.

---

## 📊 Proje Metrikleri (Cycle 6 sonu)

| Metrik | Değer |
|:---|:---:|
| Toplam Python LOC | **~9 500** (`app/` 4 803 + `tests/` ~4 200 + `database/` 533) |
| Frontend LOC | 2 972 satır (`frontend/index.html`, 9 sayfa, slider pagination) |
| Endpoint sayısı | **43** (11 router; pagination count endpoint'leri dahil) |
| ORM tablo sayısı | **15** (Cycle 8 #4 + archiving = 14 + sensor_reading_monthly_aggregates) |
| Pydantic schema sayısı | 25+ |
| Toplam test | **350** (Cycle 4'te 41 → +309, 25 dosya) |
| Test coverage | **%95.04** (eşik %80, shiftFinal %95+ hedefi geçildi) |
| Cycle 6 commit sayısı | 33 (Cycle 5 sonrasından) |
| Bitki türü | 17 (Türkiye'nin 7 coğrafi bölgesi için) |
| Çiftlik kapsamı | 81 il × 2 tarla = 162 tarla |
| Sensör seed | 324 sensör, ~4 860 okuma (diurnal pattern) |
| Hava durumu seed | 1 215 kayıt (sıcaklık/nem diurnal cycle) |
| ML modeli | RandomForest (sklearn 1.8.0, sentetik 1000 örnek) |
| Docker support | ✅ multi-stage Dockerfile + docker-compose |
| CI/CD | GitHub Actions: 2 workflow — `ci.yml` (lint + test + alembic migration smoke + XML coverage) ve `security.yml` (bandit + pip-audit + haftalık cron) |
| Pre-commit hooks | ruff v0.13 (lint + format), bandit 1.8, trim whitespace, EOF, check-yaml, check-large-files, check-merge-conflict, detect-private-key |
