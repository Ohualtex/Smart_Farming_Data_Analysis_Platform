#!/bin/bash
# ============================================================
# SFDAP — Demo Canlı Başlatma (TEK KOMUT)
# ============================================================
# Yaptığı: taze demo verisi  →  uygulama (:8000)  →  Cloudflare tunnel.
# Çalıştır:  ./demo-canli.sh
# Tunnel'ın yazdığı  https://...trycloudflare.com  URL'ini paylaş.
# Giriş:     admin@demo.test / 123456
# Durdur:    Ctrl+C  (uygulama + tunnel birlikte kapanır)
# ============================================================
set -e
cd "$(dirname "$0")"

echo "🌱 [1/3] Demo verisi tazeleniyor..."
PYTHONPATH=. .venv/bin/python scripts/seed_demo_readings.py 2>&1 | tail -1

echo "🚀 [2/3] Uygulama :8000'de başlatılıyor..."
.venv/bin/python -m uvicorn app.main:app --port 8000 > /tmp/sfdap-demo-app.log 2>&1 &
APP_PID=$!
trap 'echo; echo "🛑 Kapatılıyor..."; kill $APP_PID 2>/dev/null' EXIT INT TERM

for i in $(seq 1 30); do
  if curl -sf -o /dev/null http://localhost:8000/dashboard/ 2>/dev/null; then
    echo "   ✓ uygulama hazır"; break
  fi
  sleep 1
done

echo "🌐 [3/3] Cloudflare tunnel açılıyor (☕ uyku engellendi) — aşağıdaki HTTPS URL'ini paylaş:"
echo "        (giriş: admin@demo.test / 123456)"
echo ""
# caffeinate: demo boyunca Mac uyumasın (idle/display/system) → tunnel kopmaz.
# cloudflared'in alt-süreci olarak çalışır; Ctrl+C ile birlikte serbest kalır.
# (macOS yerleşik komutu, kurulum gerekmez.)
caffeinate -dimsu cloudflared tunnel --url http://localhost:8000
