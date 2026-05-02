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

Yazma endpoint'leri (POST/DELETE/PATCH) `X-API-Key` header'ı zorunlu kılar.
Okuma endpoint'leri (GET) auth gerektirmez.

| Ortam | API Key |
|:------|:--------|
| Development (varsayılan) | `dev-api-key` |
| Production | `.env` dosyasındaki `API_KEY` (`ENVIRONMENT=production` iken default değer reddedilir) |

### Swagger UI üzerinden auth

1. `http://localhost:8000/docs`
2. Sağ üstteki **🔒 Authorize** butonuna tıkla
3. Value: `dev-api-key` yaz, **Authorize** → **Close**
4. Artık 🔒 simgeli endpoint'leri test edebilirsin

### curl üzerinden

```bash
curl -X POST http://localhost:8000/api/sensors/ \
  -H "X-API-Key: dev-api-key" \
  -H "Content-Type: application/json" \
  -d '{"field_id": 1, "sensor_type": "soil_moisture", "serial_number": "S-001"}'
```

---

## 3. Endpoint Kategorileri

| Kategori | Prefix | Örnek endpoint |
|:---------|:-------|:---------------|
| Health | `/api/health` | `GET /api/health`, `GET /api/health/deep` |
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
curl http://localhost:8000/api/sensors/1/readings?limit=10
```

### 4.4 Analitik özet (son 30 gün)

```bash
curl "http://localhost:8000/api/analytics/summary?days=30" | jq .counts
```

### 4.5 PDF rapor indir

```bash
curl "http://localhost:8000/api/analytics/export?format=pdf&days=30" -o rapor.pdf
```

### 4.6 İki periyot karşılaştır

```bash
curl "http://localhost:8000/api/analytics/compare?\
start_date_1=2026-04-01&end_date_1=2026-04-15&\
start_date_2=2026-04-16&end_date_2=2026-04-30"
```

### 4.7 Yeni sistem uyarısı oluştur (auth)

```bash
curl -X POST http://localhost:8000/api/alerts/ \
  -H "X-API-Key: dev-api-key" \
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
curl http://localhost:8000/api/health/deep | jq
```

DB, scheduler ve ML model bileşenlerinin durumunu döner.

---

## 5. Hata Kodları

| Kod | Anlam | Çözüm |
|:---:|:------|:------|
| 401 | API Key eksik | `X-API-Key` header'ı ekle |
| 403 | Geçersiz API Key | Doğru key gönder |
| 404 | Kayıt bulunamadı | ID'yi doğrula |
| 422 | Validation hatası | Body/query parametrelerini kontrol et |
| 429 | Rate limit aşıldı | Birkaç saniye bekle |
| 500 | Sunucu hatası | Log'lara bak (loguru `app/logs/sfdap.log`) |

Standart hata response'u:
```json
{
  "detail": "API anahtari eksik. 'X-API-Key' header'i gerekli."
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

**Mehmet Sait Tayşi** — Cycle 4/5/6 Görevi
