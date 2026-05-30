/**
 * SFDAP Dashboard — UI helpers (form-error + envelope mesaj).
 *
 * ⚠️  DRIFT NOTE (bağlama eksik)
 * ------------------------------
 * Bu modül şu an YALNIZ Vitest tarafından import edilir; `main.js` bunu
 * henüz import ETMEZ — aynı 4 helper main.js içinde `_` önekiyle
 * (`_setFieldError`/`_clearFieldError`/`_clearAllErrors`/`_extractErrorMessage`)
 * birebir duplike tanımlıdır. Yani test prod kodunun *kopyasını* doğruluyor.
 * İdeal: main.js bu modülü import etsin (skeleton.js deseni) ki test gerçek
 * prod kodunu doğrulasın. O bağlama yapılana kadar main.js'teki bir
 * değişikliği burada da yansıt (aksi halde sessiz drift).
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
