#!/usr/bin/env bash
# ============================================================
# SFDAP — Database Backup Script
# ============================================================
# Produces a backup for SQLite (dev) or PostgreSQL (prod), driven by
# the active DATABASE_URL.
#
# Kullanım:
#   ./scripts/backup.sh                       # default ayarlar
#   BACKUP_DIR=/var/backups ./scripts/backup.sh  # özel dizin
#   RETENTION_DAYS=14 ./scripts/backup.sh     # 14 günlük rotation
#
# Cron örneği (her gece 02:30):
#   30 2 * * * cd /opt/sfdap && DATABASE_URL=... ./scripts/backup.sh
#
# Makefile ile: `make backup`
# ============================================================

set -euo pipefail

# ─── Konfigürasyon (env-driven) ──────────────────────────────
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
DATABASE_URL="${DATABASE_URL:-sqlite:///./sfdap_dev.db}"

# Yedek dizini hazır mı?
mkdir -p "$BACKUP_DIR"

# Timestamp (sıralanabilir + okunabilir)
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "==> SFDAP Backup başlıyor ($(date '+%Y-%m-%d %H:%M:%S'))"
echo "    DATABASE_URL: ${DATABASE_URL%%://*}://***"
echo "    BACKUP_DIR:   $BACKUP_DIR"
echo "    RETENTION:    $RETENTION_DAYS gün"

# ─── DB type'a göre yedek al ─────────────────────────────────
if [[ "$DATABASE_URL" == sqlite* ]]; then
    # SQLite: sqlite3 .backup komutu (atomic, lock'sız)
    DB_FILE="${DATABASE_URL#sqlite:///}"
    BACKUP_FILE="$BACKUP_DIR/sfdap_${TIMESTAMP}.db"

    if [ ! -f "$DB_FILE" ]; then
        echo "❌ Hata: SQLite dosyası bulunamadı: $DB_FILE"
        exit 1
    fi

    sqlite3 "$DB_FILE" ".backup '$BACKUP_FILE'"
    echo "✅ SQLite yedek: $BACKUP_FILE ($(du -h "$BACKUP_FILE" | cut -f1))"

elif [[ "$DATABASE_URL" == postgresql* || "$DATABASE_URL" == postgres* ]]; then
    # PostgreSQL: pg_dump custom format (parallel restore'a uygun)
    BACKUP_FILE="$BACKUP_DIR/sfdap_${TIMESTAMP}.dump"

    if ! command -v pg_dump >/dev/null 2>&1; then
        echo "❌ Hata: pg_dump bulunamadı. PostgreSQL client kurulu olmalı."
        exit 1
    fi

    pg_dump --format=custom --no-owner --no-acl "$DATABASE_URL" > "$BACKUP_FILE"
    echo "✅ PostgreSQL yedek: $BACKUP_FILE ($(du -h "$BACKUP_FILE" | cut -f1))"

else
    echo "❌ Hata: Desteklenmeyen DATABASE_URL şeması: ${DATABASE_URL%%://*}"
    echo "   Desteklenen: sqlite, postgresql"
    exit 1
fi

# ─── Rotation: eski yedekleri sil ────────────────────────────
DELETED=$(find "$BACKUP_DIR" -name "sfdap_*" -type f -mtime +"$RETENTION_DAYS" -delete -print | wc -l | tr -d ' ')
if [ "$DELETED" -gt 0 ]; then
    echo "🗑️  $DELETED eski yedek silindi (>$RETENTION_DAYS gün)"
fi

# ─── Özet ────────────────────────────────────────────────────
TOTAL_BACKUPS=$(find "$BACKUP_DIR" -name "sfdap_*" -type f | wc -l | tr -d ' ')
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1 || echo "?")
echo "📦 Toplam: $TOTAL_BACKUPS yedek, $TOTAL_SIZE"
echo "==> Backup tamamlandı."
