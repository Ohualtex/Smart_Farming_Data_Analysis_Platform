# 📖 API Kullanım ve Test Kılavuzu

Bu döküman, Mehmet Sait Taysi tarafından geliştirilen Akıllı Tarım API'sinin nasıl test edileceğini adım adım açıklar.

## 1. Swagger UI ile İnteraktif Test
FastAPI sayesinde API anahtarı ile test yapmak oldukça kolaydır:
1. Uygulamayı çalıştırdıktan sonra tarayıcıdan `http://127.0.0.1:8000/docs` adresine gidin.
2. Sağ üstteki **"Authorize"** butonuna tıklayın.
3. API Key olarak `akilli_tarim_gizli_anahtar_2026` değerini girin.
4. İstediğiniz endpoint'e tıklayıp **"Try it out"** -> **"Execute"** butonuna basın.

## 2. API Yanıt Örneği (Success 200)
Başarılı bir istek sonucunda aşağıdaki gibi bir JSON çıktısı alınmaktadır:

```json
[
  {
    "sensor_id": "SENS-NORTH",
    "moisture": 44.5,
    "ph": 6.3,
    "nitrogen": 38
  }
]
