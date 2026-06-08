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
import { popFiliz, filizInteract, initFiliz, initWelcomeFilizEyes, welcomeFilizGreeting } from "./lib/filiz.js";

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

    // İlk açılış selamı: entrance bittikten sonra Filiz otomatik çıkar + selam verir
    // (welcome görünürse). init başında schedule edilir → await'lerden bağımsız.
    setTimeout(welcomeFilizGreeting, 2600);

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
        filizInteract:      () => filizInteract(),
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
    // Welcome scrollytelling: sticky pin dolum fazı. --rise = act1 içindeki dolum
    // ilerlemesi (0=yüzey, 1=ekran %100 toprak, pin tam o anda serbest). CSS toprak
    // grubunu (soil/fill/filiz-rise) düz yukarı kaydırır + başlık/logo'yu soldurur.
    (() => {
        const welcome = document.getElementById("welcome");
        const pin = document.querySelector(".welcome-pin");
        const act1 = document.querySelector(".welcome-act1");
        if (!welcome || !pin || !act1) return;
        let ticking = false;
        const update = () => {
            // sticky yol = act1 yüksekliği − 1 ekran (pin'in takılı kaldığı mesafe)
            const travel = Math.max(act1.offsetHeight - welcome.clientHeight, 1);
            const rise = Math.min(Math.max(welcome.scrollTop / travel, 0), 1);   // [0,1] (iOS rubber-band clamp)
            pin.style.setProperty("--rise", rise.toFixed(4));
            ticking = false;
        };
        welcome.addEventListener("scroll", () => {
            if (!ticking) { requestAnimationFrame(update); ticking = true; }
        }, { passive: true });
        update();
    })();
    // Toprak-altı sahneleri: kart/açıklama yandan (zigzag), intro/cta aşağıdan YAYLI girer.
    // Yön sınıfı data-side'a göre eklenir; IO toggle ile re-trigger (çıkınca sıfırlanır → teker teker).
    (() => {
        const welcome = document.getElementById("welcome");
        const reveals = document.querySelectorAll(".wu-reveal");
        if (!reveals.length) return;
        reveals.forEach((el) => {
            const side = el.closest(".wu-scene")?.dataset.side;
            if (!side) el.classList.add("from-b");                                              // intro/cta: aşağıdan
            else if (el.classList.contains("wu-card")) el.classList.add(side === "left" ? "from-l" : "from-r");
            else el.classList.add(side === "left" ? "from-r" : "from-l");                       // açıklama: KARŞI taraf
        });
        if (!welcome || !("IntersectionObserver" in window)) {
            reveals.forEach((el) => el.classList.add("in-view"));
            return;
        }
        const io = new IntersectionObserver((entries) => {
            entries.forEach((e) => e.target.classList.toggle("in-view", e.isIntersecting));
        }, { root: welcome, threshold: 0.4 });
        reveals.forEach((el) => io.observe(el));
    })();
    // Dolum YAYLI snap (#2): act1 içinde scroll DURUNCA, yeterince çekildiyse başlığa
    // YAYLANARAK (overshoot) oturur; az çekildiyse yüzeye geri döner (tersinir).
    // Native scroll-snap yay yapamadığı için JS. Özellik sahneleri native snap'te kalır.
    (() => {
        const welcome = document.getElementById("welcome");
        const act1 = document.querySelector(".welcome-act1");
        if (!welcome || !act1) return;
        let timer = null, animating = false, cancelled = false;
        // easeOutBack: hedefi biraz aşıp geri oturur = "yay/zıplama"
        const easeOutBack = (p) => { const c1 = 1.7, c3 = c1 + 1; return 1 + c3 * (p - 1) ** 3 + c1 * (p - 1) ** 2; };
        const springTo = (target) => {
            animating = true; cancelled = false;
            const start = welcome.scrollTop, dist = target - start, dur = 480, t0 = performance.now();
            const step = (now) => {
                if (cancelled) { animating = false; return; }
                const p = Math.min((now - t0) / dur, 1);
                welcome.scrollTop = start + dist * easeOutBack(p);
                if (p < 1) requestAnimationFrame(step);
                else { welcome.scrollTop = target; animating = false; }
            };
            requestAnimationFrame(step);
        };
        const settle = () => {
            if (animating) return;
            const travel = Math.max(act1.offsetHeight - welcome.clientHeight, 1);
            const st = welcome.scrollTop;
            if (st <= 2 || st >= travel) return;              // yüzeyde ya da dolum tamam → native/serbest
            const target = (st / travel) < 0.22 ? 0 : travel; // tersinir: az çekince→yüzey, yeterli→başlık
            if (Math.abs(st - target) > 3) springTo(target);
        };
        welcome.addEventListener("scroll", () => { clearTimeout(timer); timer = setTimeout(settle, 130); }, { passive: true });
        welcome.addEventListener("wheel", () => { if (animating) cancelled = true; }, { passive: true });
        welcome.addEventListener("touchstart", () => { if (animating) cancelled = true; }, { passive: true });
    })();

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

    let _cycleTimer = null;
    btns.forEach(btn => btn.addEventListener('click', () => {
        // welcome sıralı gün-gece döngüsü: yönlü transition-delay'leri AKTİF et
        // (yalnız kullanıcı toggle'ında; initial applyTheme'de değil → entrance temiz).
        root.classList.add('welcome-cycle');
        clearTimeout(_cycleTimer);
        _cycleTimer = setTimeout(() => root.classList.remove('welcome-cycle'), 2300);
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
