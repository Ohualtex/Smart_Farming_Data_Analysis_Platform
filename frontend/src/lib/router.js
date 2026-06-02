/* ============================================================
   SFDAP — Router Module
   ============================================================
   Hash-based SPA navigation, sidebar toggle, page title yönetimi.
   ============================================================ */

export const pageTitles = {
    dashboard: ['Genel Bakış', 'Tarlanın özeti'],
    fields: ['Tarlalarım', 'Çiftliklerine bağlı tarlalar'],
    'field-detail': ['Tarla Detayı', 'Sensör, sulama, hastalık ve toprak'],
    weather: ['Hava Durumu', 'Sıcaklık, nem ve yağış'],
    irrigation: ['Sulama', 'Önerilen su miktarı ve geçmiş'],
    fertilizer: ['Gübreleme', 'NPK önerisi ve takvim'],
    sensors: ['Sensörler', 'Tarladaki ölçüm cihazları'],
    analytics: ['Raporlar', 'Bölge bazında özet ve dışa aktarma'],
    map: ['Türkiye Haritası', 'Çiftliklerin coğrafi dağılımı'],
    plants: ['Bitki Sağlığı', 'Yapraktan hastalık tespiti'],
    alerts: ['Uyarılar', 'Sistem ve sensör uyarıları'],
    users: ['Kullanıcı Yönetimi', 'Tüm kullanıcılar (admin)'],
    auth: ['Hesabım', 'Profil ve şifre'],
};

/**
 * Sayfa değiştirme fonksiyonu.
 * @param {string} page - Sayfa adı
 * @param {Object} handlers - Sayfa yükleme handler'ları
 * @param {Function} startHeroTipRotation - Hero tip rotation starter
 */
export function navigate(page, handlers, startHeroTipRotation) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(n => {
        n.classList.remove('active');
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
    // Focus the <main> programmatically for a11y
    const main = document.getElementById('main-content');
    if (main) main.focus({ preventScroll: false });

    // Load page data
    const handler = handlers[page];
    if (handler) handler();

    // Hero subtitle dinamik Filiz tipi
    startHeroTipRotation?.(page);

    // Close sidebar on mobile
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.remove('open');
    const hamburger = document.querySelector('.hamburger');
    if (hamburger) hamburger.setAttribute('aria-expanded', 'false');
}

export function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const isOpen = sidebar.classList.toggle('open');
    const hamburger = document.querySelector('.hamburger');
    if (hamburger) hamburger.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
}

/**
 * Hash router'ı başlat.
 * @param {Function} navigateFn - navigate fonksiyonu
 * @param {Function} openFieldDetailFn - field detail açma fonksiyonu
 */
export function initHashRouter(navigateFn, openFieldDetailFn) {
    window.addEventListener('hashchange', () => {
        const raw = location.hash.slice(1) || 'dashboard';
        if (raw.startsWith('field/')) {
            const id = parseInt(raw.split('/')[1], 10);
            if (Number.isFinite(id)) openFieldDetailFn(id);
            return;
        }
        if (pageTitles[raw]) navigateFn(raw);
    });
}
