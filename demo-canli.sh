#!/bin/bash
# ============================================================
# SFDAP — Demo Canlı Başlatma (TEK KOMUT)
# ============================================================
# Yaptığı: kurulum →  demo verisi  →  uygulama (:8000)  →  Cloudflare tunnel.
# Çalıştır:  ./demo-canli.sh
# Tunnel'ın yazdığı  https://...trycloudflare.com  URL'ini paylaş.
# Giriş:     admin@demo.test / 123456
# Durdur:    Ctrl+C  (uygulama + tunnel birlikte kapanır)
#
# Taze makinede ilk çalıştırma kendi kendine yeter:
#   - .venv yoksa oluşturur + requirements.txt yükler
#   - DB boşsa seed_data.py ile demo hesap/sensör/tarla doldurur (idempotent)
#   - cloudflared kurulu değilse kurulum komutunu söyler ve durur
# ============================================================
set -euo pipefail
cd "$(dirname "$0")"

# ─── 0/4: Ön koşullar ────────────────────────────────────────
# cloudflared zorunlu — yoksa anlamsız hata yerine net kurulum yönergesi.
if ! command -v cloudflared >/dev/null 2>&1; then
  echo "❌ 'cloudflared' bulunamadı. Kur ve tekrar çalıştır:"
  echo "   macOS:  brew install cloudflared"
  echo "   Linux:  https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
  exit 1
fi

# .venv yoksa oluştur + bağımlılıkları yükle (uvicorn import'u sentinel).
if [ ! -x .venv/bin/python ]; then
  echo "📦 [0/4] .venv yok — oluşturuluyor + bağımlılıklar yükleniyor (ilk sefer biraz sürer)..."
  python3 -m venv .venv
  .venv/bin/python -m pip install --quiet --upgrade pip
  .venv/bin/python -m pip install --quiet -r requirements.txt
  echo "   ✓ kurulum tamam"
elif ! .venv/bin/python -c "import uvicorn" >/dev/null 2>&1; then
  echo "📦 [0/4] Bağımlılıklar eksik — requirements.txt yükleniyor..."
  .venv/bin/python -m pip install --quiet -r requirements.txt
  echo "   ✓ bağımlılıklar tamam"
fi

# ─── 1/4: Demo veritabanı (idempotent) ───────────────────────
# DB boşsa demo hesap/sensör/tarla doldur; doluysa seed_database() kendisi atlar.
echo "🌱 [1/4] Demo veritabanı hazırlanıyor (idempotent)..."
PYTHONPATH=. .venv/bin/python database/seed_data.py 2>&1 | tail -1 || true

# ─── 2/4: Taze okumalar ──────────────────────────────────────
echo "🔄 [2/4] Demo verisi tazeleniyor (son 48h)..."
PYTHONPATH=. .venv/bin/python scripts/seed_demo_readings.py 2>&1 | tail -1

# ─── 3/4: Uygulama ───────────────────────────────────────────
echo "🚀 [3/4] Uygulama :8000'de başlatılıyor..."
.venv/bin/python -m uvicorn app.main:app --port 8000 > /tmp/sfdap-demo-app.log 2>&1 &
APP_PID=$!
trap 'echo; echo "🛑 Kapatılıyor..."; kill $APP_PID 2>/dev/null || true' EXIT INT TERM

for i in $(seq 1 30); do
  if curl -sf -o /dev/null http://localhost:8000/dashboard/ 2>/dev/null; then
    echo "   ✓ uygulama hazır"; break
  fi
  if ! kill -0 $APP_PID 2>/dev/null; then
    echo "   ✗ uygulama başlatılamadı — log: /tmp/sfdap-demo-app.log"; tail -20 /tmp/sfdap-demo-app.log; exit 1
  fi
  sleep 1
done

# ─── 4/4: Cloudflare tunnel ──────────────────────────────────
echo "🌐 [4/4] Cloudflare tunnel açılıyor — aşağıdaki HTTPS URL'ini paylaş:"
echo "        (giriş: admin@demo.test / 123456)"
echo ""
# caffeinate: macOS'ta demo boyunca uyku engellenir → tunnel kopmaz.
# cloudflared'in alt-süreci olur; Ctrl+C ile birlikte serbest kalır.
# Linux'ta caffeinate yok → doğrudan cloudflared çalışır.
if command -v caffeinate >/dev/null 2>&1; then
  caffeinate -dimsu cloudflared tunnel --url http://localhost:8000
else
  cloudflared tunnel --url http://localhost:8000
fi
