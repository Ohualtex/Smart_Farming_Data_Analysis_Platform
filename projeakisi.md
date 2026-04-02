## Cycle 1 (5 - 12 Mart)
**MİRAÇ DURAN (Scrum Master / Manager) : Proje Temellerinin Oluşturulması**
GitHub reposu oluşturuldu, branch koruma kuralları (main) ayarlandı. Ekibe iş akışı eğitimi verildi. Proje akış dokümanı oluşturuldu.

**MİRAÇ DURAN : Gerekli Teknolojilerin Araştırılması**
Projede kullanılacak uygun veri madenciliği ve makine öğrenimi teknolojilerini (programlama dilleri, kütüphaneler, araçlar) araştırın ve bir rapor hazırlayın.

**EMİRHAN GÜNAY : Proje Analizi ve Kapsam Tanımlama**
Projenin amacını, hedeflerini ve kapsamını detaylı bir şekilde analiz edin. Kullanılacak veri kaynaklarını ve beklenen sonuçları belirleyin.

**AYŞE ESLEM ÇEKİCİ : Gereksinim Toplama ve Belgeleme**
Proje için gerekli olan tüm gereksinimleri (işlevsel, işlevsel olmayan, veri, kullanıcı) toplayın ve detaylı bir şekilde dokümante edin.

**ECENUR ÜNER : Geliştirme Ortamının Kurulumu**
Gerekli tüm yazılımları ve araçları (IDE, veri tabanı, kütüphaneler) kurarak geliştirme ortamını hazır hale getirin. Kurulum adımlarını dokümante edin.

**MEHMET SAİT TAYŞİ : Veri Seti İncelemesi ve Ön İşleme Adımları**
Kullanılacak veri setini inceleyin ve ön işleme adımlarını (eksik veri tamamlama, aykırı değer tespiti, veri dönüşümü) belirleyin.

## Cycle 2 (12 - 21 Mart)

**MİRAÇ DURAN : Web Kazıma Projesi İçin Veri Yapısının ve Saklama Yöntemlerinin Planlanması**
Tamamlanan 'Gerekli Teknolojilerin Araştırılması' görevi sonrasında, belirlenen teknolojiler ışığında, web kazıma projesi için elde edilecek verinin nasıl yapılandırılacağını ve hangi saklama yöntemlerinin (örneğin, veritabanı, CSV, JSON) kullanılacağını belirleyin. Farklı veri yapılandırma ve saklama seçeneklerinin avantaj ve dezavantajlarını değerlendirerek, projenin ihtiyaçlarına en uygun çözümü belirleyin ve bir plan oluşturun.

**EMİRHAN GÜNAY :**
Mevcut görev yok.

**AYŞE ESLEM ÇEKİCİ :**
Mevcut görev yok.

**ECENUR ÜNER : Veri Kaynaklarının Belirlenmesi ve Veri Toplama Planının Oluşturulması**
Hafta 1'de kurulan geliştirme ortamı ile uyumlu olarak, proje kapsamındaki veri kaynaklarını (web siteleri, API'ler vb.) detaylı bir şekilde belirleyin. Her bir veri kaynağı için veri toplama sıklığı, yöntemi (örn. scraping, API sorguları), veri formatı ve beklenen veri hacmi gibi parametreleri içeren bir veri toplama planı oluşturun. Bu plan, veri toplama sürecinin verimli ve etik bir şekilde yürütülmesini sağlamalıdır. Elde edilen bulguları ve planı ekip ile paylaşarak geri bildirim alın ve planı buna göre güncelleyin.

**MEHMET SAİT TAYŞİ :Veri Seti Analizi ve Model Seçimi**
İncelediğimiz veri setindeki değişkenlerin dağılımlarını, birbirleriyle olan ilişkilerini ve hedef değişkenle olan korelasyonlarını detaylı bir şekilde analiz edin. Bu analiz sonucunda, hangi makine öğrenimi algoritmalarının bu veri seti için uygun olabileceğine dair bir ön değerlendirme raporu hazırlayın. Rapor, seçilen algoritmaların güçlü ve zayıf yönlerini, veri setinin özellikleriyle nasıl eşleştiğini ve beklenen performansı içermelidir.

## Cycle 3 (21 Mart - 1 Nisan)

**MİRAÇ DURAN : API Tasarımı ve Dokümantasyonu**
Platformun dış dünyayla iletişimini sağlayacak API'ların tasarımının yapılması ve API dokümantasyonunun oluşturulması.

**EMİRHAN GÜNAY : Veritabanı Şemasının Oluşturulması**
Projenin gereksinimlerine uygun bir veritabanı şemasının oluşturulması ve ilişkilerin belirlenmesi.

**AYŞE ESLEM ÇEKİCİ : UI/UX Wireframe Tasarımı**
Kullanıcı arayüzü ve kullanıcı deneyimi tasarımının yapılması, interaktif özelliklerin belirlenmesi.

**ECENUR ÜNER :**
Mevcut görev yok.

**MEHMET SAİT TAYŞİ :**
Mevcut görev yok.

## Cycle 4 (1 Nisan - 13 Nisan)

**MİRAÇ DURAN : Makine Öğrenimi Modeli: Basit Sulama Optimizasyon Modeli Geliştirme**
Toprak nemi ve hava durumu verilerini kullanarak basit bir sulama optimizasyon modeli geliştir. Model, toprak nem seviyesini belirli bir aralıkta tutmak için gereken sulama miktarını tahmin etmelidir. Model için Python ve TensorFlow/Scikit-learn kütüphanelerini kullan. Modelin performansını değerlendirmek için basit metrikler (örneğin ortalama mutlak hata) kullan.

**EMİRHAN GÜNAY : Veri Toplama Altyapısı: Toprak Sensörü Veri Entegrasyonu**
Toprak sensörlerinden gelen verilerin platforma entegrasyonunu sağla. Sensörlerden gelen ham veriyi al, temizle, dönüştür ve veri tabanına kaydet. Veri entegrasyonu için Python ve ilgili kütüphaneleri (örn. Pandas) kullan. Veri tabanı şemasını gözden geçir ve gerekli güncellemeleri yap. Entegrasyonun doğruluğunu ve performansını test et.

**AYŞE ESLEM ÇEKİCİ : Veri İşleme Altyapısı: Hava Durumu Verisi Temizleme ve Dönüştürme**
Hava durumu API'sinden (örneğin AccuWeather, OpenWeatherMap) alınan verileri temizle ve kullanılabilir bir formata dönüştür. Eksik veya hatalı verileri tespit et ve uygun yöntemlerle (örneğin ortalama değer atama, enterpolasyon) düzelt. Veriyi, platformun veri modeline uygun hale getir ve veri tabanına kaydet. Dönüşüm sürecini Python ve Pandas kullanarak gerçekleştir.

**ECENUR ÜNER : Web Arayüzü: Veri Görselleştirme Entegrasyonu (Temel)**
Web arayüzüne, toprak sensörü ve hava durumu verilerini görselleştiren temel bir bölüm entegre et. Kullanıcıların belirli bir zaman aralığı için verileri grafikler (örneğin çizgi grafikler, çubuk grafikler) üzerinde görüntülemesini sağla. Görselleştirme için Python (örneğin Flask/Django) ve JavaScript kütüphanelerini (örneğin Chart.js) kullan. Arayüzün kullanıcı dostu ve erişilebilir olduğundan emin ol.

**MEHMET SAİT TAYŞİ : API Entegrasyonu: Temel Veri Erişim API'si Geliştirme**
Platformun temel veri erişim API'sini geliştir. API, toprak sensörü ve hava durumu verilerine erişim sağlamalıdır. API'yi Python (örneğin Flask/FastAPI) kullanarak geliştir. API'nin güvenliğini sağlamak için temel kimlik doğrulama mekanizmaları (örneğin API anahtarı) kullan. API'nin dokümantasyonunu oluştur (örneğin Swagger/OpenAPI).
