# 🔄 Cycle 8 Retrospective — Üretim Hazırlığı (Core)

> **Cycle:** 8 (10–12 Mayıs 2026, fiilen 10 Mayıs'ta tek günde tamamlandı)
> **Yazan:** Miraç Duran (Scrum Master / Manager)
> **Durum:** ✅ Tamamlandı + bonus iş paketleri

---

## 1. 🎯 Cycle 8 Hedefi

Cycle 7'nin platformun tüm temel özelliklerini bitirmesinin ardından, ürünü **pilot/üretim seviyesine taşıyacak backend altyapı eksiklerini kapatmak**. Plan, Miraç'ın 5 maddelik üretim çekirdeği görevi etrafında inşa edildi; ekip cila katmanı (observability, a11y, edge tests, backup) yeniden organizasyonla `shiftFinal` bridge sprint'ine taşındı (bkz. [projeakisi.md](../projeakisi.md)).

## 2. ✅ Tamamlanan İşler

### 2.1 Miraç'ın Üretim Çekirdeği (5/5 ✅)

| # | Görev | Commit | Etki |
|:-:|:--|:--|:--|
| 1 | Rate limit binding (17 endpoint) | `05000a9` | 30/min STRICT + 10/min AUTH, brute-force koruması |
| 2 | N+1 query fix (`analytics.py`) | `db0b144` | 162 sorgu → 2 sorgu (81 farm × dashboard) |
| 3 | JWT auth backend (bcrypt + HS256) | `603c264` | sha256+dict skeleton'dan production-grade'e geçiş |
| 4 | Alembic 14-tablo initial migration | `d6c3e22` | `pass` placeholder'dan gerçek schema'ya — PostgreSQL geçişi mümkün |
| 5 | nginx reverse proxy + Let's Encrypt | `b139154` | TLS termination + HTTPS redirect + ACME challenge |

### 2.2 Bonus İş Paketleri (plan dışı)

| Paket | Commit | Etki |
|:--|:--|:--|
| Cycle date shift (11–20 → 10–12) | `41cd9c8` | Erken bitiş gerçeğini takvime yansıtma |
| Tier 1 lint cleanup (DTZ005, ERA001, D100) | `4c796eb` | 2 false-positive temizliği + module docstring |
| Tier 2A coverage gap kapatma | `cf35a63` | scheduler %50→%100, mqtt %54→%88, weather %74→%100 |
| Tier 2A.2 ML coverage push | `15c154e` | irrigation %73→%100, plant_disease %71→%93, model_perf %72→%99 |
| Cycle yeniden numaralandırma | `4ae8ce7` | shiftFinal bridge sprint deseni (shiftSession devamı) |
| Cycle 7 archiving slip kapatma | `fca5e7c` | Emirhan'ın 2. sub-task'ı (`sensor_reading_monthly_aggregates`) |
| Comprehensive quality audit + CI/CD | `d011017` | Ruff 8→17 kural, bandit/pip-audit workflow, QUALITY_AUDIT.md |
| Doküman aykırılık temizliği | (sonraki) | 16 stale referans hizalandı |
| Tier 1 cila paketi (A5+A6+B1) | (sonraki) | `_clean_tr` modernize, Pillow 14 prep, magic numbers, config tests |

## 3. 📈 Metrik Atılımları

```
                Cycle 8 başı       Cycle 8 sonu       Δ
─────────────────────────────────────────────────────────
Test sayısı     246                313                +67  (+27%)
Coverage        %86                %95                +9 pp
LOC (app/)      ~3,300             ~4,739             +43%
ORM tablo       14                 15                 +1 (aggregate)
Migration       0 (boş)            2 (gerçek)         +2
Endpoint        41                 41                 0 (decorator eklendi)
CI workflow     1                  2                  +1 (security)
Ruff kural      8                  17                 +9
Pre-commit hook 2                  3                  +1 (bandit)
Bandit issue    —                  0 (medium+)        —
```

## 4. 🚧 Karşılaşılan Zorluklar ve Çözümler

### 4.1 Bcrypt 5.0 ↔ Passlib 1.7.4 uyumsuzluğu
- **Problem:** Passlib `bcrypt.__about__.__version__` API'sini okur; bcrypt 5.0'da bu attribute kaldırıldı.
- **Belirti:** `AttributeError: module 'bcrypt' has no attribute '__about__'` + `ValueError: password cannot be longer than 72 bytes` (5.0'da sessiz truncate de kaldırıldı).
- **Çözüm:** `requirements.txt`'te `bcrypt>=4.0,<5.0` constraint'i; passlib upgrade beklenirken transitive paketten ödün verildi. Yorumla geleceğe not bırakıldı.

### 4.2 Alembic versions/ git tarafından track edilmiyordu
- **Problem:** `.gitignore`'da blanket `alembic/versions/*.py` kuralı vardı; ekip migration dosyalarının repo'ya gittiğini sanıyordu.
- **Belirti:** `git status` migration eklemesini "untracked" göstermedi; doğal "checked in" varsayımı yanlıştı.
- **Çözüm:** `.gitignore` rule'unu `alembic/versions/__pycache__/` ile sınırlandırdık; mevcut migration ve sonraki autogen'ler artık track ediliyor.

### 4.3 SlowAPI testleri toplu pytest koşumunda 429 üretiyordu
- **Problem:** `tests/conftest.py`'nin `client` fixture'ı slowapi `Limiter`'a dokunmuyordu; rate limit binding sonrası AUTH_RATE testleri başka testlerin kuyruğunda 429 yiyebildi.
- **Çözüm:** İki fixture: `client` (limiter disabled) ve `rate_limited_client` (limiter enabled + in-memory storage reset).

### 4.4 Paho-MQTT yüklü değilken `start()` testleri
- **Problem:** `paho-mqtt` opsiyonel bağımlılık; CI ortamında her zaman yüklü olmayabilir. Bare `sys.modules` mock'ı, alt-modül import'larında patladı.
- **Çözüm:** `fake_paho` fixture'ı tam üçlü hiyerarşi (`paho` + `paho.mqtt` + `paho.mqtt.client`) inşa ediyor; `MQTTListener.start()` başarılı path'i artık opsiyonel dep olmadan test edilebilir.

### 4.5 Cycle 7 archiving slip
- **Problem:** Emirhan'ın Cycle 7 görevinin 2. parçası (historical aggregation) bitmemişti ama README "✅ Tamamlandı" diyordu.
- **Çözüm:** Tek slip olarak tespit edildi → Cycle 8 günü kapanmadan Miraç tarafından kapatıldı (`SensorReadingMonthlyAggregate` + `archive_old_readings()` + haftalık cron + 11 yeni test).

### 4.6 Cycle naming çakışması (8.5 problemi)
- **Problem:** "Cycle 8.5" amatör görünüyordu; renumbering (Cycle 9 polish → Cycle 10 final) tüm referansları kırdı.
- **Çözüm:** `shiftSession` (Cycle 6) deseninden esinlenerek **adlı bridge sprint** modeli: `shiftFinal` numarasız sprint'tir; final rapor Cycle 9 numarasını korur.

## 5. 🧠 Öğrenmeler — Keep / Stop / Start

### ✅ Keep Doing
- **Audit-driven backlog** — `docs/QUALITY_AUDIT.md` tier'ları (A/B/C) net önceliklendirme sağladı; ekipte "ne yapalım sıradakini" tartışması azaldı.
- **Atomik commit'ler bilingual mesaj** — her commit tek değişiklik kümesi + EN/TR mesaj; reviewer ve akademik teslim için altın.
- **Pre-commit hook'lar erken hata yakaladı** — ruff + bandit lokal'de %95 sorunları yakaladı, CI'a sadece %5 sızdı.
- **Smoke test (`alembic upgrade head` CI'da)** — yeni model eklemelerinde "migration unutuldu mu" sorusu otomatik cevaplanıyor.

### ❌ Stop Doing
- **Manuel coverage hedef tahmini** — "%95'e ulaşır" demek yerine baştan failure threshold'u yüksek tutup CI'ı zorlamak doğru olurdu. shiftFinal'da `fail_under=95` denemeliyiz.
- **`.gitignore` blanket pattern'ler** — `alembic/versions/*.py` gibi şey her dosyayı kapsar; ihtiyaca göre spesifik (`__pycache__`) olmak daha güvenli.
- **README/dokümanı manuel güncelleme** — 16 stale referans birikmişti; metric'ler doc'a otomatik enjekte edilmeli (Makefile target veya pre-commit hook).

### 🚀 Start Doing
- **Audit/Retrospective her cycle'da** — bu doküman gibi; akademik teslim için zaten gerekli, bonus olarak ekip refleksini güçlendiriyor.
- **Bonus iş paketlerini ayrı commit'lemek** — "Tier 2A coverage" ve "Cycle 7 slip" gibi şeyleri ana görev commit'lerine karıştırmamak; reviewer'a temiz timeline.
- **Bridge sprint pattern (shiftSession/shiftFinal)** — cycle yapısını bozmadan ara işleri konteinerlemek için kalıcı pattern.
- **Plan dışı bulguları tier'lara çekmek** — ad-hoc "şuna da bakayım" yerine `QUALITY_AUDIT.md` Tier B/C'ye düşürüp shiftFinal'a aktarmak.

## 6. 📦 shiftFinal'a Devredilen Borç

Cycle 8 başı planlanan ancak Cycle 8'de yapılmayan (kasıtlı olarak `shiftFinal` bridge sprint'ine taşınan) işler:

| Sahibi | Görev | Status |
|:--|:--|:--:|
| Mehmet | Sentry + Prometheus + structured logging | ⏳ shiftFinal A2 |
| Ecenur | Vite bundling + a11y (ARIA, WCAG AA) + skeleton loaders | ⏳ shiftFinal A3 |
| Emirhan | Backup/restore script + DB pool tuning + (archiving ✅ yapıldı) | ⏳ shiftFinal A4 |
| Ayşe | Edge case test paketi (1MB, unicode, race) + auth integration | ⏳ shiftFinal B5 |
| Miraç | (Tier A5/A6/B1 ✅ erken kapatıldı) | — |

> **Not:** Coverage %95+ resmî tutuş hedefi (Ayşe A1) Cycle 8'deki bonus push ile **bugün** karşılandı; Ayşe shiftFinal'da edge case paketine odaklanabilir.

## 7. 🏆 Cycle 8 İçin Skor Kartı

| Boyut | Skor | Not |
|:--|:--:|:--|
| Planlı görevleri tamamlama | ✅ 5/5 | Tüm Miraç görevleri commit edildi |
| Zamanlama | 🌟 | 3 günlük plan tek günde bitti (10 May) |
| Bonus iş paketleri | 🌟 | 9 ek paket (audit, archiving, renumbering, ...) |
| Kalite metrikleri | ✅ | Coverage %86→%95, +67 test, Ruff genişletme |
| Güvenlik | ✅ | Bandit medium+ 0 issue, pip-audit CI'a entegre |
| Doküman tutarlılığı | ✅ | 16 stale referans tek commit'te hizalandı |
| Ekip iletişimi | 🟡 | Mehmet/Ecenur/Emirhan/Ayşe henüz bilgilendirilmedi (shiftFinal başlangıcında olacak) |

## 8. 🔮 Cycle 9 (Final Rapor) Etkisi

Cycle 8'in fazlasıyla tamamlanmış olması Cycle 9'a şu avantajları sağlıyor:
1. **Akademik raporda anlatılacak somut başarı:** 12 commit, +67 test, %9 coverage atılımı, 0 bandit issue.
2. **Repo "presentable" durumda:** sunum sırasında demo edilebilecek production-grade altyapı (HTTPS, JWT, rate limit, migration).
3. **shiftFinal'a kapasite alanı:** ekibin diğer üyeleri bu cila sprint'inde rahat çalışabilir; backend altyapı borç bırakmıyor.
4. **`QUALITY_AUDIT.md` raporu Cycle 9 final dokümanına doğrudan bölüm olarak girebilir.**

---

**Yazan:** Miraç Duran
**Tarih:** 11 Mayıs 2026
**İlgili dosyalar:** [`projeakisi.md`](../projeakisi.md), [`QUALITY_AUDIT.md`](QUALITY_AUDIT.md), [`README.md`](../README.md)
