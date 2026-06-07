# 📖 API Kullanım ve Test Kılavuzu

> **Not:** En güncel API referansı için projeyi çalıştırıp **`http://localhost:8000/docs`** üzerinden Swagger UI'a bakınız. Bu döküman özet ve örnekler içerir.

---

## 1. Hızlı Başlangıç

```bash
# Projeyi çalıştır
make run                # ya da: uvicorn app.main:app --reload

# Sonra tarayıcıdan:
#   API:        http://localhost:8000
#   Swagger:    http://localhost:8000/docs
#   Dashboard:  http://localhost:8000/dashboard
```

---

## 2. Kimlik Doğrulama

**Tüm API endpoint'leri** (GET dahil) `Authorization: Bearer <token>` header'ı ister. Token, `/api/auth/login` akışından elde edilir. Uygulama bcrypt parola hash + HS256 imzalı JWT kullanır.

> **Tek istisna — legacy `X-API-Key`:** Yalnız `/api/model-performance` altındaki 2 route eski `X-API-Key` header'ını kabul eder. Bunun dışındaki hiçbir endpoint X-API-Key ile çalışmaz; her zaman Bearer JWT kullanın.

| Ortam | API Key (yalnız `/api/model-performance` legacy) |
|:------|:--------|
| Development (varsayılan) | `dev-api-key` |
| Production | `.env` dosyasındaki `API_KEY` (`ENVIRONMENT=production` iken default değer reddedilir) |

### Kullanıcı Auth Akışı

| Method | Endpoint | Açıklama |
|:-------|:---------|:---------|
| POST | `/api/auth/register` | Email + parola → user kaydı (bcrypt hash) |
| POST | `/api/auth/login` | Email + parola → `{access_token}` döner (HS256 JWT) |
| GET | `/api/auth/me` | Bearer token ile mevcut kullanıcıyı döner |
| POST | `/api/auth/logout` | Token'ı in-memory blacklist'e atar |

```bash
# Register
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"farmer@example.com","password":"s3cret123","full_name":"Çiftçi Ahmet"}'

# Login → token al
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"farmer@example.com","password":"s3cret123"}' | jq -r .access_token)

# Korumalı endpoint (her endpoint Bearer ister)
curl http://localhost:8000/api/auth/me -H "Authorization: Bearer $TOKEN"
```

> **Demo hesaplar:** Seed verisindeki 6 demo hesabın hepsinin parolası `123456`'dır. Örn. login için herhangi bir demo email + `123456` kullanın.

> **Not:** Logout sırasında token in-memory blacklist'e eklenir; production'da bu blacklist Redis veya DB'ye taşınmalı.

### Swagger UI üzerinden auth

1. `http://localhost:8000/docs`
2. Önce `POST /api/auth/login` ile token al (demo email + `123456`)
3. Sağ üstteki **🔒 Authorize** butonuna tıkla
4. `bearerAuth` alanına token'ı yapıştır, **Authorize** → **Close**
5. Artık 🔒 simgeli endpoint'leri test edebilirsin

### curl üzerinden

```bash
curl -X POST http://localhost:8000/api/sensors/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"field_id": 1, "sensor_type": "soil_moisture", "serial_number": "S-001"}'
```

---

## 3. Endpoint Kategorileri

| Kategori | Prefix | Örnek endpoint |
|:---------|:-------|:---------------|
| Health | `/api/health` | `GET /api/health`, `GET /api/health/deep` |
| Auth (skeleton) | `/api/auth` | `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me` (Bearer) |
| Sensörler | `/api/sensors` | `GET /api/sensors/`, `POST /api/sensors/` (auth) |
| Hava Durumu | `/api/weather` | `GET /api/weather/`, `GET /api/weather/latest/{farm_id}` |
| Sulama (ML) | `/api/irrigation` | `POST /api/irrigation/predict` |
| Gübreleme | `/api/fertilizer` | `GET /api/fertilizer/crops` (17 bitki), `POST /api/fertilizer/recommend` |
| Bitki Sağlığı | `/api/plants` | `GET /api/plants/health-images` |
| Analitik | `/api/analytics` | `GET /api/analytics/summary?days=30`, `GET /api/analytics/export?format=pdf\|xlsx` |
| Sistem Uyarıları | `/api/alerts` | `GET /api/alerts/`, `POST /api/alerts/` (auth) |
| Model Performansı | `/api/model-performance` | `GET /api/model-performance/summary/{model_name}` |

Tam liste ve her endpoint'in detaylı parametreleri Swagger'da.

---

## 4. Örnek Akışlar (curl)

### 4.1 Sulama tahmini al (ML)

```bash
curl -X POST http://localhost:8000/api/irrigation/predict \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "soil_moisture": 30,
    "soil_temperature": 22,
    "humidity": 60,
    "temperature": 25,
    "precipitation": 2
  }'
```

**Yanıt:**
```json
{
  "recommended_water_liters": 28.37,
  "irrigation_needed": true,
  "confidence": 0.8,
  "message": "Orta duzeyde sulama gerekli: 28.37 litre."
}
```

### 4.2 Gübre önerisi al (NPK)

```bash
curl -X POST http://localhost:8000/api/fertilizer/recommend \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "crop_type": "tomato",
    "area_hectares": 1.0,
    "soil_nitrogen": 80,
    "soil_phosphorus": 40,
    "soil_potassium": 50,
    "soil_ph": 6.5
  }'
```

> `crop_type` değerleri: `wheat`, `corn`, `barley`, `rice`, `tomato`, `pepper`, `potato`, `cotton`, `sunflower`, `sugar_beet`, `olive`, `grape`, `apple`, `citrus`, `hazelnut`, `pistachio`, `tea` (17 bitki).

### 4.3 Sensör okumalarını listele

```bash
curl "http://localhost:8000/api/sensors/1/readings?limit=10" \
  -H "Authorization: Bearer $TOKEN"
```

### 4.4 Analitik özet (son 30 gün)

```bash
curl "http://localhost:8000/api/analytics/summary?days=30" \
  -H "Authorization: Bearer $TOKEN" | jq .counts
```

### 4.5 PDF rapor indir

```bash
curl "http://localhost:8000/api/analytics/export?format=pdf&days=30" \
  -H "Authorization: Bearer $TOKEN" -o rapor.pdf
```

### 4.6 İki periyot karşılaştır

```bash
curl "http://localhost:8000/api/analytics/compare?\
start_date_1=2026-04-01&end_date_1=2026-04-15&\
start_date_2=2026-04-16&end_date_2=2026-04-30" \
  -H "Authorization: Bearer $TOKEN"
```

### 4.7 Yeni sistem uyarısı oluştur (auth)

```bash
curl -X POST http://localhost:8000/api/alerts/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "farm_id": 1,
    "alert_type": "sensor_anomaly",
    "severity": "medium",
    "message": "Sensör 5 son 2 saatte veri göndermedi"
  }'
```

### 4.8 Derin sağlık kontrolü

```bash
curl http://localhost:8000/api/health/deep \
  -H "Authorization: Bearer $TOKEN" | jq
```

DB, scheduler ve ML model bileşenlerinin durumunu döner.

---

## 5. Hata Kodları

| Kod | Anlam | Çözüm |
|:---:|:------|:------|
| 401 | Bearer token eksik veya geçersiz | `/api/auth/login` ile token al, `Authorization: Bearer <token>` header'ı ekle |
| 403 | Yetki yetersiz (rol/erişim) | Hesabın rolünü/erişimini doğrula |
| 404 | Kayıt bulunamadı | ID'yi doğrula |
| 422 | Validation hatası | Body/query parametrelerini kontrol et |
| 429 | Rate limit aşıldı | Birkaç saniye bekle |
| 500 | Sunucu hatası | Log'lara bak (loguru `app/logs/sfdap.log`) |

Standart hata response'u:
```json
{
  "detail": "Not authenticated"
}
```

---

## 6. Postman Collection

Repo kökünde `docs/api/SFDAP.postman_collection.json` (varsa) Postman'e import edilebilir.
Yoksa Swagger'dan `/openapi.json`'u export edip Postman'in **Import → OpenAPI** özelliği ile yükleyin.

---

## 7. Geliştirici Notları

- Tüm yazma endpoint'leri `slowapi` ile rate-limit'lidir (varsayılan 100 req/min).
- Tarih parametreleri ISO 8601 formatında (örn. `2026-04-30T15:00:00Z`).
- Pagination için `?skip=` ve `?limit=` query parametreleri (çoğu list endpoint'inde).
- CORS sadece `settings.CORS_ORIGINS` listesindeki origin'lere açık.
