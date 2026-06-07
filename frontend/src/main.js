/* ============================================================
   SFDAP Dashboard — Entry Point (Orchestrator)
   ============================================================
   Refactored: API, utils, router + sayfa modülleri `src/lib/` altında.
   Bu dosya yalnız glue: import'lar + pageHandlers + navigate + actionMap
   + INIT + tema. Sayfa/aksiyon mantığı `lib/pages/*` ve `lib/filiz.js`'te.

   `<script type="module">` ile yüklenir. Tüm etkileşimler `data-action`
   event delegation üzerinden (window-bridge yok).
   ============================================================ */

import { api, initApiCallbacks } from "./lib/api.js";
import { showToast, updateStatus, updateClock } from "./lib/utils.js";
import { pageTitles, toggleSidebar, initHashRouter, navigate as _navigateCore } from "./lib/router.js";
import { getCurrentUser, setCurrentUser, setApiOnline } from "./lib/session.js";
import { setNavigate } from "./lib/nav.js";
import { rethemeCharts } from "./lib/charts.js";

// ─── Sayfa modülleri ─────────────────────────────────────────
import {
    loadDashboard, loadDemoData, animateHeroStats, _startHeroTipRotation,
} from "./lib/pages/dashboard.js";
import {
    loadFields, toggleForm, submitNewFarm, submitNewField, editFarm, deleteFarm,
    editField, deleteField, submitNewSensor, deleteSensor,
    openFieldDetail, analyzeFieldLeaf,
} from "./lib/pages/fields.js";
import {
    loadSensors, loadSensorDetail, loadWeather, loadIrrigation,
    predictIrrigation, approveIrrigation, updateIrrigationStatus, addFieldIrrigation,
    recommendFertilizer, fertilizerSchedule, loadAnalytics, loadMap, loadPlants,
    analyzePlantImage, getSensorsPage, getIrrigationPage,
} from "./lib/pages/monitoring.js";
import {
    loadAlerts, resolveAlert, toggleBell, runAlertCheck, resolveFromBell,
} from "./lib/pages/alerts.js";
import {
    _renderUserBadge, refreshAuthState, goToLogin, goToWelcome, toggleLandingForm,
    doLogin, doRegister, doChangePassword, doLogout,
    loadUsers, createUser, changeUserRole, resetUserPassword, deleteUser,
} from "./lib/pages/account.js";
import { popFiliz, initFiliz, initWelcomeFilizEyes, welcomeFilizGreeting } from "./lib/filiz.js";

let refreshInterval = null;

// ─── NAVIGATION (delegates to lib/router.js) ─────────────────
// Page handler map — navigate() çağrıldığında doğru veri-yükleme fonksiyonunu çalıştırır.
const pageHandlers = {
    dashboard: () => loadDashboard(),
    fields: () => loadFields(),
    sensors: () => loadSensors(),
    weather: () => loadWeather(),
    irrigation: () => loadIrrigation(),
    analytics: () => loadAnalytics(),
    map: () => loadMap(),
    plants: () => loadPlants(),
    alerts: () => loadAlerts(),
    users: () => loadUsers(),
    auth: () => refreshAuthState(),
};

function navigate(page) {
    _navigateCore(page, pageHandlers, _startHeroTipRotation);
}
// Sayfa modülleri navigate'i lib/nav.js üzerinden çağırır (döngüsüz bridge).
setNavigate(navigate);

// Hash router'ı init'te başlatacağız (init fonksiyonunda).

// ─── INIT ─────────────────────────────────────────────────────
async function init() {
    // Welcome ilk-giriş: .welcome-intro from-state'leri ilk-boyada uygulanır;
    // ardından kaldırılır → elemanlar doğal duruma TRANSITION ile "girer" (toggle
    // ile aynı transition → animation-fill kilidi yok). RAF: görünür sekmede ~2
    // frame, akıcı. setTimeout: gizli/arka-plan sekmede RAF duraklar → fallback
    // ile state takılmaz (timer throttled da olsa firelanır).
    const _dropIntro = () => document.getElementById('welcome')?.classList.remove('welcome-intro');
    requestAnimationFrame(() => requestAnimationFrame(_dropIntro));
    setTimeout(_dropIntro, 450);

    // API modülüne callback'leri bağla (circular dep önlemek için)
    initApiCallbacks({
        showToast,
        renderUserBadge: _renderUserBadge,
        setCurrentUser,
    });

    // Hash router'ı başlat
    initHashRouter(navigate, openFieldDetail);

    // ─── EVENT DELEGATION ─────────────────────────────────────
    // data-action → handler map. Inline onclick kaldırıldı, CSP uyumlu.
    const actionMap = {
        navigate:           (el) => navigate(el.dataset.arg),
        toggleSidebar:      () => toggleSidebar(),
        toggleBell:         () => toggleBell(),
        toggleLandingForm:  (el) => { toggleLandingForm(el.dataset.arg); },
        goToLogin:          () => goToLogin(),
        goToWelcome:        () => goToWelcome(),
        popFiliz:           () => popFiliz(),
        doLogin:            () => doLogin(),
        doRegister:         () => doRegister(),
        doLogout:           () => doLogout(),
        doChangePassword:   () => doChangePassword(),
        predictIrrigation:  () => predictIrrigation(),
        recommendFertilizer:() => recommendFertilizer(),
        fertilizerSchedule: () => fertilizerSchedule(),
        analyzePlantImage:  () => analyzePlantImage(),
        runAlertCheck:      () => runAlertCheck(),
        createUser:         () => createUser(),
        loadAlerts:         () => loadAlerts(),
        sensorsPrev:        () => loadSensors(getSensorsPage() - 1),
        sensorsNext:        () => loadSensors(getSensorsPage() + 1),
        irrigationPrev:     () => loadIrrigation(getIrrigationPage() - 1),
        irrigationNext:     () => loadIrrigation(getIrrigationPage() + 1),
        // ─── v9a: window-bridge'den taşınan dinamik handler'lar ───────
        // Argümanlar data-* attribute'lerinden okunur (data-id sayı,
        // data-name/data-status/data-arg string). Eski inline onclick'ler
        // template string'lerden data-action'a çevrildi; window global yok.
        openFieldDetail:        (el) => openFieldDetail(+el.dataset.id),
        loadSensorDetail:       (el) => loadSensorDetail(+el.dataset.id),
        addFieldIrrigation:     (el) => addFieldIrrigation(+el.dataset.id),
        resolveAlert:           (el) => resolveAlert(+el.dataset.id),
        resolveFromBell:        (el) => resolveFromBell(+el.dataset.id),
        submitNewSensor:        (el) => submitNewSensor(+el.dataset.id),
        analyzeFieldLeaf:       () => analyzeFieldLeaf(),
        approveIrrigation:      () => approveIrrigation(),
        loadDashboard:          () => loadDashboard(),
        loadDemoData:           () => loadDemoData(),
        submitNewFarm:          () => submitNewFarm(),
        submitNewField:         () => submitNewField(),
        toggleForm:             (el) => toggleForm(el.dataset.arg),
        deleteFarm:             (el) => deleteFarm(+el.dataset.id, el.dataset.name),
        deleteField:            (el) => deleteField(+el.dataset.id, el.dataset.name),
        deleteSensor:           (el) => deleteSensor(+el.dataset.id, el.dataset.name),
        deleteUser:             (el) => deleteUser(+el.dataset.id, el.dataset.name),
        editFarm:               (el) => editFarm(+el.dataset.id, el.dataset.name),
        editField:              (el) => editField(+el.dataset.id, el.dataset.name),
        resetUserPassword:      (el) => resetUserPassword(+el.dataset.id, el.dataset.name),
        updateIrrigationStatus: (el) => updateIrrigationStatus(+el.dataset.id, el.dataset.status),
        // changeUserRole: <select> change event'i — yeni rol el.value'dan okunur
        changeUserRole:         (el) => changeUserRole(+el.dataset.id, el.value),
        // Bileşik aksiyon: boş-durum "İlk çiftliğimi ekle" (navigate + form aç)
        addFirstFarm:           () => { navigate('fields'); toggleForm('newFarmForm'); },
    };

    document.addEventListener('click', (e) => {
        const el = e.target.closest('[data-action]');
        if (!el) return;
        const action = el.dataset.action;
        const handler = actionMap[action];
        if (handler) {
            e.preventDefault();
            handler(el);
        }
    });

    // Select (onchange) delegation — alert filtre dropdown'ları + changeUserRole
    document.addEventListener('change', (e) => {
        const el = e.target.closest('[data-action]');
        if (!el) return;
        const handler = actionMap[el.dataset.action];
        if (handler) handler(el);
    });

    // Keydown delegation — klavye a11y: role="button" taşıyan data-action
    // elemanlarında (örn. sensör satırı) Enter/Space tıklama gibi davranır.
    // v9a: inline onkeydown kaldırıldı, window-bridge'siz event delegation.
    document.addEventListener('keydown', (e) => {
        if (e.key !== 'Enter' && e.key !== ' ') return;
        const el = e.target.closest('[data-action][role="button"]');
        if (!el) return;
        const handler = actionMap[el.dataset.action];
        if (handler) {
            e.preventDefault();
            handler(el);
        }
    });

    // Health check
    const health = await api('/api/health');
    const apiOnline = health !== null;
    setApiOnline(apiOnline);
    updateStatus(apiOnline);
    if (apiOnline) showToast('Sistem aktif — veriler güncel', 'success');
    else showToast('Bağlantı yok — son kayıtlı veriler gösteriliyor', 'error');

    // Auth state ilk yükleme — gate uygular (login yoksa landing, app gizli).
    await refreshAuthState();

    // REBUILD Faz 3.5: girişsizse hiçbir sayfaya navigate etme — landing kalır.
    // Giriş yapılınca doLogin() navigate('dashboard') çağırır.
    if (getCurrentUser()) {
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
    initWelcomeFilizEyes();   // welcome filiz göz takibi (fareyi takip)
    setTimeout(welcomeFilizGreeting, 2400);   // ilk açılış: çık + sağ el selam (entrance sonrası)

    // Tema (light/dark)
    initTheme();
}

/* ─── 🌗 TEMA YÖNETİMİ ───────────────────────────────────── */
function initTheme() {
    const STORAGE_KEY = 'sfdap-theme';
    const root = document.documentElement;
    // Birden çok toggle: header (#themeToggle) + welcome (.welcome-sun / .welcome-moon).
    // Hepsi `.js-theme-toggle` class'ı taşır ve aynı state'i paylaşır.
    const btns = Array.from(document.querySelectorAll('.js-theme-toggle'));
    if (!btns.length) return;

    // İlk tema: localStorage > saat-bazlı (06–20 gündüz, aksi gece). head'deki
    // inline script ile aynı mantık; ilk açılışta sabitlenir (refresh değiştirmez).
    let initial = localStorage.getItem(STORAGE_KEY);
    if (!initial) {
        const h = new Date().getHours();
        initial = (h >= 6 && h < 20) ? 'light' : 'dark';
        localStorage.setItem(STORAGE_KEY, initial);
    }
    applyTheme(initial);

    btns.forEach(btn => btn.addEventListener('click', () => {
        const current = root.dataset.theme || 'dark';
        const next = current === 'light' ? 'dark' : 'light';
        applyTheme(next);
        localStorage.setItem(STORAGE_KEY, next);
        // Chart.js canvas'ı CSS değişkenlerini almaz → tema değişince renkleri
        // YERİNDE güncelle ki yazılar yeni temada görünür kalsın (refresh gerekmesin).
        rethemeCharts();
    }));

    function applyTheme(theme) {
        const label = theme === 'light' ? 'Karanlık temaya geç' : 'Aydınlık temaya geç';
        if (theme === 'light') root.dataset.theme = 'light';
        else delete root.dataset.theme;
        btns.forEach(btn => {
            btn.setAttribute('aria-label', label);
            btn.setAttribute('title', label);
        });
    }
}

init();

// ─── WINDOW BRIDGE KALDIRILDI (v9a) ───────────────────────────
// Eskiden tüm public function'lar inline `on*` handler'lar için window'a
// expose ediliyordu. v9a'da statik + dinamik tüm inline handler'lar
// `data-action` event delegation'a çevrildi (yukarıdaki actionMap +
// click/change/keydown listener'ları). Artık global window pollution yok;
// fonksiyonlar modül scope'unda closure olarak dispatcher'dan çağrılıyor.
//
// NOT: CSP `script-src 'unsafe-inline'` HÂLÂ gerekli — Swagger UI (/docs)
// inline script kullanıyor. Yani bridge kaldırma CSP'yi sıkılaştırmıyor;
// kazanım kod temizliği (no global namespace pollution).
