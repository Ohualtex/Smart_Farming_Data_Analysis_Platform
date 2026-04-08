# =============================================
# SFDAP - Sensör Veri Doğrulama & İstatistik
# =============================================
# Amaç: Veritabanında kayıtlı sensör verilerini
#       kontrol etme ve istatistik hesaplama
# =============================================

import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime

# Veritabanı yolu
DATABASE_PATH = Path(__file__).parent.parent / "database" / "sfdap.db"


def print_separator(title: str = "", width: int = 60):
    """Dekoratif ayırıcı çizgi yazdırır."""
    if title:
        print("=" * width)
        print(title.center(width))
        print("=" * width)
    else:
        print("=" * width)


def get_database_stats():
    """Veritabanından toprak nem verilerini çeker ve istatistik hesaplar."""
    
    try:
        # Veritabanına bağlan
        conn = sqlite3.connect(str(DATABASE_PATH))
        
        # SQL sorgusu
        query = "SELECT * FROM soil_moisture_readings ORDER BY reading_timestamp DESC"
        
        # Veriyi DataFrame'e yükle
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if len(df) == 0:
            print("\n⚠ Veritabanında veri bulunamadı!")
            return None
        
        return df
        
    except Exception as e:
        print(f"\n❌ Sorgu hatası: {e}")
        return None


def display_raw_data(df: pd.DataFrame, limit: int = 10):
    """SQlite'den çekilen ham verileri tabular formatta gösterir."""
    
    print_separator("📋 VERITABANINDAKI HAM VERİLER")
    
    # Sütun seçimi (görüntüye uygun)
    display_cols = ['id', 'sensor_id', 'reading_timestamp', 'moisture_percent', 
                    'soil_temperature_c', 'depth_cm']
    
    available_cols = [col for col in display_cols if col in df.columns]
    
    print(f"\nToplam {len(df)} kayıt | İlk {min(limit, len(df))} gösteriliyor:\n")
    
    # DataFrame'i formatla ve yazdır
    display_df = df[available_cols].head(limit).reset_index(drop=True)
    print(display_df.to_string(index=True))


def calculate_statistics(df: pd.DataFrame):
    """Nem ve sıcaklık verilerinin istatistiklerini hesaplar."""
    
    print_separator("📊 VERİ İSTATİSTİKLERİ")
    
    print("\n🌍 NEM (%) STATİSTİKLERİ:")
    print(f"   ├─ Sayı: {df['moisture_percent'].count()} kayıt")
    print(f"   ├─ Ortalama: {df['moisture_percent'].mean():.2f}%")
    print(f"   ├─ Medyan: {df['moisture_percent'].median():.2f}%")
    print(f"   ├─ Std. Sapma: {df['moisture_percent'].std():.2f}%")
    print(f"   ├─ Minimum: {df['moisture_percent'].min():.2f}%")
    print(f"   ├─ 25. Yüzdelik: {df['moisture_percent'].quantile(0.25):.2f}%")
    print(f"   ├─ 75. Yüzdelik: {df['moisture_percent'].quantile(0.75):.2f}%")
    print(f"   └─ Maksimum: {df['moisture_percent'].max():.2f}%")
    
    print(f"\n🌡 SICAKLIK (°C) STATİSTİKLERİ:")
    print(f"   ├─ Sayı: {df['soil_temperature_c'].count()} kayıt")
    print(f"   ├─ Ortalama: {df['soil_temperature_c'].mean():.2f}°C")
    print(f"   ├─ Medyan: {df['soil_temperature_c'].median():.2f}°C")
    print(f"   ├─ Std. Sapma: {df['soil_temperature_c'].std():.2f}°C")
    print(f"   ├─ Minimum: {df['soil_temperature_c'].min():.2f}°C")
    print(f"   ├─ 25. Yüzdelik: {df['soil_temperature_c'].quantile(0.25):.2f}°C")
    print(f"   ├─ 75. Yüzdelik: {df['soil_temperature_c'].quantile(0.75):.2f}°C")
    print(f"   └─ Maksimum: {df['soil_temperature_c'].max():.2f}°C")
    
    if 'depth_cm' in df.columns:
        print(f"\n📏 DEERİNLİK (cm) DAĞILIMı:")
        depth_dist = df['depth_cm'].value_counts().sort_index()
        for depth, count in depth_dist.items():
            print(f"   ├─ {depth}cm: {count} sensör")
    
    if 'sensor_id' in df.columns:
        print(f"\n📡 SENSÖR DAĞILIMı:")
        sensor_dist = df['sensor_id'].value_counts().sort_index()
        for sensor_id, count in sensor_dist.items():
            print(f"   ├─ Sensör {int(sensor_id)}: {count} ölçüm")


def check_data_quality(df: pd.DataFrame):
    """Veri kalitesini kontrol eder (aralık doğrulaması)."""
    
    print_separator("✅ VERİ KALİTESİ KONTROL")
    
    # Nem aralığı kontrolü (0-100%)
    invalid_moisture = df[(df['moisture_percent'] < 0) | (df['moisture_percent'] > 100)]
    print(f"\n💧 Nem Aralığı Kontrolü (0-100%):")
    print(f"   ├─ Geçerli: {len(df) - len(invalid_moisture)}")
    print(f"   ├─ Hatalı: {len(invalid_moisture)}")
    
    if len(invalid_moisture) > 0:
        print(f"   └─ ⚠ UYARI: Aralık dışı nem değerleri tespit edildi!")
        print(f"      Hatalı değerler: {invalid_moisture['moisture_percent'].tolist()}")
    else:
        print(f"   └─ ✓ TÜM nem değerleri geçerli aralıkta")
    
    # Sıcaklık aralığı kontrolü (-10 ~ 60°C)
    TEMP_MIN, TEMP_MAX = -10, 60
    invalid_temp = df[(df['soil_temperature_c'] < TEMP_MIN) | 
                       (df['soil_temperature_c'] > TEMP_MAX)]
    print(f"\n🌡 Sıcaklık Aralığı Kontrolü ({TEMP_MIN}-{TEMP_MAX}°C):")
    print(f"   ├─ Geçerli: {len(df) - len(invalid_temp)}")
    print(f"   ├─ Hatalı: {len(invalid_temp)}")
    
    if len(invalid_temp) > 0:
        print(f"   └─ ⚠ UYARI: Aralık dışı sıcaklık değerleri tespit edildi!")
        print(f"      Hatalı değerler: {invalid_temp['soil_temperature_c'].tolist()}")
    else:
        print(f"   └─ ✓ TÜM sıcaklık değerleri geçerli aralıkta")
    
    # Eksik veri kontrolü
    print(f"\n📦 Eksik Veri Kontrolü:")
    null_counts = df.isnull().sum()
    has_nulls = null_counts.sum() > 0
    
    for col in df.columns:
        if null_counts[col] > 0:
            print(f"   ├─ {col}: {null_counts[col]} eksik")
    
    if not has_nulls:
        print(f"   └─ ✓ Eksik veri yok - Veri bütünlüğü mükemmel!")
    
    # Genel kalite puanı
    total_cells = len(df) * len(df.columns)
    valid_cells = total_cells - null_counts.sum()
    quality_score = (valid_cells / total_cells * 100) if total_cells > 0 else 0
    
    print(f"\n📈 Genel Veri Kalitesi Puanı:")
    print(f"   ├─ Geçerli hücreler: {valid_cells}/{total_cells}")
    print(f"   ├─ Kalite puanı: {quality_score:.1f}%")
    
    if quality_score >= 95:
        print(f"   └─ ⭐ MÜKEMMELKalite")
    elif quality_score >= 80:
        print(f"   └─ ⭐⭐ İYİ Kalite")
    elif quality_score >= 60:
        print(f"   └─ ⭐⭐⭐ ORTA Kalite")
    else:
        print(f"   └─ ⭐⭐⭐⭐ DÜŞÜK Kalite - Uyarı!")


def generate_summary_report(df: pd.DataFrame):
    """Özet rapor oluşturur."""
    
    print_separator("📄 ÖZET RAPOR")
    
    print(f"\n📅 Rapor Tarihi: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"💾 Veritabanı: {DATABASE_PATH}")
    
    print(f"\n📊 Veri Özeti:")
    print(f"   ├─ Toplam Kayıt: {len(df)}")
    print(f"   ├─ İlk Kayıt: {df['reading_timestamp'].iloc[-1]}")
    print(f"   ├─ Son Kayıt: {df['reading_timestamp'].iloc[0]}")
    
    if 'sensor_id' in df.columns:
        unique_sensors = df['sensor_id'].nunique()
        print(f"   ├─ Sensör Sayısı: {int(unique_sensors)}")
    
    if 'depth_cm' in df.columns:
        unique_depths = df['depth_cm'].nunique()
        print(f"   └─ Ölçüm Derinlik Türü: {int(unique_depths)}")


def main():
    """Ana program - tüm kontrolleri çalıştırır."""
    
    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║  SFDAP - SENSÖR VERİ DOĞRULAMA & İSTATİSTİK             ║")
    print("║  Veritabanı İçeriği Analiz Aracı                        ║")
    print("╚══════════════════════════════════════════════════════════╝")
    
    # Veritabanından veri çek
    print(f"\n🔍 Veritabanından veri çekiliyor: {DATABASE_PATH}")
    df = get_database_stats()
    
    if df is None or len(df) == 0:
        print("\n❌ İşlem başarısız oldu!")
        return
    
    print(f"✓ {len(df)} kayıt başarıyla yüklendi")
    
    # Kontrolleri çalıştır
    display_raw_data(df, limit=10)
    print()
    
    calculate_statistics(df)
    print()
    
    check_data_quality(df)
    print()
    
    generate_summary_report(df)
    
    print("\n" + "=" * 60)
    print("✅ VERİ DOĞRULAMA TAMAMLANDI!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
