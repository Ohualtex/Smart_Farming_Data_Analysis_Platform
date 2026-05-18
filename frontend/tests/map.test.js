/**
 * Birim testler — `frontend/src/lib/map.js`.
 *
 * Kapsam: saf yardımcı fonksiyonlar (XSS-safe escape, popup HTML, marker
 * options, region color map). DOM/Leaflet bağımlı kısım (`loadMap`,
 * `_ensureMapInstance`, wheel handler) burada test edilmez — onlar için
 * jsdom + L.map mock'u gerekir; gerçekten gerekirse ayrı bir test
 * dosyasında yapılır.
 *
 * Bu testlerin niyeti:
 *   - 7 bölge renk haritasının tam ve doğru hex'lerle tanımlı olduğunu
 *     pin'lemek (legend ile sürüş);
 *   - `_escapeHtml`'in 5 XSS karakterini doğru çevirdiğini;
 *   - `_farmPopupHtml`'in unsafe input'u sanitize ettiğini;
 *   - `_markerOptions`'un region'a göre doğru fillColor, bilinmeyen
 *     region'da default color döndürdüğünü.
 */

import { describe, expect, it } from "vitest";
import {
  DEFAULT_REGION_COLOR,
  REGION_COLORS,
  TURKEY_CENTER,
  TURKEY_ZOOM,
  _escapeHtml,
  _farmPopupHtml,
  _markerOptions,
} from "../src/lib/map.js";

describe("REGION_COLORS — 7 bölge renk paleti", () => {
  it("legend ile birebir 7 bölge tanımlı", () => {
    expect(Object.keys(REGION_COLORS)).toEqual(
      expect.arrayContaining([
        "Marmara",
        "Ege",
        "Akdeniz",
        "İç Anadolu",
        "Karadeniz",
        "Doğu Anadolu",
        "Güneydoğu Anadolu",
      ]),
    );
    expect(Object.keys(REGION_COLORS).length).toBe(7);
  });

  it("her renk 7-karakterlik hex formatında", () => {
    Object.values(REGION_COLORS).forEach((hex) => {
      expect(hex).toMatch(/^#[0-9A-F]{6}$/i);
    });
  });

  it("default fallback color tanımlı + hex format", () => {
    expect(DEFAULT_REGION_COLOR).toMatch(/^#[0-9A-Fa-f]{6}$/);
  });
});

describe("TURKEY_CENTER / TURKEY_ZOOM — harita merkez sabitleri", () => {
  it("Türkiye merkez koordinatı plausible bounds içinde", () => {
    expect(TURKEY_CENTER).toHaveLength(2);
    const [lat, lng] = TURKEY_CENTER;
    expect(lat).toBeGreaterThanOrEqual(35);
    expect(lat).toBeLessThanOrEqual(43);
    expect(lng).toBeGreaterThanOrEqual(25);
    expect(lng).toBeLessThanOrEqual(45);
  });

  it("default zoom ulusal ölçek için makul (5-7)", () => {
    expect(TURKEY_ZOOM).toBeGreaterThanOrEqual(5);
    expect(TURKEY_ZOOM).toBeLessThanOrEqual(7);
  });
});

describe("_escapeHtml — XSS sanitize", () => {
  it("null / undefined için boş string döner", () => {
    expect(_escapeHtml(null)).toBe("");
    expect(_escapeHtml(undefined)).toBe("");
  });

  it("5 tehlikeli karakteri doğru entity'ye çevirir", () => {
    expect(_escapeHtml("&")).toBe("&amp;");
    expect(_escapeHtml("<")).toBe("&lt;");
    expect(_escapeHtml(">")).toBe("&gt;");
    expect(_escapeHtml('"')).toBe("&quot;");
    expect(_escapeHtml("'")).toBe("&#39;");
  });

  it("script tag enjekte edemez (XSS sanity)", () => {
    const out = _escapeHtml("<script>alert(1)</script>");
    expect(out).not.toContain("<script>");
    expect(out).toContain("&lt;script&gt;");
  });

  it("sayı / boolean gibi non-string input'u String'e çevirir", () => {
    expect(_escapeHtml(42)).toBe("42");
    expect(_escapeHtml(true)).toBe("true");
  });
});

describe("_farmPopupHtml — popup HTML üretimi", () => {
  const sampleFarm = {
    id: 1,
    name: "Adana Tarım Çiftliği",
    city: "Adana",
    region: "Akdeniz",
    area_hectares: 239,
  };

  it("name + city + region + alan + ID içerir", () => {
    const html = _farmPopupHtml(sampleFarm);
    expect(html).toContain("Adana Tarım Çiftliği");
    expect(html).toContain("Adana");
    expect(html).toContain("Akdeniz");
    expect(html).toContain("239.0 ha");
    expect(html).toContain("#1");
  });

  it("alan null ise em-dash gösterir", () => {
    const html = _farmPopupHtml({ ...sampleFarm, area_hectares: null });
    expect(html).toContain("Alan: —");
  });

  it("XSS taşıyan name input'u sanitize edilir", () => {
    const html = _farmPopupHtml({
      ...sampleFarm,
      name: '<img src=x onerror="alert(1)">',
    });
    expect(html).not.toContain("<img src=x");
    expect(html).toContain("&lt;img");
  });

  it("city / region null ise '·' separator hâlâ render", () => {
    const html = _farmPopupHtml({ ...sampleFarm, city: null, region: null });
    expect(html).toContain(" · ");
  });
});

describe("_markerOptions — region renk + outline", () => {
  const baseFarm = { region: "Marmara" };

  it("Marmara region için fillColor #4A90E2 (legend ile uyumlu)", () => {
    const opts = _markerOptions(baseFarm);
    expect(opts.fillColor).toBe(REGION_COLORS.Marmara);
    expect(opts.fillColor).toBe("#4A90E2");
  });

  it("bilinmeyen region için DEFAULT_REGION_COLOR fallback", () => {
    const opts = _markerOptions({ region: "Mars Kolonisi" });
    expect(opts.fillColor).toBe(DEFAULT_REGION_COLOR);
  });

  it("outline her zaman koyu (#1f2937) — WCAG kontrast 3:1+", () => {
    const opts = _markerOptions(baseFarm);
    expect(opts.color).toBe("#1f2937");
    expect(opts.weight).toBeGreaterThanOrEqual(1);
  });

  it("radius pixel-tabanlı (zoom-independent)", () => {
    const opts = _markerOptions(baseFarm);
    expect(opts.radius).toBe(7);
  });

  it("custom palette inject edilebilir (DI)", () => {
    const customPalette = { Marmara: "#FF00FF" };
    const opts = _markerOptions(baseFarm, customPalette);
    expect(opts.fillColor).toBe("#FF00FF");
  });
});
