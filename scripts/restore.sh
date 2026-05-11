#!/usr/bin/env bash
# ============================================================
# SFDAP — Veritabanı Restore Script'i
# ============================================================
# `backup.sh` ile alınmış yedeği geri yükler. Hem SQLite hem PostgreSQL
# için çalışır. shiftFinal — Emirhan A4 görevi.
#
# Kullanım:
#   ./scripts/restore.sh ./backups/sfdap_20260520_023000.db        # SQLite
#   ./scripts/restore.sh ./backups/sfdap_20260520_023000.dump      # PostgreSQL
#
# ⚠️ DİKKAT: Mevcut veritabanı ÜZERİNE yazılır. Operasyon ÖNCESİ ek bir
#    backup almak iyi pratik (`make backup`).
#
# Makefile ile: `make restore BACKUP=./backups/sfdap_20260520.db`
# ============================================================

set -euo pipefail

# ─── Argüman kontrolü ────────────────────────────────────────
if [ -z "${1:-}" ]; then
    echo "Kullanım: $0 <backup-file>"
    echo ""
    echo "Mevcut yedekler:"
    BACKUP_DIR="${BACKUP_DIR:-./backups}"
    if [ -d "$BACKUP_DIR" ]; then
        ls -lh "$BACKUP_DIR"/sfdap_* 2>/dev/null | tail -10 || echo "  (yedek bulunamadı)"
    else
        echo "  (backup dizini yok: $BACKUP_DIR)"
    fi
    exit 1
fi

BACKUP_FILE="$1"
DATABASE_URL="${DATABASE_URL:-sqlite:///./sfdap_dev.db}"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Hata: Yedek dosyası bulunamadı: $BACKUP_FILE"
    exit 1
fi

echo "==> SFDAP Restore başlıyor ($(date '+%Y-%m-%d %H:%M:%S'))"
echo "    Yedek: $BACKUP_FILE ($(du -h "$BACKUP_FILE" | cut -f1))"
echo "    Hedef: ${DATABASE_URL%%://*}://***"
echo ""
echo "⚠️  UYARI: Mevcut veritabanı üzerine yazılacak."
read -p "    Devam etmek için 'EVET' yazın: " CONFIRM
if [ "$CONFIRM" != "EVET" ]; then
    echo "İptal edildi."
    exit 0
fi

# ─── DB type'a göre restore ──────────────────────────────────
if [[ "$BACKUP_FILE" == *.db ]] && [[ "$DATABASE_URL" == sqlite* ]]; then
    DB_FILE="${DATABASE_URL#sqlite:///}"
    # Güvenlik için mevcut DB'yi yedekle
    if [ -f "$DB_FILE" ]; then
        SAFETY_BACKUP="${DB_FILE}.before-restore-$(date +%Y%m%d_%H%M%S)"
        cp "$DB_FILE" "$SAFETY_BACKUP"
        echo "💾 Güvenlik yedeği: $SAFETY_BACKUP"
    fi
    cp "$BACKUP_FILE" "$DB_FILE"
    echo "✅ SQLite restore tamamlandı."

elif [[ "$BACKUP_FILE" == *.dump ]] && [[ "$DATABASE_URL" == postgresql* || "$DATABASE_URL" == postgres* ]]; then
    if ! command -v pg_restore >/dev/null 2>&1; then
        echo "❌ Hata: pg_restore bulunamadı."
        exit 1
    fi
    # --clean: önce drop, sonra recreate (tam restore)
    # --if-exists: drop sırasında olmayan obje hatası vermez
    pg_restore --clean --if-exists --no-owner --no-acl --dbname="$DATABASE_URL" "$BACKUP_FILE"
    echo "✅ PostgreSQL restore tamamlandı."

else
    echo "❌ Hata: Yedek format'ı DATABASE_URL ile uyuşmuyor."
    echo "   SQLite yedekler .db, PostgreSQL yedekler .dump uzantılı olmalı."
    exit 1
fi

echo "==> Restore tamamlandı."
