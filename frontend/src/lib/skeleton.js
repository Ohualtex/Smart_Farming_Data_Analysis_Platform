/**
 * SFDAP Dashboard — Skeleton loader + aria-busy helpers (test mirror).
 *
 * ⚠️  DRIFT NOTE
 * --------------
 * These 4 functions are currently duplicated from `frontend/src/main.js`
 * lines 31-68. main.js is loaded as a classic <script> (23 inline
 * onclick handlers in index.html depend on globals); converting it to
 * an ES module is planned as a Cycle 9 follow-up (`projeakisi.md`
 * Cycle 9 / Ecenur — Sunum Materyalleri'nde frontend cila pasajı).
 *
 * Until then, this lib mirrors main.js so Vitest can exercise the
 * skeleton/aria-busy contract without touching the browser bundle.
 * If you change a helper in main.js, mirror it here (or vice-versa);
 * tests pin the visual + a11y shape and will fail loudly on drift.
 *
 * EN/TR: main.js'in 31-68. satırlarındaki yardımcılar burada Vitest
 * için kopyalanmıştır. main.js klasik script olarak yüklenir (index.html
 * inline onclick handler'ları globaller kullanır); ES module geçişi
 * Cycle 9 cila pasajına planlanmıştır. Helper'lardan birini değiştirirsen
 * iki dosyayı da senkronize et — testler HTML + aria-busy şeklini sabitler.
 */

export function _skeletonCards(count = 4) {
  let html = "";
  for (let i = 0; i < count; i++) {
    html +=
      '<div class="card skeleton-card">' +
      '<div class="skeleton skeleton-line lg" style="height:32px;width:32px;border-radius:50%;"></div>' +
      '<div class="skeleton skeleton-line lg" style="margin-top:12px;"></div>' +
      '<div class="skeleton skeleton-line sm" style="margin-top:8px;"></div>' +
      "</div>";
  }
  return html;
}

export function _skeletonRows(rows = 6, cols = 4) {
  let html = "";
  for (let r = 0; r < rows; r++) {
    html += '<tr class="skeleton-row">';
    for (let c = 0; c < cols; c++) {
      html += '<td><span class="skeleton skeleton-line"></span></td>';
    }
    html += "</tr>";
  }
  return html;
}

export function _skeletonBlock(lines = 3) {
  let html = '<div class="skeleton-card" style="margin:0;">';
  for (let i = 0; i < lines; i++) {
    html += `<div class="skeleton skeleton-line${i === 0 ? " lg" : i === lines - 1 ? " sm" : ""}"></div>`;
  }
  html += "</div>";
  return html;
}

export function _setBusy(elementId, busy) {
  const el = document.getElementById(elementId);
  if (el) el.setAttribute("aria-busy", busy ? "true" : "false");
}
