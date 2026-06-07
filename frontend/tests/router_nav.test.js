/**
 * Birim testler — navigate() (frontend/src/lib/router.js).
 *
 * Kapsam: hedef sayfa aktive + başlık güncelleme; hash senkronu (refresh
 * kalıcılığı, replaceState); tepeden açılma (scrollTo 0,0); active highlight
 * yalnız .nav-item'lara; handler tetikleme.
 * jsdom environment vitest config'inden gelir.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { navigate } from "../src/lib/router.js";

beforeEach(() => {
  document.body.innerHTML = `
    <div id="sidebar" class="open"></div>
    <button class="hamburger" aria-expanded="true"></button>
    <main id="main-content" tabindex="-1"></main>
    <a class="nav-item" href="#dashboard">Genel</a>
    <a class="nav-item" href="#weather">Hava</a>
    <h1 id="pageTitle"></h1>
    <p id="pageSubtitle"></p>
    <section class="page active" id="page-dashboard"></section>
    <section class="page" id="page-weather"></section>`;
  history.replaceState(null, "", " ");
  vi.spyOn(window, "scrollTo").mockImplementation(() => {});
  vi.spyOn(history, "replaceState");
});
afterEach(() => {
  vi.restoreAllMocks();
  document.body.innerHTML = "";
});

describe("navigate", () => {
  it("hedef sayfayı aktive eder + öncekini kapatır + başlık günceller", () => {
    navigate("weather", {}, null);
    expect(document.getElementById("page-weather").classList.contains("active")).toBe(true);
    expect(document.getElementById("page-dashboard").classList.contains("active")).toBe(false);
    expect(document.getElementById("pageTitle").textContent).toBeTruthy();
    expect(document.getElementById("pageSubtitle").textContent).toBeTruthy();
  });

  it("hash'i mevcut sayfaya senkronlar (refresh kalıcılığı)", () => {
    navigate("weather", {}, null);
    expect(history.replaceState).toHaveBeenCalledWith(null, "", "#weather");
  });

  it("sayfayı tepeden açar (scrollTo 0,0)", () => {
    navigate("weather", {}, null);
    expect(window.scrollTo).toHaveBeenCalledWith(0, 0);
  });

  it("active highlight yalnız .nav-item'a — çip (nav-item değil) active almaz", () => {
    document.body.insertAdjacentHTML(
      "beforeend",
      '<a class="user-badge" href="#weather" id="chip"></a>',
    );
    navigate("weather", {}, null);
    expect(document.querySelector('.nav-item[href="#weather"]').classList.contains("active")).toBe(true);
    expect(document.getElementById("chip").classList.contains("active")).toBe(false);
  });

  it("mobil sidebar'ı kapatır", () => {
    navigate("weather", {}, null);
    expect(document.getElementById("sidebar").classList.contains("open")).toBe(false);
    expect(document.querySelector(".hamburger").getAttribute("aria-expanded")).toBe("false");
  });

  it("sayfa handler'ını çağırır", () => {
    const h = vi.fn();
    navigate("weather", { weather: h }, null);
    expect(h).toHaveBeenCalledTimes(1);
  });
});
