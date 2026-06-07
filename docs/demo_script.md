# 🎬 SFDAP — Sunum Demo Senaryosu (REBUILD)

**Hedef süre:** 10-12 dakika
**Teknik gereksinimler:** Python 3.12, dashboard tarayıcıda açık, terminal API canlı

> Bu senaryo REBUILD sonrası **çiftçi-odaklı** akışı izler: ön panel (giriş) →
> "Çiftliğim" → tarla detay → sulama onayı → hastalık tanısı → bildirim →
> (admin) sistem gözetimi. Demo persona **Çiftçi Ahmet**'in 5 sorusunu cevaplar.

---

## ⚙️ Hazırlık (sunumdan önce, 2 dk)

```bash
cd Smart_Farming_Data_Analysis_Platform
# Taze çiftçi-odaklı demo seed (6 kullanıcı, 3 çiftlik, 6 tarla)
rm -f sfdap_dev.db && python database/seed_data.py
make run                 # uvicorn → http://localhost:8000
```

Tarayıcıda aç: **http://localhost:8000/dashboard/** (+ opsiyonel `/docs` Swagger).

**Demo hesapları:**

| Rol | E-posta | Şifre |
|:--|:--|:--|
| 🧑‍🌾 Çiftçi *(ana persona)* | `ahmet@demo.test` | `123456` |
| 🧑‍🌾 Çiftçi | `ayse@demo.test` | `123456` |
| 🧑‍🌾 Çiftçi | `mehmet@demo.test` | `123456` |
| 🛠️ Geliştirici | `developer@demo.test` | `123456` |
| 🏛️ Gözetmen | `overseer@demo.test` | `123456` |
| 🛡️ Admin | `admin@demo.test` | `123456` |

> Tüm demo hesaplarının şifresi `123456` (seed_data.py `DEMO_PASSWORD`).

---

## 🎯 Demo Akışı

### Adım 1 — Ön panel & giriş (1 dk)

> *"SFDAP — çiftçinin kendi tarlalarındaki sensör, hava ve ML tahminlerini tek
> panelde birleştiren bir karar destek aracı. Giriş yapmadan içerik görünmez."*

**Göster:** `/dashboard/` açılır → full-screen **ön panel** (giriş ekranı) karşılar.
- "Hesabın yok mu? Kayıt ol" linki → kayıt formu (gizli, isteğe bağlı)
- `ahmet@demo.test` / `123456` ile **giriş yap**

> *"Giriş yapınca header'da yeşil 'çiftçi' rozeti + sahip olduğu çiftlik sayısı."*

---

### Adım 2 — "Çiftliğim" dashboard (1.5 dk)

> *"Ahmet'in ilk sorusu: tarlam susuz mu? Dashboard 4 kartla anında cevap veriyor."*

**Göster:** Genel Bakış sayfası — rol-aware özet:
- 💧 **Bugün toprak nemi** — Tarla A **🥵 Susuz** (kritik)
- 🚿 Son sulama · 🚨 Açık uyarı (severity kırılımı) · 🦠 Son hastalık tanısı
- Hero: çiftlik / sensör / okuma sayıları (giriş yapan çiftçiye göre)

> *(Yeni/boş hesap demosu:)* *"Yeni kullanıcı boş hesapla girince onboarding banner
> karşılar — tek tıkla 'Demo verisi yükle' ile örnek çiftlik kurulur."*

---

### Adım 3 — Tarla detayı (2 dk)

**Tıkla:** Sidebar → **Tarlalarım** → "Ahmet'in Çiftliği" → **Tarla A**

- Hero: bitki (Buğday) · alan · toprak tipi · ✏️ Düzenle / 🗑 Sil
- Toprak nemi kartı (Susuz) + **nem trend grafiği** (Chart.js, son okumalar)
- Sensörler (son okumalarıyla) · sulama geçmişi · hastalık geçmişi · toprak analizi · açık uyarı

> *"Tek tarlanın tüm bağlamı tek ekranda — RBAC sayesinde Ahmet yalnız kendi
> tarlasını görür."*

---

### Adım 4 — ML sulama önerisi → onayla (1.5 dk)

**Tıkla:** Sidebar → **Sulama** → form doldur (toprak nemi 22, sıcaklık 25, vb.) → **Tahmin**

> *"RandomForest modeli kaç litre su gerektiğini söylüyor. Ama asıl yeni şey:
> öneriyi tek tıkla programa ekleyebiliyoruz."*

- Sonuç kartında **"✅ Onayla ve programa ekle"** → tarla seç → sulama programı (pending) oluşur
- Tarla detayında sulama satırında **✓ Tamamlandı / ✗ İptal** ile durum takibi

---

### Adım 5 — Yaprak fotoğrafından hastalık tanısı (1.5 dk)

> *"Ahmet'in ikinci sorusu: bu yaprakta hastalık var mı?"*

**Tarla detayında** → "🦠 Hastalık Tespiti" → yaprak fotoğrafı yükle → **Tespit Et**

- CNN/heuristic model anında teşhis + güven skoru + şiddet döndürür
- Sonuç hastalık geçmişine düşer (detay otomatik yenilenir)

---

### Adım 6 — Bildirim akışı (1 dk)

> *"Beşinci soru: bir sorun çıkarsa haberim olur mu? Header'daki çan bunu çözüyor."*

**Tıkla:** Header → **🔔 bildirim çanı**
- Açık uyarı sayısı + dropdown (mesaj/severity/hızlı Çöz)
- **"🔄 Kontrol et"** → tarlaları tarar, düşük nem / hastalık hatırlatması üretir (dedup'lı)

---

### Adım 7 — Gübreleme önerisi (1 dk)

**Tıkla:** Sidebar → **Gübreleme** → Domates, 1 ha, N=80/P=40/K=50 → **Çalıştır**

> *"17 bitki türü için NPK önerisi — hem nicel (kg) hem Türkçe açıklama."*

---

### Adım 8 — Admin/gözetmen: sistem gözetimi (1.5 dk)

**Çıkış yap → `admin@demo.test` ile giriş** (header rozeti kırmızı 'yönetici').

> *"Aynı platform, farklı rol. Admin sistem-geneli görür + kullanıcıları yönetir."*

- Sidebar'da **👥 Kullanıcılar** (yalnız admin görür) → liste + rol değiştir / şifre sıfırla / sil / yeni kullanıcı
- **Harita** → sistemdeki çiftliklerin coğrafi dağılımı (bölge renkli)
- **Analitik** → sistem-geneli bölge kırılımları (admin/gözetmen sistem özeti)
- Dashboard `scope=system` — tüm çiftliklerin toplamı

> *"Çiftçi kendi verisini, gözetmen tüm sistemi read-only, admin tam yetki —
> 4-rol RBAC her endpoint'te uygulanıyor."*

---

### Adım 9 — Test & kalite + kapanış (1 dk)

**Terminal:**
```bash
make test            # 586 backend test
cd frontend && npm test   # 74 frontend (Vitest)
```

> *"586 backend + 74 frontend test, ruff lint+format temiz, bandit medium+ 0 issue.
> 4 GitHub Actions workflow (lint+test+migrations+fuzz / security / a11y).
> Pre-commit hook'larıyla her commit denetimden geçiyor."*

**Göster:** README "Sprint Durumu" + `CHANGELOG.md` [Unreleased] REBUILD bölümü.

> *"Sorularınız?"*

---

## 🎬 Demo İpuçları

- **Hız:** her ekran 30-60 sn — yavaş tıkla, açıklamayı tamamla
- **Giriş gate:** demo başında çıkış yapıp ön paneli göstermek etkili
- **Görüntü:** %100 zoom; dark mode görsel olarak daha çarpıcı
- **Yedek:** Wi-Fi giderse OpenWeatherMap çağrıları başarısız olur ama seed verisi yeter

## 🚨 Olası sorular & cevaplar

| Soru | Cevap |
|:--|:--|
| Gerçek çiftçiler nasıl kullanır? | "Sensör donanım kiti + mobil app ile pilot. JWT auth + 4-rol RBAC kuruldu; çiftçi kendi verisini görür." |
| 81 il / ulusal ölçek nerede? | "O çerçeveden vazgeçtik — proje artık çiftçi-odaklı bir saha aracı; admin/gözetmen sistem-geneli gözetim sağlar." |
| Hangi veriyi kullandınız? | "ML eğitim seti sentetik (RandomForest). Demo seed çiftçi-odaklı; IoT/MQTT ile gerçek akışa hazır." |
| Veri gizliliği / izolasyon? | "JWT + bcrypt + 4-rol RBAC: her endpoint farmer'ı kendi `user_id`'sine bağlı veriyle sınırlar; admin self-demote/self-delete'e karşı korumalı." |
| Bildirimler gerçek zamanlı mı? | "On-demand 'Kontrol et' tarama dedup'lı uyarı üretir; periyodik scheduler'a genişletilebilir." |
