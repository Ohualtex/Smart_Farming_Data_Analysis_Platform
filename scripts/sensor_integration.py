# =============================================
# SFDAP - Sensor Data Integration Module
# =============================================
# Purpose: Clean, validate, and persist soil moisture sensor readings.
# ---
# Amaç: Toprak nem sensörü verilerini temizle, doğrula ve veritabanına kaydet.
# =============================================

from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# =============================================
# SABITLER VE KONFİGÜRASYON
# =============================================

# Resolve the project root: scripts/ → repo root → database/sfdap.db
current_dir = Path(__file__).parent.resolve()
PROJECT_ROOT = current_dir.parent
DATABASE_PATH = PROJECT_ROOT / "database" / "sfdap.db"

# Windows uyumu için path'i düzeltle
db_path_str = str(DATABASE_PATH).replace("\\", "/")
DATABASE_URL = f"sqlite:///{db_path_str}"

# Nem sensörü doğrulama aralıkları
MOISTURE_MIN_PERCENT = 0
MOISTURE_MAX_PERCENT = 100

# Sıcaklık doğrulama aralıkları (gerçekçi toprak sıcaklığı)
TEMPERATURE_MIN_C = -10
TEMPERATURE_MAX_C = 60

# Elektrik iletkenliği aralığı (dS/m)
EC_MIN_DS_M = 0
EC_MAX_DS_M = 10


# =============================================
# VERİ ÜRETİMİ (Data Generation)
# =============================================


def generate_sample_raw_data(num_records: int = 20) -> pd.DataFrame:
    """
    Ham sensör verileri üretir - geçerli, hatalı ve eksik değerler içerir.

    Args:
        num_records: Oluşturulacak kayıt sayısı (varsayılan: 20)

    Returns:
        DataFrame: Ham sensör verileri
    """

    # Temel veriler
    base_date = datetime.now(UTC)
    data = {
        "sensor_id": np.random.randint(1, 5, num_records),
        "reading_timestamp": [base_date - timedelta(hours=i) for i in range(num_records)],
        "moisture_percent": [],
        "depth_cm": np.random.choice([15, 30, 45, 60], num_records),
        "soil_temperature_c": [],
        "electrical_conductivity": np.random.uniform(0.8, 4.0, num_records),
    }

    # Nem değerleri: geçerli, hatalı ve eksik
    moisture_values = [
        35.5,
        42.3,
        28.7,
        65.2,
        75.1,  # Geçerli veriler
        150.0,
        200.5,
        -50.0,  # Hatalı (aralık dışı)
        np.nan,
        np.nan,  # Eksik veriler
        45.0,
        38.9,
        52.1,
        71.4,
        88.3,  # Geçerli veriler
        105.0,
        -30.0,  # Hatalı (aralık dışı)
        np.nan,  # Eksik veri
        33.2,
        67.8,
        48.5,  # Geçerli veriler
    ]
    data["moisture_percent"] = moisture_values[:num_records]

    # Sıcaklık değerleri: geçerli, hatalı ve eksik
    temperature_values = [
        22.5,
        21.8,
        23.1,
        24.2,
        25.0,  # Geçerli veriler
        -99.0,
        150.0,
        -85.5,  # Hatalı (aralık dışı)
        np.nan,
        np.nan,  # Eksik veriler
        20.3,
        22.7,
        24.5,
        26.1,
        23.9,  # Geçerli veriler
        999.0,
        -50.0,  # Hatalı (aralık dışı)
        np.nan,  # Eksik veri
        21.5,
        23.0,
        25.5,  # Geçerli veriler
    ]
    data["soil_temperature_c"] = temperature_values[:num_records]

    return pd.DataFrame(data)


# =============================================
# VERİ TEMİZLEME (Data Cleaning - ETL)
# =============================================


def clean_moisture_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Nem değerlerini %0-100 aralığına filtreler.
    Hatalı değerleri NaN ile değiştirir.

    Args:
        df: Temizlenecek DataFrame

    Returns:
        DataFrame: Temizlenmiş DataFrame
    """

    df_cleaned = df.copy()

    # Nem değerini aralık dışında olanları NaN'a çevir
    invalid_mask = (df_cleaned["moisture_percent"] < MOISTURE_MIN_PERCENT) | (
        df_cleaned["moisture_percent"] > MOISTURE_MAX_PERCENT
    )

    df_cleaned.loc[invalid_mask, "moisture_percent"] = np.nan

    return df_cleaned


def clean_temperature_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Sıcaklık değerlerini gerçekçi aralıkla (-10°C ile 60°C) filtreler.
    Hatalı değerleri NaN ile değiştirir.

    Args:
        df: Temizlenecek DataFrame

    Returns:
        DataFrame: Temizlenmiş DataFrame
    """

    df_cleaned = df.copy()

    # Sıcaklık değerini aralık dışında olanları NaN'a çevir
    invalid_mask = (df_cleaned["soil_temperature_c"] < TEMPERATURE_MIN_C) | (
        df_cleaned["soil_temperature_c"] > TEMPERATURE_MAX_C
    )

    df_cleaned.loc[invalid_mask, "soil_temperature_c"] = np.nan

    return df_cleaned


def clean_timestamp_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Timestamp sütununu güncel tarih/saat formatına dönüştürür.
    Eksik zaman damgalarını şimdiki zamana ayarlar.

    Args:
        df: Temizlenecek DataFrame

    Returns:
        DataFrame: Temizlenmiş DataFrame
    """

    df_cleaned = df.copy()

    # Timestamp'ı datetime'a dönüştür
    df_cleaned["reading_timestamp"] = pd.to_datetime(df_cleaned["reading_timestamp"], errors="coerce")

    # Eksik timestamp'ları şimdiki zamana ayarla
    missing_timestamp = df_cleaned["reading_timestamp"].isna()
    df_cleaned.loc[missing_timestamp, "reading_timestamp"] = datetime.now(UTC)

    return df_cleaned


def remove_incomplete_rows(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """
    Kritik alanlar eksik olan satırları temizler.
    Kritik alanlar: sensor_id, moisture_percent, soil_temperature_c

    Args:
        df: Temizlenecek DataFrame

    Returns:
        Tuple: (Temizlenmiş DataFrame, Silinmiş satır sayısı)
    """

    df_cleaned = df.copy()
    initial_count = len(df_cleaned)

    # Kritik sütunlar için eksik değerleri kontrol et
    critical_columns = ["sensor_id", "moisture_percent", "soil_temperature_c"]
    df_cleaned = df_cleaned.dropna(subset=critical_columns)

    removed_count = initial_count - len(df_cleaned)

    return df_cleaned, removed_count


def execute_etl_pipeline(raw_df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Eksiksiz ETL ardışık düzenini çalıştırır.

    Args:
        raw_df: Ham DataFrame

    Returns:
        Tuple: (Temizlenmiş DataFrame, İstatistik bilgileri)
    """

    initial_count = len(raw_df)

    print("\n📋 ETL ARDIŞIK DÜZENI BAŞLATILIYOR...")
    print(f"   ├─ Başlangıç satır sayısı: {initial_count}")

    # 1. Nem verileri temizle
    df_cleaned = clean_moisture_data(raw_df)
    print("   ├─ ✓ Nem verileri temizlendi")

    # 2. Sıcaklık verileri temizle
    df_cleaned = clean_temperature_data(df_cleaned)
    print("   ├─ ✓ Sıcaklık verileri temizlendi")

    # 3. Timestamp verileri temizle
    df_cleaned = clean_timestamp_data(df_cleaned)
    print("   ├─ ✓ Timestamp verileri temizlendi")

    # 4. Eksik satırları kaldır
    df_cleaned, removed_count = remove_incomplete_rows(df_cleaned)
    print(f"   └─ ✓ Eksik satırlar kaldırıldı ({removed_count} satır)")

    final_count = len(df_cleaned)

    # İstatistikler
    stats = {
        "initial_count": initial_count,
        "final_count": final_count,
        "removed_count": removed_count,
        "retention_rate": (final_count / initial_count * 100) if initial_count > 0 else 0,
    }

    return df_cleaned, stats


# =============================================
# VERİTABANI İŞLEMLERİ (Database Operations)
# =============================================


def ensure_database_exists() -> bool:
    """
    Veritabanı dosyasının ve gerekli tabloların var olduğunu kontrol eder.
    Gerekirse tabloları oluşturur.

    Returns:
        bool: Başarılı ise True
    """

    try:
        # Veritabanı motor oluştur
        engine = create_engine(DATABASE_URL, echo=False)

        # Veritabanına bağlan ve tabloları oluştur
        with engine.connect() as connection:
            # sfdap_schema.sql dosyasından şemayı yükle
            schema_path = PROJECT_ROOT / "database" / "sfdap_schema.sql"

            if schema_path.exists():
                with open(schema_path, encoding="utf-8") as f:
                    schema_sql = f.read()

                # Şemayı çalıştır
                statements = schema_sql.split(";")
                for statement in statements:
                    statement = statement.strip()
                    if statement:  # Boş ifadeleri atla
                        connection.execute(text(statement))

                connection.commit()
                print("✓ Veritabanı şeması başarıyla yüklendi")

        return True

    except SQLAlchemyError as e:
        print(f"⚠ Veritabanı hatası: {e}")
        return False
    except Exception as e:
        print(f"⚠ Beklenmeyen hata: {e}")
        return False


def save_data_to_database(df: pd.DataFrame) -> tuple[int, int]:
    """
    Temizlenmiş veriyi soil_moisture_readings tablosuna kaydeder.

    Args:
        df: Kaydedilecek DataFrame

    Returns:
        Tuple: (Başarıyla kaydedilen satırlar, Hatalı satırlar)
    """

    try:
        engine = create_engine(DATABASE_URL, echo=False)

        # Veriyi append moduyla kaydet
        df.to_sql("soil_moisture_readings", con=engine, if_exists="append", index=False, method="multi")

        successful_count = len(df)
        failed_count = 0

        return successful_count, failed_count

    except SQLAlchemyError as e:
        print(f"⚠ Veritabanı iş hatası: {e}")
        # Kısmi başarı durumunda satır satır kaydetmeyi dene
        return insert_data_row_by_row(df, engine)
    except Exception as e:
        print(f"⚠ Veri kayıt hatası: {e}")
        return 0, len(df)


def insert_data_row_by_row(df: pd.DataFrame, engine) -> tuple[int, int]:
    """
    Veriyi satır satır kaydeder (hata toleransı kullanarak).

    Args:
        df: Kaydedilecek DataFrame
        engine: SQLAlchemy motor

    Returns:
        Tuple: (Başarıyla kaydedilen satırlar, Hatalı satırlar)
    """

    successful_count = 0
    failed_count = 0

    try:
        for idx, row in df.iterrows():
            try:
                row_df = pd.DataFrame([row])
                row_df.to_sql("soil_moisture_readings", con=engine, if_exists="append", index=False)
                successful_count += 1
            except Exception as row_error:
                print(f"   ⚠ Satır {idx} kaydedilemedi: {row_error}")
                failed_count += 1

    except Exception as e:
        print(f"⚠ Satır satır kayıt hatası: {e}")

    return successful_count, failed_count


# =============================================
# REPORTING — RAPORLAMA
# =============================================


def print_data_summary(raw_df: pd.DataFrame, cleaned_df: pd.DataFrame, stats: dict):
    """
    Veri temizleme işleminin detaylı özetini yazdırır.

    Args:
        raw_df: Ham DataFrame
        cleaned_df: Temizlenmiş DataFrame
        stats: ETL istatistikleri
    """

    print("\n" + "=" * 60)
    print("📊 VERİ TEMİZLEME RAPORu")
    print("=" * 60)

    print("\n📥 HAM VERİ İSTATİSTİKLERİ:")
    print(f"   ├─ Toplam satır: {stats['initial_count']}")
    print(f"   ├─ Eksik nem değerleri: {raw_df['moisture_percent'].isna().sum()}")
    print(f"   ├─ Eksik sıcaklık değerleri: {raw_df['soil_temperature_c'].isna().sum()}")
    print(f"   └─ Eksik timestamp değerleri: {raw_df['reading_timestamp'].isna().sum()}")

    print("\n📤 TEMİZLENMİŞ VERİ İSTATİSTİKLERİ:")
    print(f"   ├─ Başarıyla temizlenen satırlar: {stats['final_count']}")
    print(f"   ├─ Hatalı/eksik olması nedeniyle silinen: {stats['removed_count']}")
    print(f"   ├─ Tutma oranı: %{stats['retention_rate']:.1f}")
    print("   └─ Eksik veri yok: ✓")

    if len(cleaned_df) > 0:
        print("\n📈 TEMİZLENMİŞ VERİ ÖZET İSTATİSTİKLERİ:")
        print(f"   ├─ Nem (%), ortalama: {cleaned_df['moisture_percent'].mean():.2f}")
        print(
            f"   ├─ Nem (%), min-max: {cleaned_df['moisture_percent'].min():.2f} - {cleaned_df['moisture_percent'].max():.2f}"
        )
        print(f"   ├─ Sıcaklık (°C), ortalama: {cleaned_df['soil_temperature_c'].mean():.2f}")
        print(
            f"   ├─ Sıcaklık (°C), min-max: {cleaned_df['soil_temperature_c'].min():.2f} - {cleaned_df['soil_temperature_c'].max():.2f}"
        )
        print(f"   └─ Sensör çeşitliliği: {cleaned_df['sensor_id'].nunique()} sensör")


def print_database_results(successful_count: int, failed_count: int):
    """
    Veritabanı kayıt işleminin sonuçlarını yazdırır.

    Args:
        successful_count: Başarıyla kaydedilen satır sayısı
        failed_count: Kaydedilememiş satır sayısı
    """

    total = successful_count + failed_count

    print("\n" + "=" * 60)
    print("💾 VERİTABANI KAYIT RAPORu")
    print("=" * 60)

    print("\n✅ BAŞARILI İŞLEMLER:")
    print(f"   └─ Kayıtlı satır sayısı: {successful_count}")

    if failed_count > 0:
        print("\n❌ BAŞARISIZ İŞLEMLER:")
        print(f"   └─ Kaydedilememiş satır sayısı: {failed_count}")

    print("\n📊 ÖZETLEMESİ:")
    print(f"   ├─ Toplam satır: {total}")
    print(f"   ├─ Başarı oranı: %{(successful_count / total * 100) if total > 0 else 0:.1f}")
    print(f"   └─ Veritabanı güncellemesi: {'✓ Tamamlandı' if successful_count > 0 else '✗ Başarısız'}")

    print("\n" + "=" * 60 + "\n")


# =============================================
# ANA PROGRAM
# =============================================


def main():
    """
    Ana program akışı: veri üretimi → temizleme → kayıt → rapor
    """

    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║  SFDAP - SENSÖR VERİ ENTEGRASYON PROGRAMI              ║")
    print("║  Toprak Nem Sensörleri Veri Temizleme & Kayıt          ║")
    print("╚══════════════════════════════════════════════════════════╝")

    try:
        # 1. Veritabanı hazırlığı
        print("\n🔧 Veritabanı ayarlanıyor...")
        if not ensure_database_exists():
            print("✗ Veritabanı hazırlığı başarısız!")
            return
        print("✓ Veritabanı hazır")

        # 2. Ham veri üretimi
        print("\n📝 Ham sensör verileri üretiliyor...")
        raw_data = generate_sample_raw_data(num_records=20)
        print(f"✓ {len(raw_data)} satırlık ham veri oluşturuldu")

        # 3. ETL ardışık düzeni çalıştır
        cleaned_data, etl_stats = execute_etl_pipeline(raw_data)

        # 4. Veri raporlaması
        print_data_summary(raw_data, cleaned_data, etl_stats)

        # 5. Veritabanına kaydet
        print("\n💾 Temizlenmiş veriler veritabanına kaydediliyor...")
        successful, failed = save_data_to_database(cleaned_data)

        # 6. Sonuç raporlaması
        print_database_results(successful, failed)

        print("✅ İŞLEM BAŞARIYLA TAMAMLANDI!\n")

    except KeyboardInterrupt:
        print("\n\n⚠ Program kullanıcı tarafından durduruldu.")
    except Exception as e:
        print(f"\n❌ KRITIK HATA: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
