/**
 * Birim testler — `frontend/src/lib/ui_helpers.js` (v6-2).
 *
 * Kapsam:
 *   - setFieldError / clearFieldError DOM kontratı (.has-error class,
 *     .field-error içerik, aria-invalid attr, role="alert").
 *   - clearAllErrors batch davranışı.
 *   - extractErrorMessage envelope parsing (message > detail > HTTP fallback).
 *
 * jsdom environment'ı vitest config'inden gelir (`jsdom` devDependency).
 */

import { afterEach, beforeEach, describe, expect, it } from "vitest";
import {
  clearAllErrors,
  clearFieldError,
  extractErrorMessage,
  setFieldError,
} from "../src/lib/ui_helpers.js";

function makeForm(...ids) {
  document.body.innerHTML = ids
    .map(
      (id) => `
        <div class="form-group">
          <label for="${id}">Label ${id}</label>
          <input id="${id}" />
        </div>`,
    )
    .join("\n");
}

describe("setFieldError", () => {
  beforeEach(() => makeForm("email", "password"));
  afterEach(() => (document.body.innerHTML = ""));

  it("input'un form-group'una .has-error class ekler", () => {
    setFieldError("email", "Geçersiz e-posta");
    const group = document.getElementById("email").closest(".form-group");
    expect(group.classList.contains("has-error")).toBe(true);
  });

  it(".field-error elementi yaratır ve mesajı yazar", () => {
    setFieldError("email", "Gerekli alan");
    const err = document.querySelector(".field-error");
    expect(err).not.toBeNull();
    expect(err.textContent).toBe("Gerekli alan");
  });

  it("input'a aria-invalid='true' ekler (a11y)", () => {
    setFieldError("email", "X");
    expect(document.getElementById("email").getAttribute("aria-invalid")).toBe("true");
  });

  it(".field-error elementi role='alert' alır (screen reader)", () => {
    setFieldError("email", "X");
    expect(document.querySelector(".field-error").getAttribute("role")).toBe("alert");
  });

  it("ikinci çağrı mevcut .field-error'i tekrar yaratmaz, içeriği günceller", () => {
    setFieldError("email", "İlk");
    setFieldError("email", "İkinci");
    const errs = document.querySelectorAll(".field-error");
    expect(errs.length).toBe(1);
    expect(errs[0].textContent).toBe("İkinci");
  });

  it("bulunmayan input için no-op (crash etmez)", () => {
    expect(() => setFieldError("missing", "X")).not.toThrow();
  });
});

describe("clearFieldError", () => {
  beforeEach(() => makeForm("email"));
  afterEach(() => (document.body.innerHTML = ""));

  it("has-error class'ı kaldırır", () => {
    setFieldError("email", "X");
    clearFieldError("email");
    const group = document.getElementById("email").closest(".form-group");
    expect(group.classList.contains("has-error")).toBe(false);
  });

  it("aria-invalid attribute'unu siler", () => {
    setFieldError("email", "X");
    clearFieldError("email");
    expect(document.getElementById("email").hasAttribute("aria-invalid")).toBe(false);
  });

  it(".field-error içeriğini boşaltır (element kalır — re-use için)", () => {
    setFieldError("email", "X");
    clearFieldError("email");
    expect(document.querySelector(".field-error").textContent).toBe("");
  });
});

describe("clearAllErrors", () => {
  beforeEach(() => makeForm("a", "b", "c"));
  afterEach(() => (document.body.innerHTML = ""));

  it("verilen tüm ID'lerin hatalarını temizler", () => {
    setFieldError("a", "1");
    setFieldError("b", "2");
    setFieldError("c", "3");
    clearAllErrors("a", "b", "c");
    document.querySelectorAll(".form-group").forEach((g) => {
      expect(g.classList.contains("has-error")).toBe(false);
    });
  });
});

describe("extractErrorMessage", () => {
  function mockRes(body, status = 400) {
    return new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    });
  }

  it("envelope.message varsa onu döner", async () => {
    const res = mockRes({ error_code: "NOT_FOUND", message: "Çiftlik bulunamadı.", detail: "id=99" });
    expect(await extractErrorMessage(res)).toBe("Çiftlik bulunamadı.");
  });

  it("message yok ama detail (string) varsa detail'i döner", async () => {
    const res = mockRes({ detail: "Beklenmeyen hata" });
    expect(await extractErrorMessage(res)).toBe("Beklenmeyen hata");
  });

  it("ikisi de boş string ise fallback HTTP status", async () => {
    const res = mockRes({ message: "", detail: "" }, 422);
    expect(await extractErrorMessage(res)).toBe("HTTP 422");
  });

  it("body JSON değilse fallback HTTP status (parse hatası yutulur)", async () => {
    const res = new Response("plain text crash", { status: 500 });
    expect(await extractErrorMessage(res)).toBe("HTTP 500");
  });

  it("detail array ise (Pydantic 422) alan mesajlarını birleştirir", async () => {
    const res = mockRes({ detail: [{ loc: ["body", "email"], msg: "field required" }] }, 422);
    expect(await extractErrorMessage(res)).toBe("field required");
  });

  it("detail array çok alanlıysa mesajları ' · ' ile birleştirir", async () => {
    const res = mockRes({ detail: [{ msg: "field required" }, { msg: "value too long" }] }, 422);
    expect(await extractErrorMessage(res)).toBe("field required · value too long");
  });

  it("res.clone() kullanır — body stream sonra başka yerde okunabilir", async () => {
    const res = mockRes({ message: "OK" });
    await extractErrorMessage(res);
    // Orig response hâlâ okunabilir olmalı (stream tüketilmedi)
    const body = await res.json();
    expect(body.message).toBe("OK");
  });
});
