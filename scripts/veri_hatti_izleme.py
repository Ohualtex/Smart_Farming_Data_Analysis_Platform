def veri_hatti_kontrol(nem_degeri):
    print("--- Akıllı Tarım Veri Hattı Kontrolü ---")
    if nem_degeri is None or nem_degeri <= 0:
        print("HATA: Sensör verisi alınamıyor!")
    else:
        print(f"Sistem stabil. Nem: %{nem_degeri}")

