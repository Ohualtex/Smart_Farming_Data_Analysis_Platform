/**
 * SFDAP Dashboard — UI helpers (form-error + envelope mesaj).
 *
 * Tek kaynak burasıdır. `main.js` (ES module) bu helper'ları `_` alias'ıyla
 * import eder (`import { setFieldError as _setFieldError, ... } from
 * "./lib/ui_helpers.js"`); Vitest de aynı modülü import edip test eder.
 * Yani test gerçek prod kodunu doğrular — kopyasını değil (duplikasyon
 * fixroll_v7'de kaldırıldı).
 *
 * Fonksiyonlar:
 *   - setFieldError / clearFieldError / clearAllErrors  (v5-5 form validation)
 *   - extractErrorMessage                               (v5-1 api() envelope)
 */

/**
 * Form group'a hata göster — `.has-error` class + `.field-error` doldurma +
 * `aria-invalid="true"`. Form-group bulunamadıysa no-op.
 */
export function setFieldError(inputId, msg) {
  const input = document.getElementById(inputId);
  if (!input) return;
  const group = input.closest(".form-group");
  if (!group) return;
  group.classList.add("has-error");
  let errEl = group.querySelector(".field-error");
  if (!errEl) {
    errEl = document.createElement("div");
    errEl.className = "field-error";
    errEl.setAttribute("role", "alert");
    group.appendChild(errEl);
  }
  errEl.textContent = msg;
  input.setAttribute("aria-invalid", "true");
}

/** Bir alanın error state'ini tamamen temizle. */
export function clearFieldError(inputId) {
  const input = document.getElementById(inputId);
  if (!input) return;
  const group = input.closest(".form-group");
  if (!group) return;
  group.classList.remove("has-error");
  input.removeAttribute("aria-invalid");
  const errEl = group.querySelector(".field-error");
  if (errEl) errEl.textContent = "";
}

/** Birden çok alanı bir kerede temizle (forEach helper). */
export function clearAllErrors(...ids) {
  ids.forEach(clearFieldError);
}

/**
 * Backend hata envelope'undan kullanıcıya gösterilecek mesaj üret.
 * SFDAPError envelope: `{error_code, message, detail}`.
 * - `message` öncelikli (TR, kullanıcı dostu)
 * - `detail` (string ise) fallback
 * - hiçbiri yoksa generic `HTTP ${status}`
 *
 * `res.clone()` ile orig response stream'ini bozmadan okur.
 */
export async function extractErrorMessage(res) {
  try {
    const body = await res.clone().json();
    if (body && typeof body.message === "string" && body.message.trim()) return body.message;
    if (body && typeof body.detail === "string" && body.detail.trim()) return body.detail;
  } catch {
    // body JSON değil veya parse hatası — generic mesaja düş
  }
  return `HTTP ${res.status}`;
}

export function fmtDate(iso) {
    if (!iso) return '—';
    try { return new Date(iso).toLocaleDateString('tr-TR', { day: '2-digit', month: 'short' }); }
    catch { return iso; }
}

export function fmtNumber(v, decimals = 1) {
    if (v === null || v === undefined) return '—';
    return Number(v).toLocaleString('tr-TR', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

export function escAttr(s) {
    return String(s ?? '').replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

export const STATUS_LABEL = { dry: 'Susuz', optimal: 'Uygun', wet: 'Aşırı sulu', no_data: 'Veri yok' };
export const STATUS_EMOJI = { dry: '🥵', optimal: '👌', wet: '💧', no_data: '—' };

export function showToast(message, type = 'info') {
    window.dispatchEvent(new CustomEvent('toast', { detail: { msg: message, type } }));
}

export const pageTitles = {
    dashboard: ['Genel Bakış', 'Tarlanın özeti'],
    fields: ['Tarlalarım', 'Çiftliklerine bağlı tarlalar'],
    'field-detail': ['Tarla Detayı', 'Sensör, sulama, hastalık ve toprak'],
    weather: ['Hava Durumu', 'Sıcaklık, nem ve yağış'],
    irrigation: ['Sulama', 'Önerilen su miktarı ve geçmiş'],
    fertilizer: ['Gübreleme', 'NPK önerisi ve takvim'],
    sensors: ['Sensörler', 'Tarladaki ölçüm cihazları'],
    analytics: ['Raporlar', 'Bölge bazında özet ve dışa aktarma'],
    map: ['Türkiye Haritası', 'Çiftliklerin coğrafi dağılımı'],
    plants: ['Bitki Sağlığı', 'Yapraktan hastalık tespiti'],
    alerts: ['Uyarılar', 'Sistem ve sensör uyarıları'],
    users: ['Kullanıcı Yönetimi', 'Tüm kullanıcılar (admin)'],
    auth: ['Hesabım', 'Profil ve şifre'],
};
