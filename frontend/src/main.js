/* ============================================================
   SFDAP Dashboard — Entry Point
   ============================================================
   B-batch (Cycle 9): ES module entry-point. Reusable helpers
   `src/lib/` altına ayrıldı, drift TODO kapandı.

   Bu dosya `<script type="module">` ile yüklenir. Inline `onclick`
   handler'lar `window` global'ine ihtiyaç duyar — dosyanın sonunda
   tüm public function'lar `window.X = X` ile expose edilir
   (window-bridge bölümü).
   ============================================================ */

import { _skeletonBlock, _skeletonCards, _skeletonRows, _setBusy } from "./lib/skeleton.js";
import { loadMap as _loadMapImpl } from "./lib/map.js";
import {
    clearAllErrors as _clearAllErrors,
    clearFieldError as _clearFieldError,
    extractErrorMessage as _extractErrorMessage,
    setFieldError as _setFieldError,
    fmtDate as _fmtDate,
    fmtNumber as _fmtNumber,
    escAttr as _escAttr,
    pageTitles,
} from "./lib/ui_helpers.js";
import { api, apiAuth, API_BASE, getAuthToken, setAuthToken, clearAuthToken } from "./lib/api.js";
import { setupEventDelegation } from "./lib/events.js";
import {
    currentUser, ROLE_LABELS, getCurrentUser, refreshAuthState, _renderUserBadge, _applyRoleVisibility, _applyAuthGate,
    toggleLandingForm, doLogin, doRegister, doChangePassword, doLogout
} from "./lib/auth.js";
import { loadDashboard, loadDemoData } from "./lib/dashboard.js";
import {
    loadFields, toggleForm, submitNewFarm, submitNewField, editFarm, deleteFarm,
    editField, deleteField, submitNewSensor, deleteSensor, openFieldDetail, analyzeFieldLeaf
} from "./lib/fields.js";
import { loadSensors, loadSensorDetail } from "./lib/sensors.js";
import { loadWeather } from "./lib/weather.js";
import { loadIrrigation, predictIrrigation, approveIrrigation, updateIrrigationStatus, addFieldIrrigation } from "./lib/irrigation.js";
import { recommendFertilizer, fertilizerSchedule } from "./lib/fertilizer.js";
import { loadAnalytics } from "./lib/analytics.js";
import { loadPlants, analyzePlantImage } from "./lib/plants.js";
import { loadAlerts, resolveAlert, runAlertCheck } from "./lib/alerts.js";
import { loadUsers, createUser, changeUserRole, resetUserPassword, deleteUser } from "./lib/users.js";
import { doLogin, doRegister, doLogout, doChangePassword, toggleLandingForm, refreshAuthState, currentUser } from "./lib/auth.js";

let refreshInterval = null;
let charts = {};
let apiOnline = false;

// ─── EVENTS & LISTENERS ───────────────────────────────────────
window.addEventListener('auth-expired', () => {
    showToast('Oturum süresi doldu, tekrar giriş yap', 'warning');
});
window.addEventListener('auth-forbidden', (e) => {
    const msg = e.detail;
    showToast(msg.startsWith('HTTP ') ? 'Bu işlem için yetkin yok' : msg, 'warning');
});
window.addEventListener('api-error', (e) => {
    showToast(e.detail, 'error');
});
window.addEventListener('toast', (e) => {
    showToast(e.detail.msg, e.detail.type);
});
window.addEventListener('navigate', (e) => {
    navigate(e.detail);
});
window.addEventListener('auth-status-changed', (e) => {
    if (e.detail) {
        refreshBell();
    } else {
        _hideBell();
    }
});
window.addEventListener('status-update', (e) => {
    updateStatus(e.detail.online);
});
window.addEventListener('auth-refresh-needed', () => {
    refreshAuthState();
});
window.addEventListener('hideBell', () => {
    _hideBell();
});
window.addEventListener('toggle-form', (e) => {
    toggleForm(e.detail);
});

// ─── NAVIGATION ───────────────────────────────────────────────

function navigate(page) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(n => {
        n.classList.remove('active');
        // Drop aria-current from inactive nav items.
        n.removeAttribute('aria-current');
    });
    document.getElementById(`page-${page}`).classList.add('active');
    const navItem = document.querySelector(`[href="#${page}"]`);
    if (navItem) {
        navItem.classList.add('active');
        navItem.setAttribute('aria-current', 'page');
    }
    document.getElementById('pageTitle').textContent = pageTitles[page][0];
    document.getElementById('pageSubtitle').textContent = pageTitles[page][1];
    // Focus the <main> programmatically (tabindex=-1) so keyboard users
    // hear the page change via the screen reader.
    const main = document.getElementById('main-content');
    if (main) main.focus({ preventScroll: false });
    // Load page data
    if (page === 'dashboard') loadDashboard();
    else if (page === 'fields') loadFields();
    else if (page === 'sensors') loadSensors();
    else if (page === 'weather') loadWeather();
    else if (page === 'irrigation') loadIrrigation();
    else if (page === 'analytics') loadAnalytics();
    else if (page === 'map') loadMap();
    else if (page === 'plants') loadPlants();
    else if (page === 'alerts') loadAlerts();
    else if (page === 'users') loadUsers();
    else if (page === 'auth') refreshAuthState();
    // 'field-detail' navigate() ile değil openFieldDetail(id) ile yüklenir.
    // Hero subtitle dinamik Filiz tipi (Item 8a) — farmer-anlamlı 8 sayfada
    // sayfa-açıklamasını Filiz havuzundan rastgele tiple değiştirir + 20sn'de refresh.
    _startHeroTipRotation(page);
    // Close sidebar on mobile (a11y: hamburger aria-expanded sync)
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.remove('open');
    const hamburger = document.querySelector('.hamburger');
    if (hamburger) hamburger.setAttribute('aria-expanded', 'false');
}

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const isOpen = sidebar.classList.toggle('open');
    // Keep aria-expanded in sync with the visual sidebar state.
    const hamburger = document.querySelector('.hamburger');
    if (hamburger) hamburger.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
}

window.addEventListener('hashchange', () => {
    const raw = location.hash.slice(1) || 'dashboard';
    // Parametrik route: #field/{id} → tarla detayı
    if (raw.startsWith('field/')) {
        const id = parseInt(raw.split('/')[1], 10);
        if (Number.isFinite(id)) openFieldDetail(id);
        return;
    }
    if (pageTitles[raw]) navigate(raw);
});

// ─── MAP (TÜRKİYE HARİTASI) ───────────────────────────────────
// Asıl logic `frontend/src/lib/map.js`'te (B-batch refactor).
// Burada wrapper: navigate() bunu çağırır, lib `api` parametresini alır.
async function loadMap() {
    return _loadMapImpl({ api });
}

// ─── BİLDİRİM ÇANI (REBUILD Faz 5) ────────────────────────────
function _hideBell() {
    const wrap = document.getElementById('notifWrap');
    if (wrap) wrap.style.display = 'none';
    const dd = document.getElementById('notifDropdown');
    if (dd) dd.style.display = 'none';
}

/** Açık uyarıları çek, çan sayısını + dropdown listesini güncelle. */
async function refreshBell() {
    const wrap = document.getElementById('notifWrap');
    if (!wrap) return;
    wrap.style.display = 'inline-flex';
    const alerts = await apiAuth('/api/alerts/?is_resolved=false&limit=20');
    const countEl = document.getElementById('notifCount');
    const listEl = document.getElementById('notifList');
    const open = alerts || [];
    if (countEl) {
        countEl.textContent = open.length > 9 ? '9+' : String(open.length);
        countEl.style.display = open.length > 0 ? 'inline-flex' : 'none';
    }
    document.getElementById('notifBell')?.classList.toggle('has-unread', open.length > 0);
    if (listEl) {
        listEl.innerHTML = open.length === 0
            ? '<div class="notif-empty">Açık uyarı yok ✅</div>'
            : open.slice(0, 10).map(a => `
                <div class="notif-item severity-${_escAttr(a.severity)}">
                    <div class="notif-item-msg">${_escAttr(a.message)}</div>
                    <div class="notif-item-foot">
                        <span class="notif-item-sev">${_escAttr(a.severity)}</span>
                        <button class="btn-mini" data-action="resolveFromBell" data-id="${a.id}">Çöz</button>
                    </div>
                </div>`).join('');
    }
}

function toggleBell() {
    const dd = document.getElementById('notifDropdown');
    const bell = document.getElementById('notifBell');
    if (!dd) return;
    const open = dd.style.display !== 'none' && dd.style.display !== '';
    dd.style.display = open ? 'none' : 'block';
    if (bell) bell.setAttribute('aria-expanded', open ? 'false' : 'true');
    if (!open) refreshBell();  // açarken tazele
}

/** "Kontrol et" — tarlaları tara, uyarı üret, çanı tazele. */
async function runAlertCheck() {
    const res = await apiAuth('/api/alerts/check', { method: 'POST' });
    if (res) {
        showToast(res.created > 0 ? `${res.created} yeni uyarı üretildi` : 'Yeni uyarı yok ✅', res.created > 0 ? 'warning' : 'success');
        refreshBell();
    }
}

/** Çan dropdown'ından uyarı çöz. */
async function resolveFromBell(alertId) {
    const res = await apiAuth(`/api/alerts/${alertId}`, { method: 'PATCH', body: JSON.stringify({ is_resolved: true }) });
    if (res) { showToast('Uyarı çözüldü', 'success'); refreshBell(); }
}

// Dropdown dışına tıklayınca kapat
document.addEventListener('click', (e) => {
    const wrap = document.getElementById('notifWrap');
    const dd = document.getElementById('notifDropdown');
    if (wrap && dd && !wrap.contains(e.target) && dd.style.display === 'block') {
        dd.style.display = 'none';
        document.getElementById('notifBell')?.setAttribute('aria-expanded', 'false');
    }
});

// _setFieldError / _clearFieldError / _clearAllErrors → src/lib/ui_helpers.js olarak
// import edildi (yukarıdaki import bloğu). Tek kaynak artık ui_helpers.js.

// ─── STATUS & UTILITIES ───────────────────────────────────────
function updateStatus(online) {
    const dot = document.getElementById('statusDot');
    const text = document.getElementById('statusText');
    dot.className = `status-dot ${online ? 'online' : 'offline'}`;
    text.textContent = online ? 'Sistem Aktif' : 'Bağlantı Yok';
}

function showToast(message, type = 'info', duration = 3500) {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    const icon = type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️';
    toast.innerHTML = `
        <span class="toast-icon">${icon}</span>
        <span class="toast-message">${message}</span>
        <button class="toast-close" aria-label="Kapat" title="Kapat">×</button>
    `;
    container.appendChild(toast);

    let timer = null;
    const dismiss = () => {
        clearTimeout(timer);
        toast.classList.add('hide');
        setTimeout(() => toast.remove(), 250);
    };
    toast.querySelector('.toast-close').addEventListener('click', dismiss);
    if (duration > 0) timer = setTimeout(dismiss, duration);
}

function updateClock() {
    document.getElementById('clockDisplay').textContent = new Date().toLocaleTimeString('tr');
}

// ─── INIT ─────────────────────────────────────────────────────
async function init() {
    setupEventDelegation();
    registerActions({
        doLogin,
        doRegister,
        doLogout,
        doChangePassword,
        toggleLandingForm: (btn) => toggleLandingForm(btn.dataset.arg),
        toggleSidebar,
        toggleBell,
        runAlertCheck,
        sensorsPrev: () => typeof loadSensors === 'function' && loadSensors(typeof sensorsPage !== 'undefined' ? sensorsPage - 1 : 1),
        sensorsNext: () => typeof loadSensors === 'function' && loadSensors(typeof sensorsPage !== 'undefined' ? sensorsPage + 1 : 1),
        predictIrrigation: () => typeof predictIrrigation === 'function' && predictIrrigation(),
        irrigationPrev: () => typeof loadIrrigation === 'function' && loadIrrigation(typeof irrigationPage !== 'undefined' ? irrigationPage - 1 : 1),
        irrigationNext: () => typeof loadIrrigation === 'function' && loadIrrigation(typeof irrigationPage !== 'undefined' ? irrigationPage + 1 : 1),
        recommendFertilizer: () => typeof recommendFertilizer === 'function' && recommendFertilizer(),
        fertilizerSchedule: () => typeof fertilizerSchedule === 'function' && fertilizerSchedule(),
        analyzePlantImage: () => typeof analyzePlantImage === 'function' && analyzePlantImage(),
        createUser: () => typeof createUser === 'function' && createUser(),
        editFarm: (btn) => typeof editFarm === 'function' && editFarm(btn.dataset.id, btn.dataset.name),
        deleteFarm: (btn) => typeof deleteFarm === 'function' && deleteFarm(btn.dataset.id, btn.dataset.name),
        editField: (btn) => typeof editField === 'function' && editField(btn.dataset.id, btn.dataset.name),
        deleteField: (btn) => typeof deleteField === 'function' && deleteField(btn.dataset.id, btn.dataset.name),
        deleteSensor: (btn) => typeof deleteSensor === 'function' && deleteSensor(btn.dataset.id, btn.dataset.name),
        updateIrrigationStatus: (btn) => typeof updateIrrigationStatus === 'function' && updateIrrigationStatus(btn.dataset.id, btn.dataset.status),
        submitNewSensor: (btn) => typeof submitNewSensor === 'function' && submitNewSensor(btn.dataset.id),
        analyzeFieldLeaf: () => typeof analyzeFieldLeaf === 'function' && analyzeFieldLeaf(),
        addFieldIrrigation: (btn) => typeof addFieldIrrigation === 'function' && addFieldIrrigation(btn.dataset.id),
        loadSensorDetail: (btn) => typeof loadSensorDetail === 'function' && loadSensorDetail(btn.dataset.id),
        approveIrrigation: () => typeof approveIrrigation === 'function' && approveIrrigation(),
        resolveAlert: (btn) => typeof resolveAlert === 'function' && resolveAlert(btn.dataset.id),
        resolveFromBell: (btn) => typeof resolveFromBell === 'function' && resolveFromBell(btn.dataset.id),
        resetUserPassword: (btn) => typeof resetUserPassword === 'function' && resetUserPassword(btn.dataset.id, btn.dataset.name),
        deleteUser: (btn) => typeof deleteUser === 'function' && deleteUser(btn.dataset.id, btn.dataset.name),
        changeUserRole: (el) => typeof changeUserRole === 'function' && changeUserRole(el.dataset.id, el.value),
        openFieldDetail: (btn) => typeof openFieldDetail === 'function' && openFieldDetail(btn.dataset.id),
        submitNewFarm: () => typeof submitNewFarm === 'function' && submitNewFarm(),
        submitNewField: () => typeof submitNewField === 'function' && submitNewField(),
        toggleForm: (btn) => typeof toggleForm === 'function' && toggleForm(btn.dataset.arg),
        loadDemoData: () => loadDemoData(),
    });

    // Health check
    const health = await api('/api/health');
    apiOnline = health !== null;
    updateStatus(apiOnline);
    if (apiOnline) showToast('Sistem aktif — veriler güncel', 'success');
    else showToast('Bağlantı yok — son kayıtlı veriler gösteriliyor', 'error');

    // Auth state ilk yükleme — gate uygular (login yoksa landing, app gizli).
    await refreshAuthState();

    // REBUILD Faz 3.5: girişsizse hiçbir sayfaya navigate etme — landing kalır.
    // Giriş yapılınca doLogin() navigate('dashboard') çağırır.
    if (currentUser) {
        const raw = location.hash.slice(1) || 'dashboard';
        if (raw.startsWith('field/')) {
            const id = parseInt(raw.split('/')[1], 10);
            if (Number.isFinite(id)) openFieldDetail(id);
            else navigate('dashboard');
        } else if (pageTitles[raw]) {
            navigate(raw);
        } else {
            navigate('dashboard');
        }
    }

    // Auto-refresh every 30s
    refreshInterval = setInterval(() => {
        const activePage = document.querySelector('.page.active')?.id?.replace('page-', '');
        if (activePage === 'dashboard') loadDashboard();
    }, 30000);

    // Clock
    updateClock();
    setInterval(updateClock, 1000);

    // Hero sayılarına count-up animasyonu (sevimlilik pack)
    animateHeroStats();

    // Filiz maskotu
    initFiliz();

    // Tema (light/dark)
    initTheme();
}

/* ─── ✨ Sayı sayma animasyonu (count-up) ─────────────────── */
function animateCount(el, duration = 1400) {
    const target = parseInt((el.textContent || '0').replace(/[^\d]/g, ''), 10);
    if (!Number.isFinite(target) || target === 0) return;
    const start = performance.now();
    el.textContent = '0';
    const tick = (now) => {
        const t = Math.min(1, (now - start) / duration);
        const eased = 1 - Math.pow(1 - t, 3);   // easeOutCubic — soft sonlanma
        el.textContent = Math.round(target * eased).toLocaleString('tr-TR');
        if (t < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
}
function animateHeroStats() {
    ['heroFarms', 'heroSensors', 'heroReadings'].forEach(id => {
        const el = document.getElementById(id);
        if (el) animateCount(el);
    });
}

/* ─── 🌗 TEMA YÖNETİMİ ───────────────────────────────────── */
function initTheme() {
    const STORAGE_KEY = 'sfdap-theme';
    const root = document.documentElement;
    const btn = document.getElementById('themeToggle');
    if (!btn) return;

    // İlk tema: localStorage > sistem tercihi > dark default
    const stored = localStorage.getItem(STORAGE_KEY);
    const prefersLight = window.matchMedia?.('(prefers-color-scheme: light)').matches;
    const initial = stored || (prefersLight ? 'light' : 'dark');
    applyTheme(initial);

    btn.addEventListener('click', () => {
        const current = root.dataset.theme || 'dark';
        const next = current === 'light' ? 'dark' : 'light';
        applyTheme(next);
        localStorage.setItem(STORAGE_KEY, next);
        // Sayfa yeniden yüklenmiyor — toast bildirimi çıkmasın diye.
        // Chart.js renkleri mevcut sayfada eski temada kalır; sayfa değişince güncellenir.
    });

    function applyTheme(theme) {
        if (theme === 'light') {
            root.dataset.theme = 'light';
            btn.setAttribute('aria-label', 'Karanlık temaya geç');
            btn.setAttribute('title', 'Karanlık temaya geç');
        } else {
            delete root.dataset.theme;
            btn.setAttribute('aria-label', 'Aydınlık temaya geç');
            btn.setAttribute('title', 'Aydınlık temaya geç');
        }
    }
}

/* ─── 🌱 FİLİZ MASKOTU ─────────────────────────────────────── */

// Filiz farmer ipucu havuzu — sulama/gübre/ekim/hava/hastalık/hasat/sensör.
// (Item 8b: rol-aware havuzlar; overseer/admin/developer aşağıda; _getRoleTips
//  ile seçilir. Anonim/login-yok durumda farmer havuzu fallback olarak kullanılır.)
const FILIZ_TIPS_FARMER = [
    // ─── 💧 SULAMA ─────────────────────────────────────────────
    {msg: "Toprak nemi %30 altına düştüyse bitki susamış demektir, hemen su ver.", emoji: "💧"},
    {msg: "Akşamüstü veya sabah erken sulama yap — gündüz buharlaşma çok yüksek.", emoji: "🌅"},
    {msg: "Yapraklara değil toprağa su ver — ıslak yaprak hastalık çağırır.", emoji: "🍃"},
    {msg: "Damla sulama %30-50 daha az su tüketir, yatırımına kısa sürede değer.", emoji: "♻️"},
    {msg: "Yağmurdan sonra 1-2 gün sulama yapma — toprak zaten doymuştur.", emoji: "🌧️"},
    {msg: "Köklü bitkilere az ve derin sulama yap; sığ sulama kökü yüzeye çeker.", emoji: "🪴"},
    {msg: "Soğuk suyla sulama bitkiyi şoklar — su, hava sıcaklığına yakın olmalı.", emoji: "🥶"},
    {msg: "Tuzlu kuyu suyunu yağmur suyuyla seyret — toprağa zarar vermesin.", emoji: "🧂"},

    // ─── 🌱 GÜBRELEME & TOPRAK ────────────────────────────────
    {msg: "Gübrelemeden önce mutlaka pH ölç — 6.0-7.0 çoğu bitki için ideal.", emoji: "🧪"},
    {msg: "Aşırı azot bitkiyi tatlı meyve yerine bol yaprak yapmaya iter — dengeli kullan.", emoji: "⚖️"},
    {msg: "Çay asit toprak sever (pH 4.5-6.0), patates de hafif asitten hoşlanır.", emoji: "🍵"},
    {msg: "Hasat öncesi son gübrelemeyi 30 gün önce kes — meyve/tane sağlıklı olgunlaşsın.", emoji: "📅"},
    {msg: "Yaprakta sararma demir ya da magnezyum eksikliği işaretidir — yapraktan tatbik et.", emoji: "💛"},
    {msg: "Domates için potasyum, mısır için azot, buğday için fosfor öne çıkar.", emoji: "🍅"},
    {msg: "Toprak yorgunsa bir mevsim baklagil ek — fasulye, mercimek toprağa azot kazandırır.", emoji: "🌾"},
    {msg: "Kompost altın değerinde — mutfak atığını çürütüp toprağa kazandır.", emoji: "♻️"},
    {msg: "Hayvan gübresini taze kullanma, en az 6 ay olgunlaştır — kökü yakar.", emoji: "🐄"},
    {msg: "Sonbahar yaprakları toprağa kazandır — doğal organik madde, ücretsiz!", emoji: "🍂"},
    {msg: "Toprak iyi tutunmuyorsa kil az demektir — humus ekle, su tutma artsın.", emoji: "🟫"},

    // ─── 🌿 EKİM & ROTASYON ───────────────────────────────────
    {msg: "Aynı tarlaya üst üste aynı bitkiyi ekme — toprak yorulur, hastalık birikir.", emoji: "🔁"},
    {msg: "Soğan veya sarımsak ekersen yanına nane koy — zararlı böcekleri uzaklaştırır.", emoji: "🌿"},
    {msg: "Bal arıları olmadan tozlaşma yok — tarla kenarına çiçek bandı bırak, faydası büyük.", emoji: "🐝"},
    {msg: "Karadeniz'de fındık + çay, Akdeniz'de narenciye + domates en doğal seçim.", emoji: "🗺️"},
    {msg: "İç Anadolu'da buğday ve şeker pancarı kuraklığa daha dayanıklıdır.", emoji: "🌾"},
    {msg: "Domates ve fesleğen yan yana — ikisi de daha iyi büyür, lezzet artar.", emoji: "🍃"},
    {msg: "Mısır + fasulye + kabak (üç kız kardeş) yan yana — birbirini destekler.", emoji: "🌽"},
    {msg: "Tohum ekmeden önce çimlenme testi yap: 10 tohumdan kaçı çimleniyor?", emoji: "🌱"},
    {msg: "Fide dikiminde toprağı bastır ama ezme — kök hava da ister.", emoji: "👐"},

    // ─── 🌤️ HAVA & İKLİM ─────────────────────────────────────
    {msg: "Yağmur bekleniyorsa sulamayı bir gün ertele, su tasarrufu yapmış olursun.", emoji: "☔"},
    {msg: "Sıcaklık 30°C üstüne çıkarsa bitki stres altına girer — gölgelik ya da sulama düşün.", emoji: "🥵"},
    {msg: "Sabah don uyarısı varsa hassas bitkiler için tülbent ya da malçlama hayat kurtarır.", emoji: "❄️"},
    {msg: "Rüzgar sonrası ilaçlama yapma — etken madde uçar, paranı boşa harcarsın.", emoji: "💨"},
    {msg: "Dolu beklentisinde fide ve sera örtülerini güçlendir — kayıp büyük olabilir.", emoji: "🧊"},
    {msg: "Sabah çiyiyle yapraklarda mantar başlayabilir — erken saatlerde kontrole alış.", emoji: "🍄"},
    {msg: "Aşırı sıcak günlerde sera havalandırması şart — kapılar yarım açık dursun.", emoji: "🪟"},

    // ─── 🐛 HASTALIK & ZARARLI ────────────────────────────────
    {msg: "Yaprak alt yüzünde beyaz noktacıklar varsa beyaz sinek olabilir — sarı yapışkan tuzak kur.", emoji: "🪰"},
    {msg: "Külleme (mantar) çoğu sebzenin baş düşmanı — havalandırmayı arttır, sulamayı azalt.", emoji: "⚪"},
    {msg: "Salyangoz için tarla kenarına bira tuzağı kur — basit ama etkili.", emoji: "🍺"},
    {msg: "Birden fazla bitki ekersen tek tip zararlı tarlanın hepsini biçemez.", emoji: "🦗"},
    {msg: "Köstebek toprağı havalandırır ama köke zarar verirse koruma altına al.", emoji: "🐀"},

    // ─── 🌾 HASAT & SAKLAMA ───────────────────────────────────
    {msg: "Domatesi sap kısmı yarı yeşilken topla — sonra olgunlaşır, daha lezzetli.", emoji: "🍅"},
    {msg: "Buğdayı tane sertleşmeden hasat etme; saman tadı verir.", emoji: "🌾"},
    {msg: "Patates hasadı sonrası 2 hafta serin yerde dinlendir — kabuk sertleşir.", emoji: "🥔"},
    {msg: "Üzümü sabah kuru havada topla — daha uzun saklanır.", emoji: "🍇"},
    {msg: "Soğan ve sarımsak hasat sonrası 1 hafta gölgede kurutulmalı.", emoji: "🧄"},
    {msg: "Tohum saklamak için cam kavanoz kullan, kuru ve serin yerde tut.", emoji: "🥚"},

    // ─── ⚙️ SENSÖR & PRATİK ──────────────────────────────────
    {msg: "Sensörler 15-30 cm derinlikte ölçüm alır — bitki köklerinin olduğu yer.", emoji: "📏"},
    {msg: "Sensörü en kritik tarla bölgesine yerleştir — uzak köşeye değil.", emoji: "📍"},
    {msg: "Sensör verisi günlerdir gelmiyorsa pil bitmiş ya da bağlantı kopmuş olabilir.", emoji: "🔋"},
    {msg: "Toprak elektrik iletkenliği yüksekse tuzluluk var — sulama suyunu kontrol et.", emoji: "⚡"},
    {msg: "Yaz aylarında toprağı malçla — nem korunur, yabani ot azalır, sulama azalır.", emoji: "🟫"},

    // ─── 💰 EKONOMİ & PLANLAMA ────────────────────────────────
    {msg: "Hasat tahminini önceden yap — pazar fiyatı dalgalanmasında kazançlı çık.", emoji: "📈"},
    {msg: "Tarım sigortası don ve doluya karşı koruma sağlar; başvuruyu erken yap.", emoji: "🛡️"},
    {msg: "Kooperatife üye olmak girdi maliyetini düşürür ve toplu satış imkanı verir.", emoji: "🤝"},
    {msg: "Bu yıl iyi giden bitkiyi defterine yaz — gelecek yıl plana ışık tutar.", emoji: "📓"},

    // ─── 🤗 FİLİZ KARAKTER ───────────────────────────────────
    {msg: "Selam çiftçi! Bugün de toprağın bereketli olsun.", emoji: "🌾"},
    {msg: "Bana tıklamayı unutma, hep yeni bir şey biliyorum!", emoji: "✨"},
    {msg: "Sağ üstten karanlık/aydınlık temayı değiştirebilirsin, gözlerim hep takip eder.", emoji: "🌗"},
    {msg: "Ben uyumayı severim ama gece gelip beni dürtersen sinirlenirim! Uyku 00:00-05:00 arası.", emoji: "😴"},
    {msg: "Yağmuru duyduğumda yapraklarım titrer — sevimli bir tepki vermiş oluyorum 💧", emoji: "🌧️"},
    {msg: "Filizden hasada uzun bir yol var, sabırlı ol — ben de yavaş yavaş büyüyorum.", emoji: "🌱"},
];

/* Filiz overseer havuzu — gözetmen rolüne odaklı sistem-özeti ipuçları. */
const FILIZ_TIPS_OVERSEER = [
    {msg: "Bölge bazlı analytics'te çiftlik dağılımını ısı haritasıyla gör.", emoji: "🗺️"},
    {msg: "Kritik uyarılar üstte; resolved işaretledikçe arşivlenir.", emoji: "🚨"},
    {msg: "Sistemde aktif çiftlik sayısı dashboard hero alanında her dakika tazelenir.", emoji: "📊"},
    {msg: "Hava verisi tüm bölgelerden günlük çekilir; eksik bölgeyi kontrol panelinde gör.", emoji: "🌦️"},
    {msg: "PDF/Excel dışa aktarımı Raporlar sayfasında — yöneticilere haftalık özet için ideal.", emoji: "📄"},
    {msg: "Model performansını ModelPerformanceLog endpoint'inde takip et — drift erken yakalan.", emoji: "🤖"},
    {msg: "Sensör hattındaki kopukluk önce uyarılarda görünür, sonra Analytics'te düşer.", emoji: "📡"},
    {msg: "Tüm çiftliklerin koordinatları haritada; tıkla, detay açılır.", emoji: "📍"},
    {msg: "Raporlar > Karşılaştırma sekmesinde iki dönemi yan yana koy, trend net görünür.", emoji: "📈"},
    {msg: "Bölge bazlı bitki dağılımı için Analytics > Dağılımlar bölümüne göz at.", emoji: "🌾"},
    {msg: "Sulama onay akışı: farmer talep eder, gözetmen olarak gözlemleyebilirsin.", emoji: "💧"},
    {msg: "Kritik uyarı seviyesi anomali eşiği aşıldığında otomatik tetiklenir.", emoji: "⚠️"},
    {msg: "7 bölge dağılımı: pasta grafiği sana hızlı manzara verir.", emoji: "🍩"},
    {msg: "Senin görevin gözlem ve analiz — değişiklikler yöneticilere bırakılır.", emoji: "👀"},
    {msg: "Bitki sağlığı modeli sonuçlarını Analytics > Tahminler sekmesinde görebilirsin.", emoji: "🌿"},
    {msg: "Çiftlik konsolidasyonu için Analytics > Bölge Tablosu çıktısı en yararlısı.", emoji: "📋"},
];

/* Filiz admin havuzu — yönetici rolüne odaklı kullanıcı/güvenlik ipuçları. */
const FILIZ_TIPS_ADMIN = [
    {msg: "Yeni kullanıcı oluştururken rol seçimi sonra değiştirilemez, dikkat et.", emoji: "👤"},
    {msg: "Çiftliği olan kullanıcı silinemez — önce çiftlikleri devret veya temizle.", emoji: "🚫"},
    {msg: "Şifre sıfırlama log'ları audit_log'da; düzenli kontrol et.", emoji: "🔐"},
    {msg: "Admin kendini silemez — sistem korur.", emoji: "🛡️"},
    {msg: "RBAC her endpoint'te aktif; bypass denemesini izle.", emoji: "🚨"},
    {msg: "Kullanıcı listesi filtrelenebilir: rol bazında daralt.", emoji: "🔍"},
    {msg: "Bcrypt cost factor şu an 12; üretimde 14'e çıkarman tavsiye edilir.", emoji: "🔒"},
    {msg: "Yeni admin oluştururken iki kez düşün — yetkisi tamamen serbesttir.", emoji: "⚖️"},
    {msg: "Sistem sağlık endpoint'i /api/health: nabız atışı için cron'a bağla.", emoji: "💓"},
    {msg: "Veritabanı yedeği dışa aktar — alembic migration'ları kapsamalı.", emoji: "💾"},
    {msg: "JWT token süresi 24 saat; settings'de TOKEN_EXPIRE_HOURS ile değiştir.", emoji: "🎟️"},
    {msg: "Roller: farmer (sahibi), developer (teknik), overseer (read-only), admin (full).", emoji: "👥"},
    {msg: "Rate limit aşıldığında 429 döner; abuse durumunda IP banla.", emoji: "🚦"},
    {msg: "Audit log'da kim ne yaptı, ne zaman — şüpheli aktiviteyi araştır.", emoji: "📜"},
    {msg: "Bandit + ruff CI'da çalışır — pre-commit hook'la yerel taramayı da koş.", emoji: "🧰"},
    {msg: "'Demo Yükle' onboarding seçeneği yeni kullanıcılar için; admin'e yaramaz.", emoji: "🌱"},
];

/* Filiz developer havuzu — geliştirici rolüne odaklı API/debug/workflow ipuçları. */
const FILIZ_TIPS_DEVELOPER = [
    {msg: "/docs altında Swagger var; tüm endpoint'leri canlı test edebilirsin.", emoji: "📚"},
    {msg: "X-API-Key header'ı dev endpoint'leri için — credentials'tan al.", emoji: "🗝️"},
    {msg: "pytest -k 'test_X' ile filtreli koş; tüm suite'i her seferinde çalıştırma.", emoji: "🧪"},
    {msg: "alembic upgrade head ile migration'ları uygula; head'i kaçırma.", emoji: "🗃️"},
    {msg: "FastAPI Depends ile auth/db session inject — DRY için kullan.", emoji: "💉"},
    {msg: "SQLAlchemy lazy loading N+1 yaratabilir — joinedload/selectinload ekle.", emoji: "🔗"},
    {msg: "Pydantic v2'de model_dump() var, dict() değil; legacy kodu güncelle.", emoji: "📦"},
    {msg: "Frontend src/main.js vanilla — modül scope global'i window-bridge ile expose.", emoji: "🌐"},
    {msg: "vitest jsdom ile DOM mock'lar; test'i frontend/tests altında tut.", emoji: "🃏"},
    {msg: "ruff format daha hızlı, black uyumlu; pre-commit'e ekle.", emoji: "⚡"},
    {msg: "GitHub Actions CI .github/workflows altında; matrix Python 3.11/3.12.", emoji: "🤖"},
    {msg: "API_BASE_URL env'den gelir; lokal dev için .env.local kullan.", emoji: "🔧"},
    {msg: "Pre-commit hooks: trim whitespace, ruff, bandit — her commit'i denetler.", emoji: "🪝"},
    {msg: "Bug bulduğunda issue aç, branch fix/X ile çalış, PR --web ile gönder.", emoji: "🔬"},
    {msg: "Logger seviyeleri: DEBUG > INFO > WARN > ERROR — settings'de set et.", emoji: "📋"},
    {msg: "Code review öncesi self-review yap; diff'i kendin oku.", emoji: "🤝"},
];

/* Rol → havuz seçici. Anonim/bilinmeyen rol farmer'a düşer. */
function _getRoleTips(role) {
    switch (role) {
        case 'overseer':  return FILIZ_TIPS_OVERSEER;
        case 'admin':     return FILIZ_TIPS_ADMIN;
        case 'developer': return FILIZ_TIPS_DEVELOPER;
        default:          return FILIZ_TIPS_FARMER;  // farmer + anonim fallback
    }
}

/* ─── Hero subtitle dinamik Filiz tipi (Item 8a) ─────────────────────────
 * 8 farmer-anlamlı sayfada hero banner'ın altındaki `<p class="hero-filiz-tip">`
 * sayfa-açıklaması yerine rol-aware Filiz havuzundan (Item 8b _getRoleTips)
 * rastgele tip yansıtır. Sayfa
 * açılışında değişir + 20sn'de bir refresh. Yönetim sayfalarına (kullanıcılar,
 * hesabım, analytics, harita, çiftlik-detayı) dokunulmaz; orada mevcut açıklama
 * statik kalır (bu sayfalarda `<p>`'ye `.hero-filiz-tip` class'ı yok). */
const _HERO_TIP_PAGES = new Set([
    'dashboard', 'fields', 'sensors', 'weather',
    'irrigation', 'fertilizer', 'plants', 'alerts',
]);
const _HERO_TIP_REFRESH_MS = 20000;
let _heroTipInterval = null;

function _pickHeroTip() {
    // Item 8b: rol-aware — currentUser.role'a göre uygun havuzdan çek.
    // farmer-anlamlı sayfalarda admin/overseer/dev kendi havuzunu kullanır.
    const tips = _getRoleTips(currentUser?.role);
    const tip = tips[Math.floor(Math.random() * tips.length)];
    return `${tip.emoji} ${tip.msg}`;
}

function _applyHeroTip(pageId) {
    if (!_HERO_TIP_PAGES.has(pageId)) return;
    const p = document.querySelector(`p.hero-filiz-tip[data-page="${pageId}"]`);
    if (!p) return;
    // Fade out → değiştir → fade in (smooth geçiş)
    p.classList.add('fading');
    setTimeout(() => {
        p.textContent = _pickHeroTip();
        p.classList.remove('fading');
    }, 350);  // CSS transition süresiyle eşle
}

function _startHeroTipRotation(pageId) {
    // Eski interval'ı temizle (sayfa değişimi)
    if (_heroTipInterval) {
        clearInterval(_heroTipInterval);
        _heroTipInterval = null;
    }
    if (!_HERO_TIP_PAGES.has(pageId)) return;
    // İlk yansıma — fade animasyonu olmadan anında değiştir (sayfa girişinde
    // hemen Filiz tipini göster, sayfa-açıklamasını birkaç saniye okutma).
    const p = document.querySelector(`p.hero-filiz-tip[data-page="${pageId}"]`);
    if (p) p.textContent = _pickHeroTip();
    // Periyodik yenileme (fade'li)
    _heroTipInterval = setInterval(() => _applyHeroTip(pageId), _HERO_TIP_REFRESH_MS);
}

/* Filiz selamlamaları — rol + saate göre seçilir (Item 8b).
 * Anonim/bilinmeyen rol farmer'a düşer. Mood 'sleepy' (00-05) saat dilimini
 * override eder. Eski FILIZ_GREETINGS_{MORNING,NOON,EVENING,SLEEPY} ve
 * (kullanılmayan) WORRIED bu objeye taşındı. */
const FILIZ_GREETINGS = {
    farmer: {
        morning: ["Günaydın 🌅", "Erken başlayan kazanır ☀️", "İyi sabahlar 🐓", "Tarla seni bekliyor 🌱"],
        noon:    ["İyi günler 🌞", "Bereketli öğleden sonra 🌾", "Tarla nasıl bugün?", "Şu güneşe bak ☀️"],
        evening: ["İyi akşamlar 🌇", "Hava serinliyor 🌙", "Akşamın hayrına 🌒", "Bugün de bereketli geçti mi?"],
        sleepy:  ["Mhmm... 😴", "Geç oldu... zzz", "Uykum geldi 🌙", "Sen de uyu artık 🛏️"],
    },
    overseer: {
        morning: ["Günaydın gözetmen 📋", "Sistem nabzı nasıl? 📊", "İyi sabahlar 👀", "Sabahın hayrına 🌅"],
        noon:    ["İyi günler gözetmen 📋", "Sistemde sakin mi? 🔍", "Raporlar bekliyor 📈"],
        evening: ["İyi akşamlar gözetmen 🌇", "Günün özeti hazır mı? 📜", "Hayırlı akşamlar 🌙"],
        sleepy:  ["Sistem uyandığında bakalım 😴", "Mhmm... 🌙", "Geç oldu gözetmen 🛏️"],
    },
    admin: {
        morning: ["Günaydın admin 🛡️", "Sistemi açıyoruz 🔑", "İyi sabahlar yönetici 🌅"],
        noon:    ["İyi günler admin 🛡️", "Sistem güvende mi? 🔐", "Konsol seni bekliyor 💻"],
        evening: ["İyi akşamlar admin 🌇", "Günün audit raporu? 📜", "Hayırlı akşamlar 🌙"],
        sleepy:  ["Sistem boş mu? Uyu 🌙", "Mhmm... 😴", "Bile bile uyuyamazsın admin 🛏️"],
    },
    developer: {
        morning: ["Günaydın developer ⌨️", "Coffee + commits ☕", "İyi sabahlar 🌅"],
        noon:    ["İyi günler developer 💻", "Bugs found? 🐛", "Tests green? 🟢"],
        evening: ["İyi akşamlar 🌇", "Last commit zamanı 📦", "Wrap-up 🌙"],
        sleepy:  ["git commit -m 'sleeping' 😴", "Uyu, tests sabah var 🛏️", "Geç oldu... zzz"],
    },
};

function pickFilizGreetings() {
    const role = (currentUser?.role && FILIZ_GREETINGS[currentUser.role]) ? currentUser.role : 'farmer';
    const set = FILIZ_GREETINGS[role];
    if (filizMood === 'sleepy') return set.sleepy;
    const h = new Date().getHours();
    if (h >= 5 && h < 12)  return set.morning;
    if (h >= 12 && h < 18) return set.noon;
    return set.evening;  // 18-23 (00-04 mood=sleepy ile yakalanıyor)
}

let filizMood = 'happy';        // 'happy' | 'worried' | 'sleepy'
let filizCriticalAlerts = [];

function setFilizMood(mood) {
    filizMood = mood;
    const mascot = document.getElementById('filizMascot');
    if (!mascot) return;
    mascot.dataset.mood = mood;
    // Ağız değişimi
    mascot.querySelectorAll('.mouth-happy, .mouth-worried, .mouth-sleepy').forEach(el => el.style.display = 'none');
    mascot.querySelectorAll(`.mouth-${mood}`).forEach(el => el.style.display = '');
    // Z'ler ve ter damlası
    const zzz = mascot.querySelector('.filiz-zzz');
    const sweat = mascot.querySelector('.filiz-sweat');
    if (zzz) zzz.style.display = mood === 'sleepy' ? '' : 'none';
    if (sweat) sweat.style.display = mood === 'worried' ? '' : 'none';
}

function initFiliz() {
    const mascot = document.getElementById('filizMascot');
    const bubble = document.getElementById('filizBubble');
    const messageEl = document.getElementById('filizMessage');
    const tipEl = document.getElementById('filizTip');
    if (!mascot || !bubble) return;

    let bubbleVisible = false;
    let hideTimer = null;

    const showCustomMessage = (greeting, msg, tip = 'Tıklayarak başka bir ipucu al ✨', autoCloseMs = 8000) => {
        messageEl.innerHTML = `<div style="margin-bottom:6px;font-weight:500;">${greeting}</div>${msg}`;
        tipEl.textContent = tip;
        bubble.classList.add('show');
        bubbleVisible = true;
        clearTimeout(hideTimer);
        if (autoCloseMs > 0) {
            hideTimer = setTimeout(() => {
                bubble.classList.remove('show');
                bubbleVisible = false;
            }, autoCloseMs);
        }
    };

    /**
     * v6-1 (Item 8b binding): Farmer için critical alert varsa Filiz mesajına
     * yansıt — ölü kodu canlandır (`filizCriticalAlerts` zaten 60sn'de bir
     * çekiliyor ama mevcut bubble random tip gösteriyordu).
     *
     * Strateji: %50 olasılıkla critical alert mesajı, %50 normal random tip
     * (farmer'ı sürekli alertle bombalamamak için). Sleepy mood'da alert
     * görmezden gelinir — gece kullanıcıyı strese sokma.
     *
     * Sadece farmer için aktif: admin/overseer/developer kendi alert UI'larına
     * (header çanı, /api/alerts sayfası) sahip; mascot farmer'ın "sahada
     * çağırıcı sesi" rolünde.
     */
    const pickCriticalIfAny = () => {
        if (currentUser?.role !== 'farmer') return null;
        if (filizMood === 'sleepy') return null;
        if (!filizCriticalAlerts || filizCriticalAlerts.length === 0) return null;
        if (Math.random() > 0.5) return null;  // %50 — kullanıcıyı bombalamayı önle
        const alert = filizCriticalAlerts[0];  // API en yeni first dönüyor
        if (!alert || !alert.message) return null;
        return {
            greeting: 'Aa, dikkat! 😟',
            msg: `🚨 ${alert.message}`,
            tip: 'Uyarılar sayfasından detayı gör →',
        };
    };

    const pickTip = () => {
        // v6-1: Critical alert varsa öncelik tanı (farmer için, %50 olasılıkla)
        const critical = pickCriticalIfAny();
        if (critical) return critical;
        // Item 8b: rol-aware havuz + isim ile kişiselleştirme.
        const tips = _getRoleTips(currentUser?.role);
        const tip = tips[Math.floor(Math.random() * tips.length)];
        const greetingList = pickFilizGreetings();
        const baseGreeting = greetingList[Math.floor(Math.random() * greetingList.length)];
        // İlk ad ile selam kişiselleştir; sleepy mood'da uyku tonunu koru (isim ekleme).
        const firstName = currentUser?.name?.trim().split(/\s+/)[0];
        const greeting = (firstName && filizMood !== 'sleepy')
            ? `${baseGreeting} — ${firstName}`
            : baseGreeting;
        return {
            greeting,
            msg: `${tip.emoji} ${tip.msg}`,
            tip: 'Tıklayarak başka bir ipucu al ✨',
        };
    };

    const showSmart = () => {
        const t = pickTip();
        showCustomMessage(t.greeting, t.msg, t.tip);
    };

    mascot.addEventListener('click', () => {
        // Uyku zamanında tıklanırsa Filiz sinirlenir (uyandırıldı!), aksi halde sevinir
        const stateClass = filizMood === 'sleepy' ? 'angry' : 'happy';
        const duration = stateClass === 'angry' ? 1500 : 1700;
        mascot.classList.add(stateClass);
        setTimeout(() => mascot.classList.remove(stateClass), duration);
        showSmart();
    });

    // İlk selam (3 sn)
    setTimeout(() => { if (!bubbleVisible) showSmart(); }, 3000);

    // Bubble dışına tıklayınca kapat
    document.addEventListener('click', (e) => {
        if (bubbleVisible && !mascot.contains(e.target) && !bubble.contains(e.target)) {
            bubble.classList.remove('show');
            bubbleVisible = false;
            clearTimeout(hideTimer);
        }
    });

    // ─── 👀 GÖZ TAKİBİ ──────────────────────────────────────
    const pupilL = document.getElementById('filizPupilL');
    const pupilR = document.getElementById('filizPupilR');
    document.addEventListener('mousemove', (e) => {
        if (!pupilL || !pupilR) return;
        const rect = mascot.getBoundingClientRect();
        const cx = rect.left + rect.width / 2;
        const cy = rect.top + rect.height / 2;
        const dx = e.clientX - cx;
        const dy = e.clientY - cy;
        const dist = Math.hypot(dx, dy);
        const max = 2.2;  // SVG koordinatlarında pupil hareket aralığı
        const ux = (dx / Math.max(dist, 1)) * Math.min(dist / 100, 1) * max;
        const uy = (dy / Math.max(dist, 1)) * Math.min(dist / 100, 1) * max;
        pupilL.style.transform = `translate(${ux}px, ${uy}px)`;
        pupilR.style.transform = `translate(${ux}px, ${uy}px)`;
    });

    // ─── 🎭 MOOD: sadece gündüz/gece — happy ↔ sleepy ─────────
    // (Worried otomatik tetiklenmez; alert mesajları konuşma balonunda gösterilir.)
    const updateMood = async () => {
        const hour = new Date().getHours();
        const isLateNight = hour < 5;
        setFilizMood(isLateNight ? 'sleepy' : 'happy');

        // Alert listesini balon için arka planda topla (mood'u etkilemez)
        if (apiOnline) {
            try {
                const alerts = await api('/api/alerts/?severity=critical&is_resolved=false&limit=10');
                filizCriticalAlerts = alerts || [];
            } catch {
                filizCriticalAlerts = [];
            }
        } else {
            filizCriticalAlerts = [];
        }
    };
    updateMood();
    setInterval(updateMood, 60000);  // 1 dk'da bir tekrar kontrol
}

init();
