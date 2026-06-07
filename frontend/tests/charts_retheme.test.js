/**
 * Birim testler — rethemeCharts() (frontend/src/lib/charts.js).
 *
 * Tema değişiminde kayıtlı Chart.js instance'larının canvas-içi renkleri
 * YERİNDE güncellenmeli; amber (#f59e0b) / mavi (#3b82f6) accent eksen
 * tick'leri KORUNMALI; grid:display=false eksenine dokunulmamalı.
 * jsdom environment vitest config'inden gelir.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  charts,
  rethemeCharts,
  chartTick,
  chartLegend,
  chartGrid,
} from "../src/lib/charts.js";

function mockChart() {
  return {
    options: {
      plugins: { legend: { labels: { color: "#000" } }, title: { color: "#000" } },
      scales: {
        x: { ticks: { color: "#000" }, grid: { color: "#000" } },
        y: { ticks: { color: "#f59e0b" }, grid: { color: "#000" } }, // amber accent
        y1: { ticks: { color: "#3b82f6" }, grid: { display: false } }, // mavi accent, grid kapalı
      },
    },
    update: vi.fn(),
  };
}

function clearRegistry() {
  Object.keys(charts).forEach((k) => delete charts[k]);
}

describe("rethemeCharts", () => {
  beforeEach(() => {
    clearRegistry();
    document.documentElement.dataset.theme = "light";
  });
  afterEach(() => {
    clearRegistry();
    delete document.documentElement.dataset.theme;
  });

  it("gri tick/legend/grid renklerini güncel temaya çeker + update çağırır", () => {
    const c = mockChart();
    charts.test = c;
    document.documentElement.dataset.theme = "dark";
    rethemeCharts();
    expect(c.options.scales.x.ticks.color).toBe(chartTick());
    expect(c.options.plugins.legend.labels.color).toBe(chartLegend());
    expect(c.options.scales.x.grid.color).toBe(chartGrid());
    expect(c.update).toHaveBeenCalled();
  });

  it("amber/mavi accent eksen tick'lerini KORUR", () => {
    const c = mockChart();
    charts.test = c;
    document.documentElement.dataset.theme = "dark";
    rethemeCharts();
    expect(c.options.scales.y.ticks.color).toBe("#f59e0b");
    expect(c.options.scales.y1.ticks.color).toBe("#3b82f6");
  });

  it("grid:display=false ekseninin grid rengine dokunmaz", () => {
    const c = mockChart();
    charts.test = c;
    rethemeCharts();
    expect(c.options.scales.y1.grid.display).toBe(false);
    expect(c.options.scales.y1.grid.color).toBeUndefined();
  });

  it("light↔dark farklı renkler üretir (tema-duyarlı)", () => {
    document.documentElement.dataset.theme = "light";
    const lightTick = chartTick();
    document.documentElement.dataset.theme = "dark";
    const darkTick = chartTick();
    expect(lightTick).not.toBe(darkTick);
  });
});
