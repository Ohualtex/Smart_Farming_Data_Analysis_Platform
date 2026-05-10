"""
Sensor Archiver Service Tests
================================
`app/services/sensor_archiver.archive_old_readings` davranışı:
- Cutoff'tan eski okumalar aggregate'e taşınır + kaynak satırlar silinir
- <30 gün okumalar dokunulmaz
- Idempotent: aynı pencere için ikinci kez çağrılırsa duplicate üretmez,
  mevcut aggregate'i merge eder
- Aggregate metrikleri (count + avg/min/max) doğru
- Boş DB'de no-op davranışı
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.models.models import (
    Farm,
    Field,
    Sensor,
    SensorReadingMonthlyAggregate,
    SoilMoistureReading,
    User,
)
from app.services.sensor_archiver import archive_old_readings

# ─── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def sensor_setup(db):
    """User → Farm → Field → Sensor zinciri (archiver testleri için)."""
    user = User(name="Archiver Test", email="archiver@x.com", role="farmer", password_hash="x")
    db.add(user)
    db.flush()
    farm = Farm(user_id=user.id, name="Archiver Farm", city="X", region="X")
    db.add(farm)
    db.flush()
    field = Field(farm_id=farm.id, name="F1")
    db.add(field)
    db.flush()
    sensor = Sensor(field_id=field.id, sensor_type="soil_moisture", serial_number="ARCH-1")
    db.add(sensor)
    db.commit()
    db.refresh(sensor)
    return sensor


def _add_reading(db, sensor_id: int, days_ago: int, moisture: float, soil_temp: float | None = None):
    """Belirli `days_ago` günlük geçmiş timestamp ile bir okuma ekler."""
    db.add(
        SoilMoistureReading(
            sensor_id=sensor_id,
            reading_timestamp=datetime.now(UTC) - timedelta(days=days_ago),
            moisture_percent=moisture,
            soil_temperature_c=soil_temp,
        )
    )


# ─── Behavioral tests ──────────────────────────────────────────────────


class TestArchiveOldReadings:
    """Akışın temel davranışı."""

    def test_empty_db_is_noop(self, db):
        """Hiç ham okuma yoksa fonksiyon hata vermeden 0/0 döner."""
        result = archive_old_readings(db)
        assert result.is_noop
        assert result.aggregates_written == 0
        assert result.readings_deleted == 0

    def test_recent_readings_are_kept(self, db, sensor_setup):
        """30 günden yeni okumalar dokunulmamalı."""
        _add_reading(db, sensor_setup.id, days_ago=5, moisture=40.0)
        _add_reading(db, sensor_setup.id, days_ago=15, moisture=42.0)
        db.commit()

        result = archive_old_readings(db)
        assert result.is_noop
        # Hâlâ 2 okuma duruyor
        assert db.query(SoilMoistureReading).count() == 2
        assert db.query(SensorReadingMonthlyAggregate).count() == 0

    def test_old_readings_archived_and_deleted(self, db, sensor_setup):
        """45 gün önceki okumalar aggregate'e taşınır, kaynak satırlar silinir."""
        for moisture in (30.0, 45.0, 60.0):
            _add_reading(db, sensor_setup.id, days_ago=45, moisture=moisture, soil_temp=20.0)
        db.commit()

        result = archive_old_readings(db)

        assert result.aggregates_written == 1
        assert result.readings_deleted == 3
        # Ham satırlar silindi
        assert db.query(SoilMoistureReading).count() == 0
        # 1 aggregate satır oluştu
        agg = db.query(SensorReadingMonthlyAggregate).first()
        assert agg is not None
        assert agg.sensor_id == sensor_setup.id
        assert agg.reading_count == 3
        assert agg.moisture_min == 30.0
        assert agg.moisture_max == 60.0
        assert agg.moisture_avg == pytest.approx(45.0)

    def test_separate_months_get_separate_aggregates(self, db, sensor_setup):
        """Farklı ay/yıllardaki okumalar ayrı aggregate satırı oluşturur."""
        # 35 gün önce (1 aylık önce) ve 65 gün önce (2 aylık önce)
        _add_reading(db, sensor_setup.id, days_ago=35, moisture=50.0)
        _add_reading(db, sensor_setup.id, days_ago=65, moisture=40.0)
        db.commit()

        result = archive_old_readings(db)
        assert result.aggregates_written == 2
        assert db.query(SensorReadingMonthlyAggregate).count() == 2

    def test_idempotent_merge_on_second_call(self, db, sensor_setup):
        """Aynı pencerede ikinci koşum yeni aggregate yaratmaz, var olanı merge eder."""
        # İlk batch: 45 gün önce, 2 okuma
        _add_reading(db, sensor_setup.id, days_ago=45, moisture=40.0)
        _add_reading(db, sensor_setup.id, days_ago=45, moisture=60.0)
        db.commit()
        first = archive_old_readings(db)
        assert first.aggregates_written == 1

        # Aynı aya yeni 45-günlük okuma daha gelirse (geç IoT akışı senaryosu)
        _add_reading(db, sensor_setup.id, days_ago=45, moisture=80.0)
        db.commit()

        second = archive_old_readings(db)
        # Yeni satır yaratılmadı; aynı aggregate güncellendi
        assert db.query(SensorReadingMonthlyAggregate).count() == 1
        agg = db.query(SensorReadingMonthlyAggregate).one()
        assert agg.reading_count == 3
        # Ağırlıklı ortalama: ((40+60)/2 * 2 + 80 * 1) / 3 = (100 + 80) / 3 = 60.0
        assert agg.moisture_avg == pytest.approx(60.0)
        assert agg.moisture_min == 40.0
        assert agg.moisture_max == 80.0
        assert second.aggregates_written == 1
        assert second.readings_deleted == 1

    def test_null_soil_temperature_handled(self, db, sensor_setup):
        """soil_temperature_c None olan okumalar avg/min/max'i bozmamalı."""
        _add_reading(db, sensor_setup.id, days_ago=45, moisture=50.0, soil_temp=None)
        _add_reading(db, sensor_setup.id, days_ago=45, moisture=55.0, soil_temp=22.0)
        db.commit()

        result = archive_old_readings(db)
        agg = db.query(SensorReadingMonthlyAggregate).one()
        assert agg.reading_count == 2
        assert agg.soil_temperature_avg == pytest.approx(22.0)  # tek None-olmayan
        assert agg.soil_temperature_min == 22.0
        assert agg.soil_temperature_max == 22.0
        assert result.readings_deleted == 2

    def test_custom_cutoff_days_param(self, db, sensor_setup):
        """`cutoff_days` parametresi 30 dışında verildiğinde de doğru çalışır."""
        _add_reading(db, sensor_setup.id, days_ago=10, moisture=50.0)
        db.commit()

        # 5 gün cutoff ile 10 günlük okuma silinmeli
        result = archive_old_readings(db, cutoff_days=5)
        assert result.readings_deleted == 1
        assert db.query(SoilMoistureReading).count() == 0


class TestArchiveResult:
    """`ArchiveResult.is_noop` property kontrolü."""

    def test_is_noop_when_no_readings_deleted(self, db):
        result = archive_old_readings(db)
        assert result.is_noop is True

    def test_is_not_noop_when_readings_deleted(self, db, sensor_setup):
        _add_reading(db, sensor_setup.id, days_ago=45, moisture=50.0)
        db.commit()
        result = archive_old_readings(db)
        assert result.is_noop is False
