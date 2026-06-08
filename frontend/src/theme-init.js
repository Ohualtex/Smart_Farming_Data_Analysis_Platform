// SFDAP — tema ilk-boya senkronu (FOUC önleme).
// index.html <head>'inde HARİCİ + render-blocking KLASİK script olarak yüklenir:
//   - inline değil → asset-split / CSP kuralına (TestAssetSplit) takılmaz,
//   - type=module DEĞİL → modüller defer'lı koşup boyamadan SONRA çalışırdı; bu
//     dosya senkron çalışıp temayı CSS boyamadan ÖNCE uygular (aksi halde welcome'da
//     ilk yüklemede gün/gece geçiş animasyonu oynar).
// Temayı <html data-theme> üzerine yazar; durum değişmediği için transition tetiklenmez.
(function () {
  try {
    var t = localStorage.getItem('sfdap-theme');
    if (!t) {
      // İlk açılış: saat 06:00–20:00 arası GÜNDÜZ, 20:00–06:00 arası GECE.
      var h = new Date().getHours();
      t = (h >= 6 && h < 20) ? 'light' : 'dark';
      localStorage.setItem('sfdap-theme', t); // sabitle → refresh değiştirmez
    }
    if (t === 'light') document.documentElement.dataset.theme = 'light';
  } catch (e) {}
})();
