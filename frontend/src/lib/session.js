/* ============================================================
   SFDAP — Session State Module
   ============================================================
   Paylaşılan oturum durumu (son /me snapshot). main.js'teki
   `currentUser` modül-local state'i buraya taşındı; sayfa modülleri
   (dashboard, filiz, account) bu tek kaynağı okur/yazar.
   api.js initApiCallbacks({setCurrentUser}) ile burayı günceller.
   ============================================================ */

let _currentUser = null;

export function getCurrentUser() { return _currentUser; }

export function setCurrentUser(u) { _currentUser = u; }

// ─── apiOnline runtime flag ───────────────────────────────────
// loadDashboard (dashboard.js) sağlık durumuna göre yazar; init (main.js)
// ilk yüklemede yazar; filiz updateMood (filiz.js) okur. Modüller-arası
// paylaşılan glue state — döngüsüzlük için tek kaynak burada.
let _apiOnline = false;

export function getApiOnline() { return _apiOnline; }

export function setApiOnline(v) { _apiOnline = v; }
