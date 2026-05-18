/**
 * SFDAP Türkiye Haritası — Leaflet bağımlı modül.
 *
 * Cycle 9 prep batch'inde `frontend/src/main.js`'ten extract edildi.
 * Bağımlılıklar:
 *   - `window.L` (Leaflet 1.9.4 CDN; index.html'de main.js'ten önce yüklenir)
 *   - `api()` (entry-point'ten parametre olarak alınır → cycle import yok)
 *
 * Public API:
 *   loadMap({ api, regionColors? })  — sayfa render entry-point
 *   REGION_COLORS                    — 7 bölge → hex (legend ile uyumlu)
 *
 * Test edilebilirlik:
 *   regionColors injectable → unit test'te custom palette geçilebilir.
 *   api function injectable → fetch mock'lanabilir.
 *   _farmMarker / _farmPopupHtml / _escapeHtml export edildi (test için).
 */

// 7 coğrafi bölge → hex renk. Legend (`frontend/index.html` #mapLegend)
// ile birebir uyumlu olmak zorunda — değiştirirsen orayı da güncelle.
export const REGION_COLORS = {
  Marmara: "#4A90E2",
  Ege: "#7ED321",
  Akdeniz: "#F5A623",
  "İç Anadolu": "#BD10E0",
  Karadeniz: "#50E3C2",
  "Doğu Anadolu": "#D0021B",
  "Güneydoğu Anadolu": "#F8E71C",
};
export const DEFAULT_REGION_COLOR = "#94a3b8"; // bilinmeyen bölge — slate-400

// Türkiye merkezi yaklaşık koordinat. Zoom alt/üst sınırı YOK — kullanıcı
// dünya görünümüne ya da sokak detayına serbestçe inip çıkabilir.
export const TURKEY_CENTER = [39.0, 35.0];
export const TURKEY_ZOOM = 6;

// Trackpad inertia 1-2 saniye sürer ve 30+ wheel event ateşler.
// `wheelDebounceTime` debounce'u tek event'a indirgemiyor; bu cooldown
// yaklaşımı bir wheel = 1 zoom step + 250ms aralık. Detaylı root-cause
// için `8ff0234` commit'ine bak.
const ZOOM_COOLDOWN_MS = 250;

// Singleton state — sayfa her ziyaret edildiğinde map yeniden init
// olmasın diye saklanır.
let _mapInstance = null;
let _mapMarkersLayer = null;

/**
 * XSS koruması — Leaflet popup HTML üretmeden önce string sanitize.
 */
export function _escapeHtml(s) {
  if (s == null) return "";
  return String(s).replace(/[&<>"']/g, (c) =>
    ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    })[c],
  );
}

/**
 * Tek çiftliğin popup HTML'i — name + city/region + alan + ID.
 * String döndürür; Leaflet `bindPopup()` HTML olarak kullanır.
 */
export function _farmPopupHtml(farm) {
  const area = farm.area_hectares != null ? `${farm.area_hectares.toFixed(1)} ha` : "—";
  return `
        <div>
            <strong>${_escapeHtml(farm.name)}</strong><br>
            <span style="color:#64748b;">${_escapeHtml(farm.city || "")} · ${_escapeHtml(farm.region || "")}</span><br>
            <small>Alan: ${area}</small><br>
            <small>ID: #${farm.id}</small>
        </div>
    `;
}

/**
 * `L.circleMarker` options'ı — region renk + WCAG kontrast outline.
 * Test edilebilir: input `farm` + `regionColors`, output options object.
 */
export function _markerOptions(farm, regionColors = REGION_COLORS) {
  const color = regionColors[farm.region] || DEFAULT_REGION_COLOR;
  return {
    radius: 7,
    fillColor: color,
    color: "#1f2937",
    weight: 1.5,
    opacity: 0.9,
    fillOpacity: 0.85,
  };
}

function _ensureMapInstance() {
  if (_mapInstance) {
    requestAnimationFrame(() => _mapInstance.invalidateSize());
    return _mapInstance;
  }
  if (typeof L === "undefined") {
    console.warn("Leaflet (window.L) henüz yüklenmedi; loadMap ertelendi.");
    return null;
  }
  _mapInstance = L.map("mapContainer", {
    zoomControl: true,
    zoomSnap: 1,
    zoomDelta: 1,
    scrollWheelZoom: false, // custom handler aşağıda
  }).setView(TURKEY_CENTER, TURKEY_ZOOM);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> katkıda bulunanlar',
    maxZoom: 19,
  }).addTo(_mapInstance);
  _mapMarkersLayer = L.layerGroup().addTo(_mapInstance);

  // Custom throttled wheel zoom (trackpad fix — 8ff0234)
  let _lastWheelZoomAt = 0;
  _mapInstance.getContainer().addEventListener(
    "wheel",
    (e) => {
      e.preventDefault();
      const now = Date.now();
      if (now - _lastWheelZoomAt < ZOOM_COOLDOWN_MS) return;
      _lastWheelZoomAt = now;
      const direction = e.deltaY > 0 ? -1 : 1;
      const point = _mapInstance.mouseEventToContainerPoint(e);
      _mapInstance.setZoomAround(point, _mapInstance.getZoom() + direction);
    },
    { passive: false },
  );

  return _mapInstance;
}

/**
 * Page render entry-point. `api` parametre olarak alınır → ESM cycle
 * import'unu önler, ayrıca test'te mock'lanabilir.
 *
 * @param {object} opts
 * @param {function} opts.api  — `api(endpoint)` fetch wrapper
 * @param {object}  [opts.regionColors] — özel palette (test için)
 */
export async function loadMap({ api, regionColors = REGION_COLORS } = {}) {
  const status = document.getElementById("mapStatus");
  const container = document.getElementById("mapContainer");
  container.setAttribute("aria-busy", "true");
  if (status) status.textContent = "Çiftlikler yükleniyor…";

  const map = _ensureMapInstance();
  if (!map) {
    if (status) status.textContent = "⚠️ Harita kütüphanesi yüklenemedi (Leaflet). Sayfayı yenileyin.";
    container.setAttribute("aria-busy", "false");
    return;
  }

  const farms = await api("/api/farms/?limit=500");
  if (!farms || !Array.isArray(farms)) {
    if (status) status.textContent = "⚠️ Çiftlik verisi alınamadı (API offline?).";
    container.setAttribute("aria-busy", "false");
    return;
  }

  _mapMarkersLayer.clearLayers();

  let plotted = 0;
  let skipped = 0;
  farms.forEach((farm) => {
    if (farm.location_lat == null || farm.location_lng == null) {
      skipped++;
      return;
    }
    const marker = L.circleMarker(
      [farm.location_lat, farm.location_lng],
      _markerOptions(farm, regionColors),
    );
    marker.bindPopup(_farmPopupHtml(farm));
    marker.bindTooltip(`${farm.name} (${farm.city || ""})`, {
      direction: "top",
      opacity: 0.9,
    });
    marker.addTo(_mapMarkersLayer);
    plotted++;
  });

  container.setAttribute("aria-busy", "false");
  if (status) {
    status.textContent =
      `🌍 ${plotted} çiftlik haritada gösteriliyor` +
      (skipped > 0 ? ` · ${skipped} çiftlik koordinat eksikliği nedeniyle atlandı.` : ".");
  }
}
