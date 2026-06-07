/**
 * Birim testler — _applyRoleVisibility() (frontend/src/lib/pages/account.js).
 *
 * Rol-aware görünürlük: [data-role] taşıyan elemanlar yalnız eşleşen role
 * görünür; user null ise hepsi gizli. .user-badge-role span'i HARİÇ (yalnız
 * CSS renk kodu için data-role taşır, gating'e girmemeli).
 * jsdom environment vitest config'inden gelir.
 */
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { _applyRoleVisibility } from "../src/lib/pages/account.js";

beforeEach(() => {
  document.body.innerHTML = `
    <a class="nav-item" data-role="admin" id="usersNav">Kullanıcılar</a>
    <a class="nav-item" data-role="admin,overseer,developer" id="analyticsNav">Raporlar</a>
    <a class="dev-link" data-role="admin,developer" id="devLink">&lt;/&gt;</a>
    <span class="user-badge-role" data-role="admin" id="roleSpan">yönetici</span>`;
});
afterEach(() => {
  document.body.innerHTML = "";
});

describe("_applyRoleVisibility", () => {
  it("admin: tüm admin-içeren öğeler görünür", () => {
    _applyRoleVisibility({ role: "admin" });
    expect(document.getElementById("usersNav").style.display).toBe("");
    expect(document.getElementById("analyticsNav").style.display).toBe("");
    expect(document.getElementById("devLink").style.display).toBe("");
  });

  it("çiftçi: admin-only öğeler gizli", () => {
    _applyRoleVisibility({ role: "farmer" });
    expect(document.getElementById("usersNav").style.display).toBe("none");
    expect(document.getElementById("devLink").style.display).toBe("none");
    expect(document.getElementById("analyticsNav").style.display).toBe("none");
  });

  it("developer: </> görünür ama Kullanıcılar gizli", () => {
    _applyRoleVisibility({ role: "developer" });
    expect(document.getElementById("devLink").style.display).toBe("");
    expect(document.getElementById("analyticsNav").style.display).toBe("");
    expect(document.getElementById("usersNav").style.display).toBe("none");
  });

  it("user null → tüm gated öğeler gizli", () => {
    _applyRoleVisibility(null);
    expect(document.getElementById("usersNav").style.display).toBe("none");
    expect(document.getElementById("analyticsNav").style.display).toBe("none");
    expect(document.getElementById("devLink").style.display).toBe("none");
  });

  it(".user-badge-role gating'e GİRMEZ — hiçbir durumda gizlenmez", () => {
    const span = document.getElementById("roleSpan"); // data-role=admin
    _applyRoleVisibility({ role: "farmer" }); // eşleşmeyen rol
    expect(span.style.display).toBe(""); // hariç → dokunulmadı
    _applyRoleVisibility(null); // user yok
    expect(span.style.display).toBe(""); // yine dokunulmadı
  });
});
