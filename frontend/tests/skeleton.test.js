/**
 * Birim testler — `frontend/src/lib/skeleton.js`.
 *
 * Kapsam: 4 helper'ın HTML kontratı + aria-busy davranışı.
 * Bu testler skeleton loader'ların shape'ini sabitler — eğer main.js'teki
 * aynı helper'lar drift ederse buradaki assertion'lar da güncellenmeli.
 *
 * Ayrıca a11y kontratını koruyoruz (aria-busy true/false toggle).
 */

import { describe, it, expect, beforeEach } from "vitest";
import {
  _skeletonCards,
  _skeletonRows,
  _skeletonBlock,
  _setBusy,
} from "../src/lib/skeleton.js";

describe("_skeletonCards", () => {
  it("default count = 4 kartlık iskelet üretir", () => {
    const html = _skeletonCards();
    const matches = html.match(/class="card skeleton-card"/g);
    expect(matches).not.toBeNull();
    expect(matches.length).toBe(4);
  });

  it("count parametresine göre doğru sayıda kart üretir", () => {
    expect(_skeletonCards(0)).toBe("");
    expect(_skeletonCards(1).match(/skeleton-card/g).length).toBe(1);
    expect(_skeletonCards(7).match(/skeleton-card/g).length).toBe(7);
  });

  it("her kartta icon + line lg + line sm placeholder içerir", () => {
    const html = _skeletonCards(1);
    expect(html).toContain("skeleton-line lg");
    expect(html).toContain("skeleton-line sm");
    expect(html).toContain("border-radius:50%"); // icon placeholder
  });
});

describe("_skeletonRows", () => {
  it("default 6 satır × 4 sütun tablo iskeleti üretir", () => {
    const html = _skeletonRows();
    const rows = html.match(/<tr class="skeleton-row">/g);
    const cells = html.match(/<td>/g);
    expect(rows.length).toBe(6);
    expect(cells.length).toBe(6 * 4);
  });

  it("rows ve cols parametrelerini kombinleyerek üretir", () => {
    const html = _skeletonRows(3, 5);
    expect(html.match(/<tr/g).length).toBe(3);
    expect(html.match(/<td>/g).length).toBe(3 * 5);
  });

  it("hücre içinde skeleton-line span yer alır", () => {
    const html = _skeletonRows(1, 1);
    expect(html).toContain('<span class="skeleton skeleton-line"></span>');
  });
});

describe("_skeletonBlock", () => {
  it("default 3 satırlık blok üretir; ilk satır lg, son satır sm", () => {
    const html = _skeletonBlock();
    // 3 satır = ilk (lg) + orta (varsayılan) + son (sm)
    expect(html.match(/skeleton-line lg/g).length).toBe(1);
    expect(html.match(/skeleton-line sm/g).length).toBe(1);
    expect(html.match(/skeleton-line(?! lg| sm)/g).length).toBe(1);
  });

  it("lines = 1 ise sadece tek lg satır", () => {
    const html = _skeletonBlock(1);
    // Tek satırda hem ilk hem son olduğu için lg etiketi alır (i===0 koşulu öncelikli)
    expect(html).toContain("skeleton-line lg");
    expect(html.match(/skeleton-line/g).length).toBe(1);
  });

  it("wrapper olarak skeleton-card kullanır (margin:0 sıfırlanmış)", () => {
    const html = _skeletonBlock(2);
    expect(html.startsWith('<div class="skeleton-card"')).toBe(true);
    expect(html).toContain("margin:0");
  });
});

describe("_setBusy", () => {
  beforeEach(() => {
    document.body.innerHTML = '<div id="target"></div><div id="other"></div>';
  });

  it("busy=true verilince aria-busy='true' set eder", () => {
    _setBusy("target", true);
    expect(document.getElementById("target").getAttribute("aria-busy")).toBe(
      "true",
    );
  });

  it("busy=false verilince aria-busy='false' set eder", () => {
    _setBusy("target", false);
    expect(document.getElementById("target").getAttribute("aria-busy")).toBe(
      "false",
    );
  });

  it("var olmayan elementId sessizce yutulur (no throw)", () => {
    expect(() => _setBusy("does-not-exist", true)).not.toThrow();
  });

  it("truthy/falsy verildiğinde 'true'/'false' string'e normalize eder", () => {
    _setBusy("target", 1);
    expect(document.getElementById("target").getAttribute("aria-busy")).toBe(
      "true",
    );
    _setBusy("target", 0);
    expect(document.getElementById("target").getAttribute("aria-busy")).toBe(
      "false",
    );
    _setBusy("target", null);
    expect(document.getElementById("target").getAttribute("aria-busy")).toBe(
      "false",
    );
  });

  it("birden çok element için bağımsız toggle yapar", () => {
    _setBusy("target", true);
    _setBusy("other", false);
    expect(document.getElementById("target").getAttribute("aria-busy")).toBe(
      "true",
    );
    expect(document.getElementById("other").getAttribute("aria-busy")).toBe(
      "false",
    );
  });
});
