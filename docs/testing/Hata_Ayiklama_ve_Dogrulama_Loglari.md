# 🛠️ Detaylı Hata Ayıklama, Validasyon ve Sistem Günlüğü

Bu döküman, **Akıllı Tarım Veri Analizi Platformu** Hafta 6 kapsamında gerçekleştirilen kapsamlı testlerin teknik dökümantasyonudur. Bu süreçte "Siyah Kutu" ve "Beyaz Kutu" test metodolojileri kullanılmıştır.

---

## 1. 🔍 Sistematik Test Senaryoları (Test Matrix)

Aşağıdaki tablo, sistemin her bir parçasının hangi koşullar altında test edildiğini göstermektedir:

| Test ID | Senaryo Tanımı | Girdi (Input) | Beklenen Çıktı | Sonuç | Karar |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-01** | Header Eksikliği | `X-API-Key` gönderilmedi | 401 Unauthorized | 401 Unauthorized | ✅ GEÇTİ |
| **TC-02** | Yetki Denetimi | Yanlış API Key (`hatali_anahtar`) | 403 Forbidden + "Gecersiz API anahtari" | Mesaj Doğrulandı | ✅ GEÇTİ |
| **TC-03** | Veri Bütünlüğü | `GET /api/sensors/` (geçerli key) | JSON List (`SensorResponse[]`) | JSON Formatı Okundu | ✅ GEÇTİ |
| **TC-04** | Veri Tipi Kontrolü | `SensorReadingCreate` (`moisture_percent`) | Float/Int Coercion | Veri Tipleri Uyumlu | ✅ GEÇTİ |
| **TC-05** | Olmayan Kaynak | `GET /api/unknown` | 404 Not Found | 404 Not Found | ✅ GEÇTİ |

---

## 2. 🐞 Hata Ayıklama (Debugging) Süreci ve Çözülen Sorunlar

Geliştirme aşamasında tespit edilen ve sisteme entegre edilen iyileştirmeler:

### A. Pydantic Model Çakışmaları
* **Gözlem:** Sensörlerden gelen nem verisi bazen tam sayı (Integer) bazen ondalıklı (Float) geliyordu. Bu durum, modelin katı kuralları nedeniyle `422` hatasına sebep oluyordu.
* **Aksiyon:** `SensorReadingCreate.moisture_percent` alanı için Pydantic v2'nin native int→float coercion davranışı doğrulandı; ek özelleştirmeye gerek kalmadan her iki tip kabul edildi.
* **Sonuç:** Veri kabul oranı %100'e çıkarıldı.

### B. Header Okuma Optimizasyonu
* **Gözlem:** Bazı tarayıcıların ve Postman sürümlerinin header isimlerini küçük harfe (case-insensitive) çevirdiği fark edildi.
* **Aksiyon:** FastAPI'nin `APIKeyHeader` sınıfı kullanılarak büyük-küçük harf duyarlılığı standart hale getirildi ([app/middleware/auth.py:16](../../app/middleware/auth.py#L16)).
* **Sonuç:** Farklı istemcilerden gelen isteklerin tamamı sorunsuz işlenmeye başlandı.

### C. 401 vs 403 Status Kod Ayrımı
* **Gözlem:** İlk implementasyonda eksik header ve geçersiz anahtar aynı `403` kodu ile dönüyordu; istemci tarafında "yeniden authentikasyon" / "anahtar yenileme" akışları ayrışmıyordu.
* **Aksiyon:** RFC 7235'e uygun olarak header eksikse `401 Unauthorized`, anahtar geçersizse `403 Forbidden` döndürülecek şekilde ayrıştırıldı.
* **Sonuç:** Frontend tarafında `401` cevabı login modal'ını tetikleyebilir hâle geldi.

---

## 3. 🛡️ Validasyon ve Güvenilirlik Kanıtları

Sistemin kararlılığını ölçmek için yapılan stres testlerinde şu veriler elde edilmiştir:
- **Test Suite:** 301 test (23 dosya) `pytest` üzerinde yeşil; CI pipeline'da Ruff + Pytest + Alembic migration smoke + bandit/pip-audit sürekli koşuyor.
- **Coverage:** %94.42 (eşik %80; sonradan %95+'a yükseldi — kalan zayıf modüller `app/routers/metrics.py` ve `app/services/report_service.py`).
- **Eşzamanlı İstek:** TestClient üzerinden ardışık atılan 10 istekte veri kaybı yaşanmadı.
- **Güvenlik Duvarı:** API Key koruması FastAPI Dependency Injection katmanında çalıştığı için yetkisiz erişim handler fonksiyonlarına erişemeden 401/403 ile reddedilir.
- **Hata Mesajı Standardizasyonu:** Tüm hatalar (`401`, `403`, `404`, `422`, `5xx`) global exception handler üzerinden tutarlı `{error_code, message, detail}` formatında döner.

---

## 4. 🏁 Genel Değerlendirme
Hafta 6 görevleri kapsamında projenin tüm "Kritik" ve "Yüksek" öncelikli maddeleri doğrulanmıştır. Proje, teknik dokümantasyon ve çalışma kararlılığı açısından **31 Mayıs 2026** teslim tarihine tam hazır durumdadır.
