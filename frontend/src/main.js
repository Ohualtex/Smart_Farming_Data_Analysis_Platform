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
    loadDashboard, loadDemoData, _startHeroTipRotation,
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
        // <select> YALNIZ 'change' ile sürülür: dropdown'a tıklamak (açmak) click
        // delegation'ı tetikleyip istenmeyen aksiyon göndermesin — örn. admin rol
        // dropdown'ını açmak istenmeyen rol-değişikliği PATCH'i atardı (audit YÜKSEK).
        if (el.tagName === 'SELECT') return;
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

    // Hero sayılarına count-up animasyonu artık loadDashboard()'da, veri
    // yazıldıktan SONRA tetikleniyor (audit #28). init'te '—' okunduğu için
    // çalışmıyordu → buradaki ölü çağrı kaldırıldı.

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
        const ug = document.querySelector(".welcome-underground");
        if (!welcome || !pin || !act1) return;
        let ticking = false;
        const update = () => {
            // sticky yol = act1 yüksekliği − 1 ekran (pin'in takılı kaldığı mesafe)
            const travel = Math.max(act1.offsetHeight - welcome.clientHeight, 1);
            const rise = Math.min(Math.max(welcome.scrollTop / travel, 0), 1);   // [0,1] (iOS rubber-band clamp)
            pin.style.setProperty("--rise", rise.toFixed(4));
            // page-1'i geçince fill-intro + fill-decor SÖNSÜN (page-2 içeriğiyle üst üste binmesin):
            const exit = Math.min(Math.max((welcome.scrollTop - travel) / (travel * 0.5), 0), 1);
            pin.style.setProperty("--exit", exit.toFixed(4));
            // 🎬 Toprak-altı sinematik derinlik: --depth-t (0=giriş → 1=en derin) sis için;
            // --cam (px, ham scroll) parallax katmanları için. Underground act1'den SONRA başlar.
            if (ug) {
                const ugTop = act1.offsetHeight;
                const ugRange = Math.max(welcome.scrollHeight - welcome.clientHeight - ugTop, 1);
                const depthT = Math.min(Math.max((welcome.scrollTop - ugTop) / ugRange, 0), 1);
                ug.style.setProperty("--depth-t", depthT.toFixed(4));
                ug.style.setProperty("--cam", Math.round(welcome.scrollTop));
                ug.style.setProperty("--rise", rise.toFixed(4));   // atmos opacity → yüzeyde gizli, dolumda belirir
            }
            ticking = false;
        };
        welcome.addEventListener("scroll", () => {
            if (!ticking) { requestAnimationFrame(update); ticking = true; }
        }, { passive: true });
        update();
    })();
    // Kart/açıklama giriş YÖNÜ (zigzag, data-side): kart kendi tarafından, açıklama karşıdan.
    document.querySelectorAll(".wu-reveal").forEach((el) => {
        const side = el.closest(".wu-scene")?.dataset.side;
        if (!side) el.classList.add("from-b");
        else if (el.classList.contains("wu-card")) el.classList.add(side === "left" ? "from-l" : "from-r");
        else el.classList.add(side === "left" ? "from-r" : "from-l");   // açıklama: KARŞI taraf
    });

    // FULLPAGE navigasyon: HER kaydırma = 1 sayfa (yüzey → başlık → özellikler → CTA),
    // smooth YAY ile kayar. Aktif sahnenin kartı/açıklaması girer; önceki "geldiği gibi" çıkar.
    (() => {
        const welcome = document.getElementById("welcome");
        const act1 = document.querySelector(".welcome-act1");
        if (!welcome || !act1) return;
        const scenes = [...welcome.querySelectorAll(".wu-scene")];
        let pages = [], page = 0, animating = false, locked = false, idleTimer = null, hardTimer = null;
        const unlock = () => { locked = false; clearTimeout(hardTimer); };
        const maybeUnlock = () => { if (!animating) unlock(); };   // tekerlek durunca + animasyon bitince açılır

        const computePages = () => {
            const ch = welcome.clientHeight, max = welcome.scrollHeight - ch;
            const clamp = (v) => Math.max(0, Math.min(max, Math.round(v)));
            const travel = Math.max(act1.offsetHeight - ch, 1);
            const sceneTargets = scenes.map((s) => clamp(s.getBoundingClientRect().top + welcome.scrollTop + s.offsetHeight / 2 - ch / 2));
            pages = [0, clamp(travel), ...sceneTargets];   // 0=yüzey, 1=başlık, 2..=özellikler/CTA
        };
        const updateReveals = () => {
            scenes.forEach((s, i) => {
                const active = page === i + 2;   // sayfa i+2 → sahne i aktif
                s.querySelectorAll(".wu-reveal").forEach((el) => el.classList.toggle("in-view", active));
            });
        };
        // Yan navigasyon noktaları — katmanlar arası HIZLI geçiş (toprağa inince görünür)
        const dotsNav = document.createElement("nav");
        dotsNav.className = "wu-dots"; dotsNav.setAttribute("aria-label", "Sayfa navigasyonu");
        let dots = [];
        const buildDots = () => {
            dotsNav.innerHTML = "";
            dots = pages.map((_, i) => {
                const b = document.createElement("button");
                b.type = "button"; b.className = "wu-dot"; b.setAttribute("aria-label", "Sayfa " + (i + 1));
                b.addEventListener("click", () => navTo(i));
                dotsNav.appendChild(b); return b;
            });
        };
        const updateDots = () => {
            dots.forEach((d, i) => d.classList.toggle("active", i === page));
            dotsNav.classList.toggle("visible", page >= 1);   // yüzeyde gizli, toprakta görünür
        };
        welcome.appendChild(dotsNav);
        const ease = (p) => 1 - Math.pow(1 - p, 3);   // easeOutCubic: yumuşak, TAŞMA YOK (sıçrama/jank yok)
        const animateTo = (target) => {
            animating = true;
            const start = welcome.scrollTop, dist = target - start, dur = 520, t0 = performance.now();
            const step = (now) => {
                const p = Math.min((now - t0) / dur, 1);
                welcome.scrollTop = start + dist * ease(p);
                if (p < 1) requestAnimationFrame(step);
                else { welcome.scrollTop = target; animating = false; clearTimeout(idleTimer); idleTimer = setTimeout(maybeUnlock, 70); }
            };
            requestAnimationFrame(step);
        };
        const navTo = (target) => {
            if (locked) return;
            target = Math.max(0, Math.min(pages.length - 1, target));
            if (target === page) return;
            locked = true;
            clearTimeout(hardTimer); hardTimer = setTimeout(unlock, 900);   // GARANTİ açılış → sürekli kaydırma takılmaz
            page = target;
            updateReveals();        // aktif kart girer, öncekiler "geldiği gibi" çıkar (aynı anda)
            updateDots();
            animateTo(pages[page]);
        };
        const go = (dir) => navTo(page + dir);

        computePages(); buildDots(); updateReveals(); updateDots();
        window.addEventListener("resize", () => { computePages(); buildDots(); updateDots(); welcome.scrollTop = pages[page]; });
        // TEK JEST = TEK SAHNE: nav sırasında + tekerlek durana dek kilitli (go locked'ı kontrol+set eder).
        // HER wheel olayı idle sayacını erteler → tekerlek 90ms DURUNCA + animasyon bitince serbest kalır
        // (maybeUnlock iki yoldan da çağrılır → asla takılı kalmaz).
        welcome.addEventListener("wheel", (e) => {
            e.preventDefault();
            clearTimeout(idleTimer);
            idleTimer = setTimeout(maybeUnlock, 90);
            go(e.deltaY > 0 ? 1 : -1);
        }, { passive: false });
        let touchY = null;
        welcome.addEventListener("touchstart", (e) => { touchY = e.touches[0].clientY; }, { passive: true });
        welcome.addEventListener("touchmove", (e) => { e.preventDefault(); }, { passive: false });
        welcome.addEventListener("touchend", (e) => {
            if (touchY === null) return;
            const dy = touchY - e.changedTouches[0].clientY;
            if (Math.abs(dy) > 42) go(dy > 0 ? 1 : -1);
            touchY = null;
        }, { passive: true });
        window.addEventListener("keydown", (e) => {
            if (!welcome.isConnected || getComputedStyle(welcome).display === "none") return;
            if (e.key === "ArrowDown" || e.key === "PageDown") { e.preventDefault(); go(1); }
            else if (e.key === "ArrowUp" || e.key === "PageUp") { e.preventDefault(); go(-1); }
        });
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
