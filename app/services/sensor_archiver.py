"""
Sensor Readings Archival Service
==================================
Folds `SoilMoistureReading` rows older than 30 days into the per-
(sensor, year, month) `SensorReadingMonthlyAggregate` table. Keeps the
IoT-stream insert path from bloating its hot table.

Atomic single-transaction flow:
1) Fetch readings older than `cutoff = now - 30 days`.
2) Group by (sensor_id, year, month); compute count + avg/min/max
   moisture, avg/min/max `soil_temperature_c`, avg
   `electrical_conductivity` per group.
3) If an aggregate row exists (idempotency) **merge**: sum counts,
   weighted-avg recompute, min/max update.
4) Upsert aggregates.
5) Delete the source readings (no cascade needed — no FK).
6) Commit.

On error: rollback. Returns (archived_count, deleted_count); caller
(scheduler or manual) logs these numbers.

---

30 günden eski sensor okumalarını ay bazlı aggregate'e indiren idempotent
arşivleyici. Aynı pencerede yeniden çalışınca mevcut aggregate'le
birleştirir; çift kayıt üretmez.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from loguru import logger
from sqlalchemy.orm import Session

from app.models.models import SensorReadingMonthlyAggregate, SoilMoistureReading

# Age cutoff for archival (in days). Can be promoted to an env later.
# ---
# Bu yaştan eski okumalar arşivlenir; ileride env'e taşınabilir.
DEFAULT_ARCHIVE_CUTOFF_DAYS = 30


@dataclass(frozen=True)
class ArchiveResult:
    """Bir arşivleme koşusunun çıktısı (caller log'lar)."""

    aggregates_written: int  # yeni veya güncellenen aggregate satır sayısı
    readings_deleted: int  # silinen ham okuma sayısı
    cutoff: datetime  # bu koşumda kullanılan eşik

    @property
    def is_noop(self) -> bool:
        """Hiç ham okuma yoktu — yapılacak iş yok."""
        return self.readings_deleted == 0


def _aggregate_group(rows: list[SoilMoistureReading]) -> dict:
    """Bir (sensor_id, year, month) grubu için özet metrikleri üret."""
    moistures = [r.moisture_percent for r in rows if r.moisture_percent is not None]
    temps = [r.soil_temperature_c for r in rows if r.soil_temperature_c is not None]
    conds = [r.electrical_conductivity for r in rows if r.electrical_conductivity is not None]

    return {
        "reading_count": len(rows),
        "moisture_avg": sum(moistures) / len(moistures) if moistures else 0.0,
        "moisture_min": min(moistures) if moistures else 0.0,
        "moisture_max": max(moistures) if moistures else 0.0,
        "soil_temperature_avg": sum(temps) / len(temps) if temps else None,
        "soil_temperature_min": min(temps) if temps else None,
        "soil_temperature_max": max(temps) if temps else None,
        "electrical_conductivity_avg": sum(conds) / len(conds) if conds else None,
    }


def _merge_into_existing(existing: SensorReadingMonthlyAggregate, group: dict) -> None:
    """Yeniden çalıştırma idempotency'si — mevcut aggregate'i yeni grup ile birleştir.

    Ağırlıklı ortalama formülü:
        new_avg = (old_avg * old_count + new_avg * new_count) / (old_count + new_count)

    EN: Idempotent merge — recompute weighted averages and broaden min/max
    so the aggregate stays consistent if archive_old_readings re-runs.
    """
    total_count = existing.reading_count + group["reading_count"]

    def _weighted(old_avg: float | None, new_avg: float | None) -> float | None:
        if old_avg is None and new_avg is None:
            return None
        if old_avg is None:
            return new_avg
        if new_avg is None:
            return old_avg
        return (old_avg * existing.reading_count + new_avg * group["reading_count"]) / total_count

    existing.moisture_avg = _weighted(existing.moisture_avg, group["moisture_avg"])
    existing.moisture_min = min(existing.moisture_min, group["moisture_min"])
    existing.moisture_max = max(existing.moisture_max, group["moisture_max"])
    existing.soil_temperature_avg = _weighted(existing.soil_temperature_avg, group["soil_temperature_avg"])
    if group["soil_temperature_min"] is not None:
        existing.soil_temperature_min = (
            min(existing.soil_temperature_min, group["soil_temperature_min"])
            if existing.soil_temperature_min is not None
            else group["soil_temperature_min"]
        )
    if group["soil_temperature_max"] is not None:
        existing.soil_temperature_max = (
            max(existing.soil_temperature_max, group["soil_temperature_max"])
            if existing.soil_temperature_max is not None
            else group["soil_temperature_max"]
        )
    existing.electrical_conductivity_avg = _weighted(
        existing.electrical_conductivity_avg, group["electrical_conductivity_avg"]
    )
    existing.reading_count = total_count
    existing.archived_at = datetime.now(UTC)


def archive_old_readings(db: Session, cutoff_days: int = DEFAULT_ARCHIVE_CUTOFF_DAYS) -> ArchiveResult:
    """`cutoff_days` günden eski okumaları aylık özet tabloya taşır.

    Tek bir transaction içinde:
    - Aggregate satırlarını upsert et (sensor_id × year × month).
    - Kaynak `SoilMoistureReading` kayıtlarını sil.
    - Commit.

    EN: Moves readings older than `cutoff_days` into the monthly
    aggregate table and deletes the source rows in a single transaction.
    """
    cutoff = datetime.now(UTC) - timedelta(days=cutoff_days)
    old_readings = db.query(SoilMoistureReading).filter(SoilMoistureReading.reading_timestamp < cutoff).all()

    if not old_readings:
        logger.info(f"sensor_archiver: cutoff={cutoff.isoformat()} — taşınacak kayıt yok")
        return ArchiveResult(aggregates_written=0, readings_deleted=0, cutoff=cutoff)

    # Grupla: (sensor_id, year, month) → list[reading]
    groups: dict[tuple[int, int, int], list[SoilMoistureReading]] = defaultdict(list)
    for r in old_readings:
        if r.reading_timestamp is None:
            continue
        key = (r.sensor_id, r.reading_timestamp.year, r.reading_timestamp.month)
        groups[key].append(r)

    aggregates_written = 0
    try:
        for (sensor_id, year, month), rows in groups.items():
            metrics = _aggregate_group(rows)
            existing = (
                db.query(SensorReadingMonthlyAggregate)
                .filter(
                    SensorReadingMonthlyAggregate.sensor_id == sensor_id,
                    SensorReadingMonthlyAggregate.year == year,
                    SensorReadingMonthlyAggregate.month == month,
                )
                .first()
            )
            if existing is None:
                db.add(
                    SensorReadingMonthlyAggregate(
                        sensor_id=sensor_id,
                        year=year,
                        month=month,
                        **metrics,
                    )
                )
            else:
                _merge_into_existing(existing, metrics)
            aggregates_written += 1

        # Kaynak okumaları sil (cascade FK yok, manuel delete güvenli)
        # EN: Delete source readings; no cascading FK so manual delete is safe.
        deleted = (
            db.query(SoilMoistureReading)
            .filter(SoilMoistureReading.reading_timestamp < cutoff)
            .delete(synchronize_session=False)
        )
        db.commit()
        logger.info(
            f"sensor_archiver: {aggregates_written} aggregate yazıldı, "
            f"{deleted} ham kayıt silindi (cutoff={cutoff.isoformat()})"
        )
        return ArchiveResult(aggregates_written=aggregates_written, readings_deleted=deleted, cutoff=cutoff)
    except Exception:
        db.rollback()
        logger.exception("sensor_archiver: arşivleme başarısız, rollback edildi")
        raise
