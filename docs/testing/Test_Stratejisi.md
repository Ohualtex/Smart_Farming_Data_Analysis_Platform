# 🧪 Test Stratejisi ve Geliştirici Yönergeleri

Smart Farming Data Analysis Platform (SFDAP), yüksek güvenilirlik hedefiyle geniş bir test kapsamına (test coverage) sahiptir.

Bu belge, repoya yeni kod ekleyecek takım üyelerinin test yazım standartlarını belirler; ayrıca geçmiş sprint'lerde uygulanan test senaryolarını, hata-ayıklama (debugging) kayıtlarını ve doğrulama kanıtlarını tek yerde toplar.

## 1. Test Çerçevesi (Framework)

- **Backend:** test koşucusu (test runner) olarak **`pytest`** kullanılır.
  - Kurulum: `pip install -r requirements-dev.txt`
  - Koşturma: `make test` (kapsamla birlikte; Schemathesis fuzz hariç tutulur)
  - Fuzz testleri: `make fuzz` (Schemathesis tabanlı şema fuzzing)
- **Frontend:** test koşucusu olarak **`vitest`** kullanılır.
  - Koşturma: `npm test` (frontend dizininde)

### Güncel Test Durumu

| Katman | Araç | Geçen Test | Not |
| :--- | :--- | :--- | :--- |
| Backend | pytest | **586** | Schemathesis fuzz (+64) lokalde `SKIP_SCHEMATHESIS=1` ile atlanır |
| Frontend | vitest | **74** | nav / tema / rol görünürlük davranışları dahil |

CI pipeline'da Ruff (lint) + Pytest (coverage) + Alembic migration smoke + bandit/pip-audit sürekli koşar.

## 2. Test Veritabanı ve Fixture'lar

Testler, üretim (production) veya geliştirme (development) veritabanı üzerinde **KOŞMAZ**. Yanlışlıkla verilerin silinmemesi için `tests/conftest.py` dosyasında özel bir mimari kurulmuştur.

- **In-Memory SQLite:** Testler başladığında hafızada geçici bir SQLite veritabanı yaratılır.
- **`client` Fixture'ı:** Test yazarken `client` parametresini fonksiyonunuza eklerseniz, FastAPI'nin test istemcisine ve temiz bir test veritabanına otomatik sahip olursunuz. Bu istemci, RBAC pivot'undan sonra header'ında otomatik olarak **admin Bearer JWT** ile gider (write işlemleri için).
- **`anon_client` Fixture'ı:** Hiçbir auth header'ı (Bearer veya X-API-Key) eklemez; yetkisiz erişim senaryolarını test etmek için kullanılır.
- **Rol bazlı yardımcılar:** `client` üstüne register + DB rol override + Bearer login bindirerek farmer/developer/overseer/admin rollerini ayrı ayrı test edebilirsiniz.

> **Auth notu:** Sistemde birincil kimlik doğrulama **Bearer JWT** (HS256, `/api/auth/login` üzerinden alınır). `X-API-Key` yalnızca `/api/model-performance` route'ları için legacy fallback olarak kalmıştır. Yeni testlerde yetkili istekler için Bearer token kullanın.

## 3. Örnek Test Yazımı

Yeni bir test yazarken aşağıdaki yapıyı kullanmalısınız:

```python
def test_example_endpoint(client):
    # 1. Hazırlık (Arrange)
    payload = {"isim": "Test Ciftlik", "sehir": "Ankara"}

    # 2. Aksiyon (Act) — `client` Bearer JWT'yi otomatik ekler
    response = client.post("/api/farms/", json=payload)

    # 3. Doğrulama (Assert)
    assert response.status_code == 201
    assert response.json()["sehir"] == "Ankara"
```

## 4. Test Metodolojisi (Üç Katmanlı Yaklaşım)

Sistemi test ederken üç katmanlı bir yaklaşım benimsenmiştir:

### A. Birim Testleri (Unit Testing)

Yazılımın en küçük yapı taşları olan API uç noktaları (endpoints) tek tek test edilir.

- **Amaç:** `app/main.py` üzerinden bağlanan 16 router'daki fonksiyonların beklenmedik durumlarda çökmesini engellemek.
- **Kapsam:** Sensör (`/api/sensors/`), Hava durumu (`/api/weather/`), Sulama (`/api/irrigation/`), Gübreleme (`/api/fertilizer/`), Bitki Sağlığı (`/api/plants/`), Analitik (`/api/analytics/`), Uyarı (`/api/alerts/`), Model Performansı (`/api/model-performance/`), kimlik doğrulama (`/api/auth/`) ve sağlık endpoint'leri dahil 67 endpoint.

### B. Entegrasyon ve Şema Validasyonu

Verilerin Pydantic v2 modelleri üzerinden geçişi sırasında uygulanan kısıtlamalar kontrol edilir.

- **Kontrol Noktası:** `SensorReadingCreate` (`moisture_percent`, `soil_temperature_c`) ve `WeatherDataCreate` (`temperature_c`, `humidity_percent`) alanlarının yanlış tip veya eksik gönderilmesi durumunda sistemin verdiği tepki (FastAPI'nin standart `422 Unprocessable Entity` cevabı).

### C. Güvenlik Denetimi (Security Audit)

Kimlik doğrulama katmanının kırılamazlığı üzerine yoğunlaşılır.

- **Metot:** Eksik/geçersiz token denemeleri, header eksikliği ve (legacy X-API-Key route'ları için) case-insensitive header testleri.
- **Davranış:** Bearer JWT korumalı endpoint'lerde token eksikse `401 Unauthorized`, yetersiz role sahip kullanıcıda `403 Forbidden` döndürülür. Legacy X-API-Key katmanında header eksikse `401`, anahtar geçersizse `403` döner ([app/middleware/auth.py](../../app/middleware/auth.py)).

## 5. Detaylı Test Senaryoları ve Sonuç Matrisi

Aşağıdaki tablo, sistemin temsili senaryolar karşısındaki davranışını detaylandırır:

| Senaryo Kodu | Test Tanımı | Test Girdisi (Input) | Beklenen Durum | Gerçekleşen Sonuç | Karar |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **AUTH-01** | Geçerli Token Erişimi | `Authorization: Bearer <jwt>` | 200 OK | 200 OK | ✅ BAŞARILI |
| **AUTH-02** | Eksik Header Erişimi | (auth header gönderilmedi) | 401 Unauthorized | 401 Unauthorized | ✅ BAŞARILI |
| **AUTH-03** | Yetersiz Rol Erişimi | Geçerli token, yetersiz rol | 403 Forbidden | 403 Forbidden | ✅ BAŞARILI |
| **AUTH-04** | Legacy Anahtar (model-performance) | `X-API-Key: hatali_anahtar` | 403 Forbidden | 403 Forbidden | ✅ BAŞARILI |
| **VALID-01** | Eksik Zorunlu Alan | `{"sensor_id": 1}` (`moisture_percent` yok) | 422 Error | 422 Unprocessable Entity | ✅ BAŞARILI |
| **VALID-02** | Hatalı Veri Tipi | `{"moisture_percent": "çok ıslak"}` | Type Error | 422 Validation Error | ✅ BAŞARILI |
| **VALID-03** | Veri Tipi Coercion | `SensorReadingCreate` (`moisture_percent` int/float) | Float/Int Coercion | Veri Tipleri Uyumlu | ✅ BAŞARILI |
| **DATA-01** | Veri Bütünlüğü | `GET /api/sensors/` (yetkili) | JSON List (`SensorResponse[]`) | JSON Formatı Okundu | ✅ BAŞARILI |
| **SYS-01** | Olmayan Kaynak Erişimi | `GET /api/unknown` | 404 Not Found | 404 Not Found | ✅ BAŞARILI |

## 6. Hata Ayıklama (Debugging) ve Doğrulama Logları

Testler sırasında "Siyah Kutu" ve "Beyaz Kutu" metodolojileriyle tespit edilen ve projenin güvenilirliğini artırmak için çözülen teknik problemler:

### 6.1. Veri Tipi Esnekliği / Pydantic Model Çakışması

- **Gözlem:** Sensörlerden gelen nem verisi bazen `45.0` (float), bazen `45` (int) olarak geliyordu. Pydantic şeması katı kuralları nedeniyle tam sayılarda `422` hatası veriyordu.
- **Aksiyon:** Pydantic v2'nin native int→float coercion davranışı doğrulandı; `SensorReadingCreate.moisture_percent` alanı ek özelleştirmeye gerek kalmadan her iki tipi de sorunsuz kabul ediyor.
- **Sonuç:** Veri kabul oranı %100'e çıkarıldı.

### 6.2. Header Case-Sensitivity (Büyük/Küçük Harf) Çakışması

- **Gözlem:** Bazı istemcilerin (tarayıcı / Postman sürümleri) `x-api-key` (küçük harf) gönderirken, sistemin `X-API-Key` (büyük harf) beklemesi erişim sorunlarına yol açtı.
- **Aksiyon:** FastAPI'nin `APIKeyHeader` sınıfı kullanılarak anahtar kontrolü case-insensitive hale getirildi ([app/middleware/auth.py:16](../../app/middleware/auth.py#L16)).
- **Sonuç:** Farklı istemcilerden gelen legacy istekler sorunsuz işlenmeye başlandı.

### 6.3. 401 vs 403 Status Kodu Ayrıştırma

- **Gözlem:** İlk implementasyonda eksik header ve geçersiz anahtar aynı `403` kodunu döndürüyordu; istemci tarafında "yeniden authentikasyon" ve "anahtar/token yenileme" akışları ayrışmıyordu.
- **Aksiyon:** RFC 7235'e uygun olarak header eksikse `401 Unauthorized`, anahtar/token geçersiz veya rol yetersizse `403 Forbidden` döndürülecek şekilde ayrıştırıldı.
- **Sonuç:** Frontend tarafında `401` cevabı login modal'ını tetikleyebilir hâle geldi.

### 6.4. Exception Handling (İstisna Yönetimi) Standardizasyonu

- **Gözlem:** Hata anlarında dönen JSON mesajları tutarsız formatlardaydı ve son kullanıcı için fazla teknik kalıyordu.
- **Aksiyon:** `app/middleware/exceptions.py` altında global exception handler kuruldu (`NotFound`, `Unauthorized`, `ValidationError`, vb.).
- **Sonuç:** Tüm hatalar (`401`, `403`, `404`, `422`, `5xx`) tutarlı `{error_code, message, detail}` standart formatına oturtuldu.

## 7. Validasyon ve Güvenilirlik Kanıtları

Sistemin kararlılığını ölçmek için yapılan testlerde elde edilen veriler:

- **Backend test suite:** 586 test `pytest` üzerinde yeşil (lokalde Schemathesis fuzz +64 `SKIP_SCHEMATHESIS=1` ile atlanır).
- **Frontend test suite:** 74 test `vitest` üzerinde yeşil.
- **Ortalama Yanıt Süresi:** ~12 ms (yerel TestClient + in-memory SQLite üzerinde).
- **Eşzamanlı İstek:** TestClient üzerinden ardışık atılan 10 istekte veri kaybı yaşanmadı.
- **Güvenlik Duvarı:** Auth koruması FastAPI Dependency Injection katmanında çalıştığı için yetkisiz erişim, handler fonksiyonlarına erişemeden 401/403 ile reddedilir.
- **Hata Mesajı Standardizasyonu:** Tüm hatalar global exception handler üzerinden tutarlı `{error_code, message, detail}` formatında döner.
- **Linter Durumu:** Ruff — All checks passed.

## 8. Kalite Kuralları

- Eklenen her yeni API endpoint'inin başarı durumu (HTTP 200/201) ve hata durumu (HTTP 404/422/401/403) mutlaka test edilmelidir.
- Frontend tarafında nav, tema ve rol görünürlük davranışları değiştiğinde ilgili `vitest` testleri güncellenmelidir.
- Sisteme kod pushlamadan önce lokalinizde `make test` (backend) ve `npm test` (frontend) komutlarını koşturup tüm testlerin geçtiğinden emin olun. (Kapsam eşiğinin altına düşerseniz CI pipeline GitHub üzerinde hata verecektir.)
