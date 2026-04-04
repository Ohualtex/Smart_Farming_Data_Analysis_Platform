# ============================================================
# SFDAP - Akıllı Tarım Veri Analizi Platformu
# Görev  : Hava Durumu Verisi Temizleme ve Dönüştürme
#
# Açıklama:
#   OpenWeatherMap API'den alınan ham hava durumu verileri;
#   temizlenir, eksik/hatalı değerler düzeltilir,
#   platformun veri modeline uygun hale getirilir ve
#   SQLite veritabanına (sfdap_dev.db) kaydedilir.
# ============================================================

import requests
import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

try:
    from sqlalchemy import create_engine
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    print("[UYARI] sqlalchemy yüklü değil. Veri sadece CSV olarak kaydedilecek.")

# ============================================================
# 1. YAPILANDIRMA
# ============================================================

# .env dosyasındaki OPENWEATHERMAP_API_KEY değerini okur
API_KEY      = os.environ.get("OPENWEATHERMAP_API_KEY", "buraya_api_anahtarinizi_yazin")
CITY         = "Konya"
UNITS        = "metric"
OUTPUT_CSV   = "hava_durumu_temiz.csv"
DATABASE_URL = "sqlite:///../../sfdap_dev.db"  # mevcut proje veritabanı

VALID_RANGES = {
    "sicaklik":    (-50, 60),
    "nem":         (0, 100),
    "ruzgar_hizi": (0, 200),
    "basinc":      (800, 1100),
    "yagis":       (0, 500),
}

# ============================================================
# 2. API'DEN VERİ ÇEKME
# ============================================================

def veri_cek(api_key, city, units="metric"):
    """OpenWeatherMap 5 günlük tahmin verisini çeker (~40 kayıt)."""
    url    = "https://api.openweathermap.org/data/2.5/forecast"
    params = {"q": city, "appid": api_key, "units": units, "lang": "tr"}
    print(f"\n[BİLGİ] '{city}' için veri çekiliyor...")
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        print(f"[BAŞARILI] {len(data['list'])} veri noktası alındı.")
        return data
    except requests.exceptions.ConnectionError:
        print("[HATA] İnternet bağlantısı yok.")
        return None
    except requests.exceptions.HTTPError as e:
        print(f"[HATA] API hatası: {e}")
        return None

# ============================================================
# 3. JSON → DATAFRAME
# ============================================================

def json_to_dataframe(data):
    """Ham API verisini proje veri modeline uygun DataFrame'e çevirir."""
    kayitlar = []
    for item in data["list"]:
        kayitlar.append({
            "tarih_saat":   item["dt_txt"],
            "sicaklik":     item["main"].get("temp"),
            "hissedilen":   item["main"].get("feels_like"),
            "min_sicaklik": item["main"].get("temp_min"),
            "max_sicaklik": item["main"].get("temp_max"),
            "nem":          item["main"].get("humidity"),
            "basinc":       item["main"].get("pressure"),
            "bulutluluk":   item["clouds"].get("all"),
            "ruzgar_hizi":  item["wind"].get("speed"),
            "ruzgar_yon":   item["wind"].get("deg"),
            "yagis":        item.get("rain", {}).get("3h", 0.0),
            "hava_durumu":  item["weather"][0].get("description") if item.get("weather") else None,
            "hava_kodu":    item["weather"][0].get("id") if item.get("weather") else None,
            "sehir":        data.get("city", {}).get("name", CITY),
        })
    df = pd.DataFrame(kayitlar)
    print(f"[BİLGİ] DataFrame oluşturuldu: {df.shape[0]} satır, {df.shape[1]} sütun")
    return df

# ============================================================
# 4. ÖRNEK VERİ (API yoksa)
# ============================================================

def ornek_veri_olustur():
    """API erişimi yoksa gerçekçi test verisi üretir (hatalı değerler dahil)."""
    print("[BİLGİ] Örnek test verisi oluşturuluyor...")
    np.random.seed(42)
    n = 40
    tarihler = pd.date_range(start="2026-03-25 00:00:00", periods=n, freq="3h")
    df = pd.DataFrame({
        "tarih_saat":   tarihler.strftime("%Y-%m-%d %H:%M:%S"),
        "sicaklik":     np.random.uniform(8, 22, n).round(1),
        "hissedilen":   np.random.uniform(5, 20, n).round(1),
        "min_sicaklik": np.random.uniform(5, 15, n).round(1),
        "max_sicaklik": np.random.uniform(15, 25, n).round(1),
        "nem":          np.random.uniform(40, 85, n).round(0),
        "basinc":       np.random.uniform(1005, 1020, n).round(0),
        "bulutluluk":   np.random.uniform(0, 100, n).round(0),
        "ruzgar_hizi":  np.random.uniform(0, 10, n).round(1),
        "ruzgar_yon":   np.random.uniform(0, 360, n).round(0),
        "yagis":        np.random.choice([0, 0, 0, 1.2, 3.5, 0.8], n),
        "hava_durumu":  np.random.choice(["açık", "parçalı bulutlu", "yağmurlu", "bulutlu"], n),
        "hava_kodu":    np.random.choice([800, 801, 500, 804], n),
        "sehir":        "Konya",
    })
    # Gerçek hayatı simüle eden hatalar
    df.loc[3,  "sicaklik"]    = np.nan
    df.loc[7,  "nem"]         = np.nan
    df.loc[12, "ruzgar_hizi"] = np.nan
    df.loc[15, "sicaklik"]    = 999     # hatalı kalibrasyon
    df.loc[20, "nem"]         = -5      # mantık dışı
    df.loc[25, "basinc"]      = 0       # sensör arızası
    df.loc[30, "yagis"]       = np.nan
    print(f"[BİLGİ] {n} satır örnek veri oluşturuldu (7 hatalı/eksik değer içeriyor).")
    return df

# ============================================================
# 5. EKSİK VERİ RAPORU
# ============================================================

def eksik_veri_raporu(df):
    print("\n" + "="*55)
    print("  EKSİK VERİ RAPORU (Temizleme Öncesi)")
    print("="*55)
    eksik  = df.isnull().sum()
    yuzde  = (eksik / len(df) * 100).round(2)
    rapor  = pd.DataFrame({"Eksik Adet": eksik, "Oran (%)": yuzde})
    rapor  = rapor[rapor["Eksik Adet"] > 0]
    print("  Eksik veri yok." if rapor.empty else rapor.to_string())
    print("="*55 + "\n")

# ============================================================
# 6. AYKIRI DEĞER TEMİZLEME
# ============================================================

def aykiri_degerleri_temizle(df):
    """Geçerli aralık dışındaki değerleri NaN yapar (domain knowledge)."""
    print("[BİLGİ] Aykırı değerler kontrol ediliyor...")
    toplam = 0
    eslesme = {
        "sicaklik": VALID_RANGES["sicaklik"],
        "nem":      VALID_RANGES["nem"],
        "ruzgar_hizi": VALID_RANGES["ruzgar_hizi"],
        "basinc":   VALID_RANGES["basinc"],
        "yagis":    VALID_RANGES["yagis"],
    }
    for sutun, (alt, ust) in eslesme.items():
        if sutun not in df.columns:
            continue
        df[sutun] = pd.to_numeric(df[sutun], errors="coerce")
        mask = (df[sutun] < alt) | (df[sutun] > ust)
        adet = mask.sum()
        if adet > 0:
            print(f"  [UYARI] '{sutun}': {adet} aykırı değer → NaN (geçerli: {alt}–{ust})")
            df.loc[mask, sutun] = np.nan
            toplam += adet
    print(f"[BİLGİ] Toplam {toplam} aykırı değer temizlendi.\n")
    return df

# ============================================================
# 7. EKSİK VERİ DOLDURMA
# ============================================================

def eksik_verileri_doldur(df):
    """
    Proje dokümanındaki strateji:
    - Sayısal: doğrusal interpolasyon → ffill → bfill
    - Kategorik: mod değeri
    - Yağış: NaN → 0
    """
    print("[BİLGİ] Eksik veriler dolduruluyor...")
    sayisal = ["sicaklik", "hissedilen", "min_sicaklik", "max_sicaklik",
               "nem", "basinc", "bulutluluk", "ruzgar_hizi", "ruzgar_yon"]
    for sutun in sayisal:
        if sutun in df.columns and df[sutun].isnull().any():
            df[sutun] = pd.to_numeric(df[sutun], errors="coerce")
            df[sutun] = df[sutun].interpolate(method="linear", limit_direction="both")
            df[sutun] = df[sutun].ffill().bfill()
            print(f"  [OK] '{sutun}' → interpolasyon + ffill/bfill")
    if "hava_durumu" in df.columns and df["hava_durumu"].isnull().any():
        mod = df["hava_durumu"].mode()[0]
        df["hava_durumu"] = df["hava_durumu"].fillna(mod)
        print(f"  [OK] 'hava_durumu' → mod: '{mod}'")
    if "yagis" in df.columns:
        df["yagis"] = df["yagis"].fillna(0.0)
    print("[BİLGİ] Doldurma tamamlandı.\n")
    return df

# ============================================================
# 8. VERİ DÖNÜŞÜMÜ
# ============================================================

def veri_donustur(df):
    """
    - tarih_saat → datetime
    - Rüzgar: m/s → km/h
    - Feature Engineering: saat, gün, ay, mevsim
    - Don riski bayrağı
    """
    print("[BİLGİ] Veri dönüşümü uygulanıyor...")
    df["tarih_saat"] = pd.to_datetime(df["tarih_saat"])

    if "ruzgar_hizi" in df.columns:
        df["ruzgar_hizi_kmh"] = (df["ruzgar_hizi"] * 3.6).round(1)

    df["saat"]       = df["tarih_saat"].dt.hour
    df["gun"]        = df["tarih_saat"].dt.day
    df["ay"]         = df["tarih_saat"].dt.month
    df["hafta_gunu"] = df["tarih_saat"].dt.day_name()

    def mevsim(ay):
        if ay in [12, 1, 2]:  return "Kış"
        if ay in [3, 4, 5]:   return "İlkbahar"
        if ay in [6, 7, 8]:   return "Yaz"
        return "Sonbahar"

    df["mevsim"]    = df["ay"].apply(mevsim)
    df["don_riski"] = df["sicaklik"] <= 2   # Tarımsal karar desteği

    for s in ["sicaklik", "hissedilen", "min_sicaklik", "max_sicaklik", "ruzgar_hizi", "yagis"]:
        if s in df.columns:
            df[s] = df[s].round(1)
    for s in ["nem", "basinc", "bulutluluk", "ruzgar_yon"]:
        if s in df.columns:
            df[s] = pd.to_numeric(df[s], errors="coerce").round(0)

    df["islem_zamani"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("[BİLGİ] Dönüşüm tamamlandı.\n")
    return df

# ============================================================
# 9. VERİTABANINA KAYDETME
# ============================================================

def veritabanina_kaydet(df, db_url):
    """
    Mevcut SFDAP veritabanına (sfdap_dev.db) kaydeder.
    Tablo: weather_processed
    """
    if not SQLALCHEMY_AVAILABLE:
        return False
    try:
        df_db = df.copy()
        df_db["tarih_saat"]   = df_db["tarih_saat"].astype(str)
        df_db["islem_zamani"] = df_db["islem_zamani"].astype(str)
        engine = create_engine(db_url, echo=False)
        df_db.to_sql("weather_processed", con=engine, if_exists="append", index=False)
        print(f"[BAŞARILI] {len(df_db)} kayıt veritabanına eklendi → tablo: 'weather_processed'")
        return True
    except Exception as e:
        print(f"[HATA] Veritabanına kayıt başarısız: {e}")
        return False

def csv_kaydet(df, dosya_adi):
    df_csv = df.copy()
    df_csv["tarih_saat"] = df_csv["tarih_saat"].astype(str)
    df_csv.to_csv(dosya_adi, index=False, encoding="utf-8-sig")
    print(f"[BAŞARILI] CSV kaydedildi → '{dosya_adi}'")

# ============================================================
# 10. ANA PROGRAM
# ============================================================

def main():
    print("\n" + "="*55)
    print("  SFDAP — Hava Durumu Veri İşleme Pipeline'ı")
    print("="*55)

    # Adım 1: Veri çek
    if API_KEY == "buraya_api_anahtarinizi_yazin":
        print("\n[BİLGİ] API anahtarı yok → örnek veri kullanılıyor.")
        df = ornek_veri_olustur()
    else:
        data = veri_cek(API_KEY, CITY, UNITS)
        df   = json_to_dataframe(data) if data else ornek_veri_olustur()

    # Adım 2: Rapor (öncesi)
    eksik_veri_raporu(df)

    # Adım 3: Aykırı değerleri temizle
    df = aykiri_degerleri_temizle(df)

    # Adım 4: Eksik verileri doldur
    df = eksik_verileri_doldur(df)

    # Adım 5: Dönüştür
    df = veri_donustur(df)

    # Adım 6: Kaydet
    if not veritabanina_kaydet(df, DATABASE_URL):
        csv_kaydet(df, OUTPUT_CSV)

    # Adım 7: Özet
    print("\n" + "="*55)
    print("  İŞLEM TAMAMLANDI")
    print("="*55)
    print(f"  Toplam kayıt  : {len(df)}")
    print(f"  Sütun sayısı  : {len(df.columns)}")
    print(f"  Don riski     : {df['don_riski'].sum()} zaman dilimi")
    print(f"  Şehir         : {df['sehir'].iloc[0]}")
    print("="*55)
    print("\nTemizlenmiş verinin ilk 3 satırı:")
    print(df[["tarih_saat", "sicaklik", "nem",
              "ruzgar_hizi_kmh", "yagis", "don_riski", "mevsim"]].head(3).to_string(index=False))

if __name__ == "__main__":
    main()