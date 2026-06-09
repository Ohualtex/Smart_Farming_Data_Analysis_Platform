#!/bin/sh
# SFDAP container entrypoint
# ==========================
# Prod'da DB şeması YALNIZ alembic migration'larıyla kurulur (create_all main.py
# lifespan'inde prod-dışına gate'li). Böylece şema alembic_version ile stamp'lenir,
# RBAC CHECK constraint'i + FK index'leri dahil olur ve `alembic upgrade head`
# DuplicateTable ile patlamaz (audit KRİTİK fix).
# Dev/test'te create_all yeterli olduğu için migration adımı yalnız production'da koşar.
set -e

if [ "$ENVIRONMENT" = "production" ]; then
  echo "[entrypoint] production → alembic upgrade head"
  alembic upgrade head
fi

# --proxy-headers + --forwarded-allow-ips: nginx'in X-Forwarded-For'una güvenip
# request.client.host'u GERÇEK client IP'sine çevirir → rate-limit + access-log
# nginx peer IP'si yerine gerçek client'ı görür (audit YÜKSEK: aksi halde tüm
# trafik tek bucket'a düşer, auth brute-force koruması çöker).
# api yalnız nginx'in eriştiği internal ağda (expose, public değil) olduğu için
# default '*' güvenli; daha sıkı kurulumda FORWARDED_ALLOW_IPS=<nginx IP> verin.
echo "[entrypoint] uvicorn başlatılıyor..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 \
  --proxy-headers --forwarded-allow-ips="${FORWARDED_ALLOW_IPS:-*}"
