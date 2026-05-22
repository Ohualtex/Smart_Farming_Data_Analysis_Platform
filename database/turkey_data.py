"""
Türkiye İl Koordinat + Bitki/Toprak Referans Verileri
======================================================
Demo seed (`seed_data.py`) ve çiftlik haritası için referans/lookup tablosu —
"ulusal ölçek" iddiası değil, koordinat ve tarımsal sabitler kütüphanesi.

İçerik:
- PROVINCES: il → (enlem, boylam, bölge, taban sıcaklık/nem) koordinat lookup'ı
- REGION_CROPS: bölge → uygun bitki indeksleri
- CROP_DATA: 17 bitki türü (pH, sıcaklık, su, gün) — fertilizer_service ile uyumlu
- SOIL_TYPES: toprak tipi isimleri
"""

# fmt: off
PROVINCES = [
    ("Adana", 37.00, 35.33, "Akdeniz", 24, 65), ("Adıyaman", 37.76, 38.28, "Güneydoğu Anadolu", 22, 35),
    ("Afyonkarahisar", 38.73, 30.54, "Ege", 14, 50), ("Ağrı", 39.72, 43.05, "Doğu Anadolu", 8, 45),
    ("Amasya", 40.65, 35.83, "Karadeniz", 16, 70), ("Ankara", 39.93, 32.86, "İç Anadolu", 15, 40),
    ("Antalya", 36.88, 30.71, "Akdeniz", 25, 60), ("Artvin", 41.18, 41.82, "Karadeniz", 14, 75),
    ("Aydın", 37.85, 27.85, "Ege", 22, 55), ("Balıkesir", 39.65, 27.88, "Marmara", 18, 60),
    ("Bilecik", 40.05, 30.00, "Marmara", 15, 55), ("Bingöl", 38.88, 40.50, "Doğu Anadolu", 10, 45),
    ("Bitlis", 38.40, 42.11, "Doğu Anadolu", 9, 50), ("Bolu", 40.73, 31.61, "Karadeniz", 13, 70),
    ("Burdur", 37.72, 30.29, "Akdeniz", 17, 50), ("Bursa", 40.19, 29.06, "Marmara", 18, 65),
    ("Çanakkale", 40.15, 26.41, "Marmara", 18, 60), ("Çankırı", 40.60, 33.62, "İç Anadolu", 13, 40),
    ("Çorum", 40.55, 34.95, "Karadeniz", 14, 55), ("Denizli", 37.77, 29.09, "Ege", 20, 50),
    ("Diyarbakır", 37.92, 40.23, "Güneydoğu Anadolu", 23, 35), ("Edirne", 41.68, 26.56, "Marmara", 17, 60),
    ("Elazığ", 38.67, 39.22, "Doğu Anadolu", 16, 45), ("Erzincan", 39.75, 39.49, "Doğu Anadolu", 12, 50),
    ("Erzurum", 39.91, 41.28, "Doğu Anadolu", 6, 55), ("Eskişehir", 39.77, 30.52, "İç Anadolu", 14, 45),
    ("Gaziantep", 37.07, 37.38, "Güneydoğu Anadolu", 22, 40), ("Giresun", 40.91, 38.39, "Karadeniz", 16, 80),
    ("Gümüşhane", 40.46, 39.48, "Karadeniz", 12, 60), ("Hakkari", 37.57, 43.74, "Doğu Anadolu", 10, 45),
    ("Hatay", 36.40, 36.35, "Akdeniz", 24, 65), ("Isparta", 37.76, 30.56, "Akdeniz", 16, 50),
    ("Mersin", 36.80, 34.63, "Akdeniz", 24, 65), ("İstanbul", 41.01, 28.98, "Marmara", 17, 70),
    ("İzmir", 38.42, 27.14, "Ege", 22, 55), ("Kars", 40.60, 43.10, "Doğu Anadolu", 5, 55),
    ("Kastamonu", 41.38, 33.78, "Karadeniz", 13, 65), ("Kayseri", 38.73, 35.48, "İç Anadolu", 13, 40),
    ("Kırklareli", 41.73, 27.23, "Marmara", 16, 60), ("Kırşehir", 39.14, 34.16, "İç Anadolu", 14, 40),
    ("Kocaeli", 40.77, 29.92, "Marmara", 17, 70), ("Konya", 37.87, 32.48, "İç Anadolu", 14, 38),
    ("Kütahya", 39.42, 29.98, "Ege", 14, 50), ("Malatya", 38.35, 38.31, "Doğu Anadolu", 16, 45),
    ("Manisa", 38.61, 27.43, "Ege", 21, 50), ("Kahramanmaraş", 37.59, 36.94, "Akdeniz", 20, 55),
    ("Mardin", 37.31, 40.74, "Güneydoğu Anadolu", 22, 35), ("Muğla", 37.22, 28.36, "Ege", 22, 55),
    ("Muş", 38.75, 41.49, "Doğu Anadolu", 9, 50), ("Nevşehir", 38.63, 34.71, "İç Anadolu", 14, 40),
    ("Niğde", 37.97, 34.69, "İç Anadolu", 14, 40), ("Ordu", 40.98, 37.88, "Karadeniz", 16, 75),
    ("Rize", 41.02, 40.52, "Karadeniz", 15, 80), ("Sakarya", 40.69, 30.40, "Marmara", 17, 70),
    ("Samsun", 41.29, 36.33, "Karadeniz", 16, 75), ("Siirt", 37.93, 41.94, "Güneydoğu Anadolu", 20, 35),
    ("Sinop", 42.03, 35.15, "Karadeniz", 15, 75), ("Sivas", 39.75, 37.02, "İç Anadolu", 11, 45),
    ("Tekirdağ", 41.00, 27.52, "Marmara", 17, 65), ("Tokat", 40.31, 36.55, "Karadeniz", 15, 60),
    ("Trabzon", 41.00, 39.72, "Karadeniz", 16, 80), ("Tunceli", 39.11, 39.55, "Doğu Anadolu", 12, 50),
    ("Şanlıurfa", 37.16, 38.79, "Güneydoğu Anadolu", 24, 30), ("Uşak", 38.67, 29.41, "Ege", 16, 50),
    ("Van", 38.49, 43.38, "Doğu Anadolu", 9, 50), ("Yozgat", 39.82, 34.81, "İç Anadolu", 12, 42),
    ("Zonguldak", 41.45, 31.79, "Karadeniz", 15, 75), ("Aksaray", 38.37, 34.03, "İç Anadolu", 14, 38),
    ("Bayburt", 40.26, 40.23, "Karadeniz", 10, 55), ("Karaman", 37.18, 33.23, "İç Anadolu", 14, 40),
    ("Kırıkkale", 39.85, 33.51, "İç Anadolu", 14, 40), ("Batman", 37.88, 41.13, "Güneydoğu Anadolu", 22, 35),
    ("Şırnak", 37.42, 42.46, "Güneydoğu Anadolu", 20, 35), ("Bartın", 41.64, 32.34, "Karadeniz", 15, 70),
    ("Ardahan", 41.11, 42.70, "Doğu Anadolu", 5, 55), ("Iğdır", 39.92, 44.05, "Doğu Anadolu", 14, 40),
    ("Yalova", 40.65, 29.28, "Marmara", 17, 70), ("Karabük", 41.20, 32.62, "Karadeniz", 14, 65),
    ("Kilis", 36.72, 37.12, "Güneydoğu Anadolu", 22, 40), ("Osmaniye", 37.07, 36.25, "Akdeniz", 22, 55),
    ("Düzce", 40.84, 31.16, "Karadeniz", 15, 70),
]
# fmt: on

# Bölgelere göre uygun bitki indeksleri (CROP_TYPES listesindeki sıra)
REGION_CROPS = {
    "Akdeniz": [0, 2, 3, 13],  # Buğday, Domates, Pamuk, Narenciye
    "Ege": [2, 4, 5, 8],  # Domates, Ayçiçeği, Zeytin, Üzüm
    "Marmara": [0, 4, 9, 10],  # Buğday, Ayçiçeği, Arpa, Patates
    "İç Anadolu": [0, 9, 11, 12],  # Buğday, Arpa, Şeker Pancarı, Elma
    "Karadeniz": [1, 6, 7, 10],  # Mısır, Fındık, Çay, Patates
    "Doğu Anadolu": [0, 9, 10, 11],  # Buğday, Arpa, Patates, Şeker Pancarı
    "Güneydoğu Anadolu": [0, 1, 3, 14],  # Buğday, Mısır, Pamuk, Antep Fıstığı
}

# 17 bitki türü verileri: (isim, bilimsel_ad, ph_min, ph_max, temp_min, temp_max, su_mm, gün)
# fertilizer_service.CROP_NPK_REQUIREMENTS ile birebir uyumlu (aynı 17 bitki).
CROP_DATA = [
    ("Buğday", "Triticum aestivum", 6.0, 7.5, 12, 25, 5.0, 120),
    ("Mısır", "Zea mays", 5.8, 7.0, 18, 33, 7.0, 90),
    ("Domates", "Solanum lycopersicum", 6.0, 6.8, 20, 30, 6.0, 75),
    ("Pamuk", "Gossypium hirsutum", 5.8, 8.0, 20, 35, 6.5, 150),
    ("Ayçiçeği", "Helianthus annuus", 6.0, 7.5, 18, 30, 5.5, 100),
    ("Zeytin", "Olea europaea", 5.5, 8.5, 15, 35, 3.0, 365),
    ("Fındık", "Corylus avellana", 5.5, 7.0, 12, 28, 4.0, 200),
    ("Çay", "Camellia sinensis", 4.5, 6.0, 15, 30, 8.0, 365),
    ("Üzüm", "Vitis vinifera", 5.5, 7.5, 15, 35, 4.0, 180),
    ("Arpa", "Hordeum vulgare", 6.0, 8.0, 10, 25, 4.5, 100),
    ("Patates", "Solanum tuberosum", 5.0, 6.5, 12, 22, 5.0, 90),
    ("Şeker Pancarı", "Beta vulgaris", 6.0, 7.5, 15, 25, 6.0, 160),
    ("Elma", "Malus domestica", 5.5, 7.0, 10, 25, 4.0, 200),
    ("Narenciye", "Citrus spp.", 5.5, 7.5, 18, 35, 5.0, 365),
    ("Antep Fıstığı", "Pistacia vera", 7.0, 8.0, 20, 38, 3.0, 200),
    ("Biber", "Capsicum annuum", 5.5, 7.0, 18, 30, 6.0, 90),
    ("Pirinç", "Oryza sativa", 5.0, 7.0, 20, 35, 12.0, 130),
]

SOIL_TYPES = ["killi-tınlı", "kumlu-tınlı", "tınlı", "kumlu", "killi", "siltli-tınlı"]
