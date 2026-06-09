/**
 * SFDAP Dashboard — UI helpers (test mirror).
 *
 * ⚠️  DRIFT NOTE
 * --------------
 * v5-1 ve v5-5'te `frontend/src/main.js`'e eklenen helper'lar burada
 * mirror edildi (`skeleton.js` ile aynı desen — main.js klasik script
 * olarak yüklenir, ES module geçişi Cycle 9 cila'sına planlanmış).
 *
 * Mirror edilen fonksiyonlar:
 *   - `setFieldError(inputId, msg)`     v5-5 inline form validation
 *   - `clearFieldError(inputId)`        v5-5 inline form validation
 *   - `clearAllErrors(...ids)`          v5-5 batch helper
 *   - `extractErrorMessage(res)`        v5-1 api() envelope toast
 *
 * Helper'lardan birini main.js'te değiştirirsen buradakini de güncelle
 * (drift kontrolü için vitest aynı kontratı pin'liyor).
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
    // Pydantic 422: detail bir dizi ({loc,msg,type}) → alan mesajlarını birleştir
    // (audit ORTA #26: aksi halde kullanıcı ham "HTTP 422" görüyordu).
    if (body && Array.isArray(body.detail) && body.detail.length) {
      const msgs = body.detail.map((e) => (e && typeof e.msg === "string" ? e.msg : null)).filter(Boolean);
      if (msgs.length) return msgs.join(" · ");
    }
  } catch {
    // body JSON değil veya parse hatası — generic mesaja düş
  }
  return `HTTP ${res.status}`;
}
