## 1. Sistemin Amacı
Akıllı Tarım platformumuzda sensörlerden gelen veri akışını anlık olarak takip etmek ve bir kopukluk yaşandığında sistemi korumaya almaktır.

## 2. İzleme Parametreleri
- **Zaman Aşımı (Timeout):** Sensörden 10 saniye boyunca veri gelmezse sistem uyarı verir.
- **Hatalı Veri:** Sensörde gelen "0" veya negatif değerler "Hatalı Veri" olarak işaretlenir. 

## 3. Uyarı Mekanizması
Hata tespit edildiğinde sistem şu adımları izler:
1. Hata log dosyasına kaydedilir.
2. Dashboard üzerinde kullanıcıya kırmızı renkli görsel bir uyarı gösterlir.
3. Veri akışı tekrar düzelene kadar sistem "Bekleme" moduna alır.