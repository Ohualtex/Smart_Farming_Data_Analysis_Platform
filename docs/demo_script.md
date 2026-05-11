# 🎬 SFDAP — Sunum Demo Senaryosu

**Hedef süre:** 12-15 dakika
**Teknik gereksinimler:** Python 3.12, dashboard tarayıcıda açık, terminal ile API canlı

> **Not:** Filiz maskotu (Adım 1 hero ve Adım 6) Cycle 7 sonunda dashboard'a entegre olacaktır. Bu PR (`shiftSession` → `main`) Cycle 7 öncesi snapshot'ı taşır; Filiz adımları ayrı bir PR'da etkinleşir.

---

## ⚙️ Hazırlık (sunumdan önce, 2 dk)

```bash
# 1. Projeyi başlat
cd Smart_Farming_Data_Analysis_Platform
make run                 # ya da: .venv/bin/uvicorn app.main:app --port 8000

# 2. Tarayıcıda iki sekme aç
#    - http://localhost:8000/dashboard/
#    - http://localhost:8000/docs    (Swagger)

# 3. Terminal hazır tut (curl demo'su için)
```

**DB hazırlığı (eğer ilk demo değilse):**
```bash
rm sfdap_dev.db
python database/seed_data.py    # 7500+ kayıtlık seed yüklenir, ~5 sn
```

---

## 🎯 Demo Akışı

### Adım 1 — Açılış & Bağlam (1 dk)

> *"Merhaba. Bu, **SFDAP — Akıllı Tarım Veri Analizi Platformu**. Türkiye'nin
> tüm 81 ilinde toprak sensörleri, hava durumu ve makine öğrenimi
> tahminlerini tek panelde birleştiren bir akademik proje. 5 kişilik bir
> ekiple Scrum metodolojisiyle 6 ay içinde geliştirdik."*

**Göster:** Dashboard ana sayfa
- Hero banner: "81 il · 324 sensör · 4860 okuma · 17 bitki türü"
- Üst kartlar: günlük genel durum
- *(Cycle 7'de: Filiz maskotu sağ alt köşede karşılayacak)*

---

### Adım 2 — Mimari Özet (1 dk)

> *"Backend FastAPI + SQLAlchemy. ML için scikit-learn. Dashboard tek-sayfa
> SPA, Chart.js ile zengin görselleştirmeler. Hepsi Docker ile
> kontenerize edilebilir, GitHub Actions ile CI/CD pipeline'ı çalışıyor."*

**Göster:** README mimari diyagramı (mermaid) ve `docs/architecture.md`

---

### Adım 3 — Bölge Bazlı Analitik (2 dk)

> *"Türkiye'nin 7 coğrafi bölgesi farklı iklim koşulları sunar. Bunu veri
> üzerinde görelim."*

**Tıkla:** Sidebar → **Analitik**

- Sensör tipi dağılımı (donut chart)
- **Çiftlik bazlı sıcaklık karşılaştırması** — bölgelere göre kırılım
- NPK radar chart — bitki bazlı azot/fosfor/potasyum ihtiyacı
- Günlük sıcaklık trendi (gece-gündüz pattern, diurnal)

> *"Burada gerçekçi bir günlük döngü görüyoruz: gece 14°C, öğle 23°C —
> sezonsal pattern simülasyonu."*

---

### Adım 4 — ML Sulama Tahmini (2 dk)

> *"Şimdi gerçek bir senaryo: bir çiftçi tarlasına ne kadar su vermesi
> gerektiğini bilmek istiyor. RandomForest modeli toprak nemi, hava
> nemi, sıcaklık ve son yağış miktarına bakarak öneriyor."*

**Tıkla:** Sidebar → **Sulama**

Form değerlerini gir:
- Toprak nemi: **30%**
- Toprak sıcaklığı: 22°C
- Hava nemi: 60%
- Hava sıcaklığı: 25°C
- Yağış: 2 mm

**Sonuç:** "Orta düzeyde sulama gerekli: 28 litre."

> *"Modelimiz scikit-learn 1.8 ile sentetik 1000 örneklik veri üzerinde
> eğitildi. Her tahmin otomatik olarak `ModelPerformanceLog` tablosuna
> kaydediliyor — gerçek değerler sonradan PATCH ile doldurulup model
> doğruluğu zamanla takip ediliyor."*

---

### Adım 5 — Akıllı Gübreleme Önerisi (1 dk)

> *"17 farklı bitki türü için NPK önerisi sunuyoruz. Türkiye'de yaygın
> tüm büyük ürünler — buğday, mısır, domates, çay, fındık, üzüm, antep
> fıstığı."*

**Tıkla:** Sidebar → **Gübreleme**

- **Bitki:** Domates seç
- **Alan:** 1 hektar
- **Toprak:** N=80, P=40, K=50, pH=6.5
- **Çalıştır**

**Sonuç:** "Domates için toplam 560 kg gübre öneriliyor."

> *"Sonuç hem nicel (kg) hem de Türkçe açıklamayla geliyor. Bu çiftçiye
> doğrudan eyleme geçirilebilir bir bilgi."*

---

### Adım 6 — UX Cilası (1.5 dk) *(Cycle 7'de Filiz Asistan eklenecek)*

> *"Dashboard light/dark tema, mobil-responsive, Türkçe arayüz.
> Çiftçinin kullanacağı bir araç olduğu için UI dilimiz teknik değil
> tamamen yerel."*

**Tema toggle (sağ üst):** Dark → Light geçiş

> *"Cycle 7'de **Filiz** adlı SVG-tabanlı maskot karakter eklenecek:
> 65+ tarımsal ipucu, gündüz/gece mood otomasyonu, göz takibi, tıklama
> tepkileri. Geliştirme bitti, ayrı PR ile main'e alınacak."*

---

### Adım 7 — Swagger API Rehberi (1.5 dk)

**Tarayıcıda:** http://localhost:8000/docs

> *"Geliştirici tarafı: 41 endpoint, hepsi Swagger'da Türkçe açıklamalı.
> Sağ üstten Authorize → API key ver, herhangi bir endpoint'i canlı
> test et."*

- **Authorize butonuna tıkla:** `dev-api-key`
- `POST /api/fertilizer/recommend` → "Try it out" → Execute → 200 ✅

> *"Ekip arkadaşlarımız bu Swagger üzerinden hem geliştirme hem test
> yapıyor. Her endpoint için `examples=` ile canlı body geliyor."*

---

### Adım 8 — Sistem Sağlığı & Operasyon (1 dk)

**Curl ile:**
```bash
curl http://localhost:8000/api/health/deep | jq
```

> *"Production-ready bir sistem için derin sağlık kontrolü: DB latency,
> scheduler durumu, ML model varlığı, aktif sensör sayısı, alert
> sayaçları. Kubernetes liveness/readiness probe'larıyla uyumlu."*

**Curl ile:**
```bash
curl http://localhost:8000/api/model-performance/drift/irrigation_rf
```

> *"Model drift tespiti: bir modelin son haftadaki accuracy'si baseline'a
> göre %10'dan fazla düşerse otomatik `SystemAlert` oluşur."*

---

### Adım 9 — Test & Kalite (1 dk)

**Terminal:**
```bash
make test
```

> *"301 test, %94 coverage, 23 test dosyası, GitHub Actions ile her PR'da
> otomatik (lint + test + alembic migration smoke + güvenlik tarayıcıları).
> Pre-commit hook'larıyla ruff lint + format + bandit zorunlu."*

```bash
.venv/bin/ruff check app/
# → All checks passed!
```

---

### Adım 10 — Yol Haritası ve Kapanış (1 dk)

> *"Cycle 7'de CNN bitki sağlığı modeli, Auth UI ve IoT/MQTT entegrasyonu
> tamamlandı. Cycle 8'de üretim çekirdeği geldi (JWT auth, Alembic migration,
> rate limit, N+1 fix, nginx+Let's Encrypt). `shiftFinal` bridge sprint'inde
> cila ve gözlemlenebilirlik (Sentry, Prometheus, frontend a11y, backup).
> Cycle 9 final rapor + akademik teslim."*

**README "Yol Haritası" tablosunu göster.**

> *"Sorularınız?"*

---

## 🎬 Demo İpuçları

- **Hız:** her ekran 30-60 sn — yavaş tıkla, açıklamayı tamamla
- **Hata olursa:** API kapalıysa Filiz "uykulu" olabilir; F5 ile yenile
- **Görüntü kalitesi:** tarayıcıyı 100% zoom, dark mode görsel olarak daha çarpıcı
- **Yedek:** Wi-Fi giderse OpenWeatherMap çağrıları başarısız olur ama seed verisi yeter

## 🚨 Olası sorular & cevaplar

| Soru | Cevap |
|:--|:--|
| Gerçek çiftçiler nasıl kullanır? | "Pilot için sensör donanım kiti + mobil app gerek. Cycle 8'de auth UI + JWT backend tamamlandığı için 1-2 pilot çiftliğe deploy edilebilir." |
| Hangi veriyi kullandınız? | "Eğitim setimiz 1000 sentetik örnek (RandomForest). Cycle 7'de gerçek IoT verisi entegre olacak." |
| Filiz neden var? | "Çiftçilerin teknolojiyle bağ kurması için sevimli bir asistan. Tarımsal ipuçları + sistem durumu görselleştirme." |
| Maliyet modeli? | "Akademik proje. Üretim için kooperatif/Bakanlık destekli SaaS modeli düşünülebilir." |
| Veri gizliliği? | "Cycle 8'de RBAC + JWT ile kullanıcı bazlı izolasyon. Şu an local dev." |
