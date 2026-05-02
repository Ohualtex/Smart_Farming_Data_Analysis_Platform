# 🧪 Test Stratejisi ve Geliştirici Yönergeleri

Smart Farming Data Analysis Platform (SFDAP), yüksek güvenilirlik hedefiyle %90+ Test Kapsamına (Test Coverage) sahiptir.

Bu belge, repoya yeni kod ekleyecek takım üyelerinin test yazım standartlarını belirler.

## 1. Test Çerçevesi (Framework)
Projede test koşucusu (test runner) olarak **`pytest`** kullanılmaktadır.
- Kurulum için: `pip install -r requirements-dev.txt`
- Koşturmak için: `make test`

## 2. Test Veritabanı ve Fixture'lar
Testler, üretim (production) veya geliştirme (development) veritabanı üzerinde **KOŞMAZ**. Yanlışlıkla verilerin silinmemesi için `tests/conftest.py` dosyasında özel bir mimari kurulmuştur.

- **In-Memory SQLite:** Testler başladığında hafızada geçici bir SQLite veritabanı yaratılır.
- **`client` Fixture'ı:** Test yazarken `client` parametresini fonksiyonunuza eklerseniz, FastAPI'nin test istemcisine ve temiz bir test veritabanına otomatik sahip olursunuz.
- **Otomatik API Anahtarı:** `client` üzerinden atılan her istek, header'ında otomatik olarak `X-API-Key: dev-api-key` bilgisi ile gider. Sizin manuel eklemenize gerek yoktur.

## 3. Örnek Test Yazımı
Yeni bir test yazarken aşağıdaki yapıyı kullanmalısınız:

```python
def test_example_endpoint(client):
    # 1. Hazırlık (Arrange)
    payload = {"isim": "Test Ciftlik", "sehir": "Ankara"}

    # 2. Aksiyon (Act)
    response = client.post("/api/farms/", json=payload)

    # 3. Doğrulama (Assert)
    assert response.status_code == 201
    assert response.json()["sehir"] == "Ankara"
```

## 4. Kalite Kuralları
- Eklenen her yeni API endpoint'inin başarı durumu (HTTP 200/201) ve hata durumu (HTTP 404/422/401) mutlaka test edilmelidir.
- Sisteme kod pushlamadan önce lokalinizde `make test` komutu ile %80 coverage sınırının altına düşmediğinizden emin olun. (Düşerseniz CI pipeline GitHub üzerinde hata verecektir).
