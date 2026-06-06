/* ============================================================
   SFDAP — Navigation Bridge
   ============================================================
   `navigate()` implementasyonu main.js'te kuruluyor (pageHandlers +
   _startHeroTipRotation'a bağlı). Sayfa modülleri (fields, account)
   navigate'e ihtiyaç duyuyor ama main.js'ten import etmek döngü yaratır
   (main → pages → main). Çözüm: mutable bir referans — main init'te
   setNavigate ile gerçek fonksiyonu enjekte eder, modüller navigate()
   wrapper'ını çağırır. Bu modül leaf'tir (hiçbir şey import etmez).
   ============================================================ */

let _navigateImpl = null;

export function setNavigate(fn) { _navigateImpl = fn; }

export function navigate(page) {
    if (_navigateImpl) _navigateImpl(page);
}
