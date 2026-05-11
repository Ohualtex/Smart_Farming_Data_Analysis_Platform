# 🚀 SFDAP Production Deploy — nginx + Let's Encrypt

> Cycle 8 — HTTPS / reverse proxy konfigürasyonu (Miraç Duran)

Bu kılavuz, Docker üzerinde SFDAP'i nginx reverse proxy + Let's Encrypt TLS ile prod-hazır şekilde başlatma adımlarını gösterir.

## 📋 Önkoşullar

- **Sunucu:** 1 GB RAM minimum (2 GB+ önerilir), Linux (Ubuntu 22.04 / Debian 12 test edildi)
- **Domain:** Public IP'ye yönlendirilmiş bir A/AAAA kaydı (`farm.example.com` gibi)
- **Portlar:** 80 ve 443 firewall'da açık
- **Yazılım:** Docker Engine 24+ ve Docker Compose v2

---

## 1. ⚙️ Environment Hazırlığı

```bash
# Repoyu klonla
git clone https://github.com/Ohualtex/Smart_Farming_Data_Analysis_Platform.git
cd Smart_Farming_Data_Analysis_Platform

# .env dosyası oluştur ve düzenle
cp .env.example .env
```

`.env`'de **mutlaka** override edilecek değerler:

```bash
ENVIRONMENT=production
DOMAIN=farm.ornek.com               # ← KENDİ DOMAIN'INIZ
EMAIL=admin@ornek.com               # ← Let's Encrypt iletişim e-posta'sı
API_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
CORS_ORIGINS=https://farm.ornek.com
```

> ⚠️ `ENVIRONMENT=production` set edildiğinde uygulama default API_KEY/SECRET_KEY ile başlamayı reddeder (`config.py:_validate_production` fail-fast).

---

## 2. 🔐 İlk SSL Sertifikası (Let's Encrypt)

İlk sertifikayı almak için 3 adım gerekir:

### 2.1 Geçici HTTP-only nginx ile dummy cert

`nginx/conf.d/default.conf.template` HTTPS dinleyici içerir; gerçek cert olmadan nginx başlamaz. Bu yüzden önce certbot'un ihtiyacı olan dizinleri oluşturup, geçici bir self-signed cert üretelim:

```bash
# Volume'leri yarat (boş)
docker compose --profile letsencrypt run --rm --entrypoint sh certbot \
  -c "mkdir -p /etc/letsencrypt/live/$DOMAIN /var/www/certbot \
      && openssl req -x509 -nodes -days 1 \
        -newkey rsa:2048 \
        -keyout /etc/letsencrypt/live/$DOMAIN/privkey.pem \
        -out /etc/letsencrypt/live/$DOMAIN/fullchain.pem \
        -subj '/CN=$DOMAIN' \
      && cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem \
            /etc/letsencrypt/live/$DOMAIN/chain.pem"
```

### 2.2 nginx + api başlat (geçici cert ile)

```bash
docker compose up -d nginx api
```

Test et: `curl -k https://$DOMAIN/api/health` 200 dönmeli.

### 2.3 Gerçek Let's Encrypt cert al

```bash
docker compose --profile letsencrypt run --rm certbot certonly \
  --webroot -w /var/www/certbot \
  -d "$DOMAIN" \
  --email "$EMAIL" \
  --agree-tos --no-eff-email --force-renewal
```

Sertifika `certbot_etc` volume'üne yazılır. nginx'i yeniden yükle:

```bash
docker compose exec nginx nginx -s reload
```

Doğrula: `curl https://$DOMAIN/api/health` artık geçerli sertifikayla 200 dönmeli.

---

## 3. 🗄️ PostgreSQL'e Geçiş (Opsiyonel)

Default SQLite, prod yükü için yeterli değil. PostgreSQL'e geçmek için:

```bash
# .env'e ekle:
DATABASE_URL=postgresql+psycopg2://sfdap_user:sfdap_password@db:5432/sfdap_db

# postgres servisini başlat
docker compose --profile postgres up -d db

# Migration'ları uygula (Cycle 8 #4 ile gelen 14-tablo initial)
docker compose exec api alembic upgrade head

# Seed data (opsiyonel — 81 il + 7500+ kayıt)
docker compose exec api python database/seed_data.py
```

---

## 4. 🔄 Sertifika Yenileme (Cron)

Let's Encrypt cert'leri 90 gün geçerli. Otomatik yenileme için crontab'a ekle:

```cron
# Her hafta Pazar 03:00 — sadece <30 gün kaldıysa yeniler
0 3 * * 0  cd /opt/sfdap && docker compose --profile letsencrypt run --rm certbot renew --quiet && docker compose exec nginx nginx -s reload
```

---

## 5. ✅ Doğrulama Checklist

| Test | Komut / URL | Beklenen |
|:-----|:------------|:---------|
| HTTP redirect | `curl -I http://$DOMAIN` | 301 → HTTPS |
| HTTPS sertifika | `curl -vI https://$DOMAIN 2>&1 \| grep "issuer"` | Let's Encrypt |
| API health | `curl https://$DOMAIN/api/health` | `{"status":"healthy"}` |
| API auth (eksik key) | `curl -X POST https://$DOMAIN/api/sensors/` | 401 Unauthorized |
| Rate limit | `for i in {1..40}; do curl -X POST https://$DOMAIN/api/auth/login -d '{}'; done` | bir noktada 429 |
| HSTS header | `curl -sI https://$DOMAIN \| grep -i strict-transport` | `max-age=15552000` |
| Swagger | `https://$DOMAIN/docs` | Swagger UI |

---

## 6. 🛠️ Sık Karşılaşılan Sorunlar

### "nginx: [emerg] cannot load certificate"
İlk başlatmada cert yokken görülür. Adım 2.1'deki dummy cert oluşturma komutunu çalıştırın.

### "ACME challenge failed: connection refused"
Port 80 kapalı veya DNS henüz propagate olmamış. Test:
```bash
curl http://$DOMAIN/.well-known/acme-challenge/test
# 404 dönmeli (dosya yok ama nginx erişilebilir demek)
```

### "Production'da default API_KEY kullanılamaz"
`config.py:_validate_production` fail-fast tetiklendi. `.env`'de `API_KEY` ve `SECRET_KEY`'i gerçek random değerlerle override edin (önkoşul tablosundaki Python tek-satır komutu).

### Plant uploads container yeniden başlatınca kaybolur
`app/ml/plant_uploads/` Dockerfile'da kopyalanmış ama bind-mount edilmemiş. Production'da volume olarak ekleyin:
```yaml
volumes:
  - plant_uploads:/app/app/ml/plant_uploads
```
ve `volumes:` bölümünde `plant_uploads:` tanımlayın.

---

## 📚 İlgili Dosyalar

- [`docker-compose.yml`](../../docker-compose.yml) — servis tanımları (api, nginx, certbot, db)
- [`nginx/conf.d/default.conf.template`](../../nginx/conf.d/default.conf.template) — nginx reverse proxy şablonu
- [`.env.example`](../../.env.example) — environment variable referansı
- [`alembic/versions/`](../../alembic/versions/) — DB migration'ları (Cycle 8 #4)

---

**Cycle 8 — Üretim Hazırlığı, Güvenlik ve Cila tamamlandı.**
