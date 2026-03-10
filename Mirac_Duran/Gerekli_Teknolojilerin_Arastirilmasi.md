# $\color{red}{\textbf{📊 Akıllı Tarım Platformu Teknoloji Raporu}}$

Bu proje temel olarak iki farklı veri tipiyle çalışacak: Tablo verileri (sensörlerden gelen nem, sıcaklık vb.) ve Görüntü verileri (bitki sağlığı için yaprak fotoğrafları). Seçilecek teknolojiler bu iki veri tipini de en verimli şekilde işleyebilmelidir.

$\color{pink}{\textbf{1. Ana Programlama Dili}}$
---
•	Python: Veri bilimi ve makine öğrenimi dünyasının tartışmasız lideridir. Ekibinin geniş kütüphane desteği ve zengin dokümantasyon sayesinde karşılaştığı hataları kolayca çözebilmesi için en doğru tercih olacaktır.

$\color{pink}{\textbf{2. Veri Madenciliği ve Ön İşleme Kütüphaneleri (Data Mining)}}$
---
Toprak sensörlerinden ve hava durumu API'lerinden gelen veriler genellikle kirli veya eksik olur. Modele girmeden önce temizlenmeleri gerekir.

• Pandas: Proje gereksinimlerinde de belirtildiği gibi, tablo formatındaki verileri (CSV, Excel veya SQL'den çekilen veriler) işlemek, filtrelemek ve analiz etmek için temel araçtır. "Hangi günlerde toprak nemi %20'nin altına düştü?" gibi soruların cevabını Pandas ile bulacaksınız.

•	NumPy: Yüksek performanslı matematiksel hesaplamalar ve çok boyutlu diziler (array) için gereklidir. Görüntü işleme sürecinin de temelini oluşturur.

•	Scikit-Learn (Sklearn): Makine öğrenimine giriş için en ideal kütüphanedir. Verileri ölçeklendirmek (normalization), eksik verileri doldurmak ve sulama optimizasyonu gibi konularda temel regresyon/sınıflandırma algoritmalarını (Rastgele Orman, Karar Ağaçları) kurmak için kullanılacaktır.

$\color{pink}{\textbf{3. Makine Öğrenimi ve Derin Öğrenme Araçları (Deep Learning)}}$
---
Hastalık tahmini gibi karmaşık işlemler için standart algoritmalar yetersiz kalır, derin öğrenmeye ihtiyaç duyulur.

•	TensorFlow & Keras: Proje tanımında istenen bu teknoloji, özellikle "Bitki Sağlığı Görüntülerini" analiz etmek için kullanılacak. Evrişimli Sinir Ağları (CNN) kurarak, hastalıklı bir yaprak fotoğrafı ile sağlıklı bir yaprak fotoğrafını birbirinden ayırt eden modeller eğiteceksiniz. Keras, TensorFlow'un kullanımını çok daha kolaylaştıran üst katmanıdır.

•	OpenCV: Görüntüleri TensorFlow modeline sokmadan önce boyutlarını ayarlamak, renkleri düzenlemek veya gürültüyü azaltmak için kullanılacak temel görüntü işleme kütüphanesidir.

$\color{pink}{\textbf{4. Veritabanı ve Bulut Bilişim (Storage \ Cloud)}}$
---

•	PostgreSQL (SQL): Sensörlerden akan zaman serisi verilerini (time-series data) ve kullanıcı bilgilerini güvenli bir şekilde tutmak için en güçlü açık kaynaklı ilişkisel veritabanlarından biridir.

•	Bulut Platformu Seçimi (AWS / GCP / Azure): Öğrenci kredileri ve sunduğu kolaylıklar açısından AWS (Amazon Web Services) veya GCP (Google Cloud Platform) tercih edilebilir. AWS üzerinde S3 (görüntüleri depolamak için) ve RDS (SQL veritabanını barındırmak için) başlangıç için ideal hizmetlerdir.



$\color{pink}{\textbf{5. Görselleştirme ve Arayüz Araçları}}$
---
•	Streamlit veya Dash: Bir web arayüzü istendiği için, ekibin sıfırdan HTML/CSS/JavaScript öğrenmekle vakit kaybetmesini istemiyorsan, doğrudan Python kodlarıyla harika veri panoları (dashboard) ve web arayüzleri oluşturabilen bu kütüphaneleri kullanabilirsiniz.

•	Matplotlib ve Seaborn: Veri analizi aşamasında, çiftçiye sunulacak raporlardaki grafikleri çizdirmek için kullanılacak standart Python kütüphaneleridir.



## 📌 $\color{red}{\textbf{Teknoloji ve Özellik Eşleştirme Tablosu}}$

Aşağıdaki tablo, proje isterlerinin hangi teknolojiyle çözüleceğini özetler:

| Proje Özelliği | Kullanılacak Veri Tipi | Önerilen Teknoloji / Kütüphane |
|:---:|:---:|:---:|
| Veri Toplama & Temizleme | Sensör, Hava Durumu | Python, Pandas, SQL |
| Sulama Optimizasyonu | Sayısal (Nem, Sıcaklık) | Scikit-Learn (Regresyon Modelleri) |
| Hastalık Tahmini | Görsel (Yaprak Fotoları) | OpenCV, TensorFlow / Keras |
| Veritabanı Yönetimi | Tablo / İlişkisel | PostgreSQL, Cloud SQL (GCP/AWS) |
| Görselleştirme & Arayüz | Tüm Çıktılar | Streamlit, Matplotlib |
