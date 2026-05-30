/**
 * SFDAP Dashboard — Skeleton loader + aria-busy helpers.
 *
 * Tek kaynak burasıdır. `main.js` (ES module — index.html'de
 * `<script type="module">`) bu helper'ları doğrudan import eder
 * (`import { _skeletonBlock, _skeletonCards, _skeletonRows, _setBusy }
 * from "./lib/skeleton.js"`). Vitest de aynı modülü import edip
 * skeleton/aria-busy sözleşmesini test eder — yani testler gerçek
 * prod kodunu doğrular, kopyasını değil.
 *
 * EN: Single source of truth. main.js (ES module) imports these helpers
 * directly; Vitest exercises the same module. No mirror/duplication.
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
