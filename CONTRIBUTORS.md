# 👥 Ekip & Katkı Matrisi

## Proje Ekibi

| Üye | Rol | Görev Alanları |
|:----|:----|:---------------|
| **Miraç Duran** | Scrum Master / Manager | Proje yönetimi, CI/CD, analitik dashboard, ulusal ölçek genişletme, integration testler |
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

### Cycle 5 — Test ve İyileştirme (11 – 28 Nis)
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
  temizliği), Filiz maskotu + UX cilası (Cycle 7'ye atandı, kod hazır)
- **Ecenur**: Veri hattı izleme modülü (script + dokümantasyon)
- *Diğer üyeler kendi Cycle 6 görevlerini devam ettirmekte*

---

## 📊 Proje Metrikleri (Cycle 6 sonu)

| Metrik | Değer |
|:---|:---:|
| Toplam Python LOC | **6 538** (`app/`, `database/`, `tests/`) |
| Frontend LOC | 2 323 satır (`frontend/index.html`) |
| Endpoint sayısı | **36** (10 router) |
| ORM tablo sayısı | **14** |
| Pydantic schema sayısı | 30+ |
| Toplam test | **198** (Cycle 4'te 41 → +157) |
| Test coverage | %91+ |
| Cycle 6 commit sayısı | 33 (Cycle 5 sonrasından) |
| Bitki türü | 17 (Türkiye'nin 7 coğrafi bölgesi için) |
| Çiftlik kapsamı | 81 il × 2 tarla = 162 tarla |
| Sensör seed | 324 sensör, ~4 860 okuma (diurnal pattern) |
| Hava durumu seed | 1 215 kayıt (sıcaklık/nem diurnal cycle) |
| ML modeli | RandomForest (sklearn 1.8.0, sentetik 1000 örnek) |
| Docker support | ✅ multi-stage Dockerfile + docker-compose |
| CI/CD | GitHub Actions: ruff + pytest |
| Pre-commit hooks | ruff, ruff-format, trim whitespace, EOF, large files |
