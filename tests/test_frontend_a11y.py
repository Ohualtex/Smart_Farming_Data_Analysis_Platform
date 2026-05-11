"""
Frontend Accessibility + Skeleton Loader Smoke Tests
=====================================================
shiftFinal — Ecenur A3 paketi. Static `frontend/index.html` icin yapisal
a11y kontrolleri ve skeleton helper varligi.

EN: Verifies the dashboard HTML carries the a11y landmarks/attributes
    introduced in shiftFinal A3 (skip link, <main id="main-content">,
    ARIA labels on nav/hamburger, scope="col" on table headers, aria-busy
    on async render targets) and that the JS skeleton helpers
    (_skeletonCards/_skeletonRows/_skeletonBlock/_setBusy) are present.

TR: Dashboard HTML'inin shiftFinal A3 a11y eklemelerini (skip link,
    <main id="main-content">, nav/hamburger ARIA label, tablo header
    scope, async hedeflerinde aria-busy) ve JS iskelet helper'larinin
    (_skeletonCards/_skeletonRows/_skeletonBlock/_setBusy) varligini
    dogrular. Tarayicida calistirilmaz — statik HTML icerik kontrolu.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

FRONTEND_HTML = Path(__file__).resolve().parents[1] / "frontend" / "index.html"


@pytest.fixture(scope="module")
def html() -> str:
    """index.html'i bir kere yukle, butun testler ayni string'i goruyor."""
    return FRONTEND_HTML.read_text(encoding="utf-8")


class TestSkipLinkAndLandmarks:
    """Sayfanin a11y landmark'lari (skip-link, <main>, sidebar nav)."""

    def test_skip_link_present_and_targets_main(self, html: str):
        """`<a class="skip-link" href="#main-content">` body'nin basinda olmali."""
        assert 'class="skip-link"' in html
        assert 'href="#main-content"' in html

    def test_main_landmark_with_id(self, html: str):
        """`<main id="main-content" role="main">` tek bir kez olmali."""
        # main tag'i + id + role hepsi ayni satirda
        assert re.search(r'<main[^>]*id="main-content"[^>]*role="main"', html), (
            "main landmark a11y attribute'lari eksik"
        )
        # Tek bir <main> olmali
        assert html.count("<main ") == 1

    def test_sidebar_nav_has_aria_label(self, html: str):
        """Sidebar nav'in `aria-label="Ana menü"`'su olmali."""
        assert 'aria-label="Ana menü"' in html

    def test_hamburger_button_has_aria_attributes(self, html: str):
        """Hamburger butonu aria-label + aria-controls + aria-expanded'a sahip."""
        # Hepsi ayni button etiketinde olmali
        match = re.search(r"<button class=\"hamburger\"[^>]*>", html)
        assert match, "hamburger butonu bulunamadi"
        button_tag = match.group(0)
        assert "aria-label=" in button_tag
        assert 'aria-controls="sidebar"' in button_tag
        assert 'aria-expanded="false"' in button_tag

    def test_toast_container_is_live_region(self, html: str):
        """Toast container `aria-live="polite"` + `role="region"`."""
        match = re.search(r'<div class="toast-container"[^>]*>', html)
        assert match
        assert 'role="region"' in match.group(0)
        assert 'aria-live="polite"' in match.group(0)


class TestTableSemantics:
    """Tablolarin <th scope="col"> ve caption a11y standartlarina uymasi."""

    def test_sensors_table_has_scope_col_headers(self, html: str):
        """Sensor tablo header'lari scope=col + sr-only caption."""
        # Kabaca sensorsTable tbody'sinden once gelen header bolumu
        idx = html.index('id="sensorsTable"')
        # Bu noktanin oncesindeki ~500 karakteri al
        before = html[max(0, idx - 500) : idx]
        assert before.count('scope="col"') >= 4  # ID, Tip, Seri No, Durum
        assert 'class="sr-only"' in before  # caption sr-only

    def test_irrigation_table_has_scope_col_headers(self, html: str):
        idx = html.index('id="irrigationTable"')
        before = html[max(0, idx - 500) : idx]
        assert before.count('scope="col"') >= 5  # 5 column

    def test_no_th_without_scope(self, html: str):
        """`<th>` baslıkları her zaman scope ile yazılmalı."""
        # NOT: dinamik table'larda scope="col" inline-style'la beraber kullanilir;
        # bu test ham `<th>` (scope yok) örüntüsü olmamasini garantiler.
        plain_th = re.findall(r"<th>[^<]", html)
        assert plain_th == [], (
            f"Scope'suz <th> elemanlari bulundu: {plain_th[:3]} — tum tablo header'larina scope='col' eklemek gerek."
        )


class TestAriaBusyTargets:
    """Async fetch hedeflerinde aria-busy="true" baslangic degeri."""

    @pytest.mark.parametrize(
        "element_id",
        [
            "dashboardCards",
            "sensorsTable",
            "weatherCards",
            "irrigationTable",
            "analyticsCards",
            "plantsHistoryTable",
            "alertsSummaryCards",
            "alertsTable",
        ],
    )
    def test_target_has_aria_busy(self, html: str, element_id: str):
        """Hedef element'in aria-busy attribute'u olmali."""
        # Element tag'ini bul ve attribute'larini kontrol et
        pattern = rf'id="{element_id}"[^>]*aria-busy="true"'
        assert re.search(pattern, html), (
            f"#{element_id} icin aria-busy='true' yok — skeleton sirasinda "
            "ekran okuyucuya yukleme durumu bildirimi eksik."
        )


class TestSkeletonHelpersAndCss:
    """JS skeleton helper'lari + CSS class'lar tanimli mi."""

    def test_skeleton_css_variants_defined(self, html: str):
        """CSS'te skeleton card/line/row variant'lari olmali."""
        assert ".skeleton-card" in html
        assert ".skeleton-line" in html
        assert ".skeleton-row" in html

    def test_reduced_motion_respected(self, html: str):
        """`prefers-reduced-motion` icin skeleton animation kapali olmali."""
        match = re.search(
            r"@media \(prefers-reduced-motion: reduce\)\s*\{[^}]*\.skeleton\s*\{[^}]*animation:\s*none",
            html,
            re.DOTALL,
        )
        assert match, "reduced-motion media query'sinde .skeleton animation:none yok"

    def test_focus_visible_outline_defined(self, html: str):
        """Klavye odagi icin :focus-visible outline tanimli."""
        assert ":focus-visible" in html

    def test_sr_only_utility_defined(self, html: str):
        """Screen reader-only yardimci sinifi tanimli olmali."""
        assert ".sr-only" in html

    @pytest.mark.parametrize(
        "helper",
        ["_skeletonCards", "_skeletonRows", "_skeletonBlock", "_setBusy"],
    )
    def test_js_helper_present(self, html: str, helper: str):
        """JS skeleton helper fonksiyonu tanimli olmali."""
        assert f"function {helper}(" in html, f"JS helper `{helper}` bulunamadi — skeleton placeholder akisi bozulur."


class TestActiveNavAriaCurrent:
    """Aktif nav item'inda aria-current='page' baslangic degeri."""

    def test_initial_active_nav_has_aria_current(self, html: str):
        """Dashboard nav item aktif olarak baslar; aria-current page olmali."""
        # nav-item active dashboard linki
        match = re.search(
            r'<a class="nav-item active" href="#dashboard"[^>]*aria-current="page"',
            html,
        )
        assert match, "Aktif dashboard nav item icin aria-current='page' yok"


class TestViteScaffold:
    """Vite scaffold dosyalari mevcut + minimum konfig."""

    def test_package_json_exists(self):
        pkg = FRONTEND_HTML.parent / "package.json"
        assert pkg.exists()
        content = pkg.read_text(encoding="utf-8")
        assert '"vite"' in content
        assert '"build"' in content
        assert '"dev"' in content

    def test_vite_config_exists(self):
        cfg = FRONTEND_HTML.parent / "vite.config.js"
        assert cfg.exists()
        content = cfg.read_text(encoding="utf-8")
        assert "defineConfig" in content
        # proxy /api → FastAPI :8000
        assert "/api" in content
        assert "8000" in content

    def test_frontend_gitignore_excludes_node_modules_and_dist(self):
        gi = FRONTEND_HTML.parent / ".gitignore"
        assert gi.exists()
        content = gi.read_text(encoding="utf-8")
        assert "node_modules/" in content
        assert "dist/" in content
