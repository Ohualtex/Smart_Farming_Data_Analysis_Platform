import { api, apiAuth } from "./api.js";
import { _skeletonRows, _setBusy } from "./skeleton.js";
import { showToast, escAttr as _escAttr, fmtDate as _fmtDate } from "./ui_helpers.js";

const PAGE_SIZE = 50;

// ─── ADMIN KULLANICI YÖNETİMİ (REBUILD Faz 3.5) ───────────────
// Tüm çağrılar apiAuth (401→login, 403→yetki toast). Yalnız admin nav görür.

export async function loadUsers() {
    const tbl = document.getElementById('usersTable');
    tbl.innerHTML = _skeletonBlock(5);
    _setBusy('usersTable', true);
    const list = await apiAuth('/api/auth/users?limit=500');
    if (!list) {
        tbl.innerHTML = '<p class="detail-empty">Kullanıcı listesi alınamadı (yetki gerekli).</p>';
        _setBusy('usersTable', false);
        return;
    }
    const roleOpts = (sel) => ['farmer', 'developer', 'overseer', 'admin']
        .map(r => `<option value="${r}"${r === sel ? ' selected' : ''}>${ROLE_LABELS[r]}</option>`).join('');
    let html = '<table class="detail-table"><caption class="sr-only">Kullanıcı listesi</caption><thead><tr>'
        + '<th>Ad</th><th>E-posta</th><th>Rol</th><th>Çiftlik</th><th>Kayıt</th><th>İşlem</th></tr></thead><tbody>';
    for (const u of list) {
        html += `<tr>
            <td>${_escAttr(u.name)}</td>
            <td>${_escAttr(u.email)}</td>
            <td><select class="user-role-select" data-change="changeUserRole" data-id="${u.id}">${roleOpts(u.role)}</select></td>
            <td>${u.owned_farms_count ?? 0}</td>
            <td>${_fmtDate(u.created_at)}</td>
            <td class="user-actions">
                <button class="btn-mini" data-action="resetUserPassword" data-id="${u.id}" data-name="${_escAttr(u.email)}">🔑 Şifre</button>
                <button class="btn-mini btn-danger" data-action="deleteUser" data-id="${u.id}" data-name="${_escAttr(u.email)}">🗑 Sil</button>
            </td>
        </tr>`;
    }
    html += '</tbody></table>';
    tbl.innerHTML = html;
    _setBusy('usersTable', false);
}

export async function createUser() {
    const name = document.getElementById('newUserName').value.trim();
    const email = document.getElementById('newUserEmail').value.trim();
    const password = document.getElementById('newUserPassword').value;
    const role = document.getElementById('newUserRole').value;
    if (!name || !email || !password) { showToast('Ad, e-posta ve şifre gerekli', 'warning'); return; }
    if (password.length < 8) { showToast('Şifre en az 8 karakter olmalı', 'warning'); return; }
    const res = await apiAuth('/api/auth/users', {
        method: 'POST',
        body: JSON.stringify({ name, email, password, role }),
    });
    if (res) {
        showToast(`${ROLE_LABELS[role]} oluşturuldu ✅`, 'success');
        document.getElementById('newUserName').value = '';
        document.getElementById('newUserEmail').value = '';
        document.getElementById('newUserPassword').value = '';
        loadUsers();
    }
    // apiAuth 409/400'de null döner + toast; ek mesaj gerekmiyor.
}

export async function changeUserRole(userId, role) {
    const res = await apiAuth(`/api/auth/users/${userId}/role`, {
        method: 'PATCH',
        body: JSON.stringify({ role }),
    });
    if (res) {
        showToast(`Rol güncellendi: ${ROLE_LABELS[role]}`, 'success');
        loadUsers();
    } else {
        // 409 (kendi rolü) vb. — listeyi eski haline çek
        loadUsers();
    }
}

export async function resetUserPassword(userId, email) {
    const np = prompt(`${email} için yeni şifre (min 8 karakter):`);
    if (np === null) return;  // iptal
    if (np.length < 8) { showToast('Şifre en az 8 karakter olmalı', 'warning'); return; }
    const res = await apiAuth(`/api/auth/users/${userId}/password`, {
        method: 'PATCH',
        body: JSON.stringify({ new_password: np }),
    });
    if (res) showToast('Şifre sıfırlandı ✅', 'success');
}

export async function deleteUser(userId, email) {
    if (!confirm(`${email} kullanıcısını silmek istediğine emin misin? Bu geri alınamaz.`)) return;
    const token = getAuthToken();
    if (!token) { location.hash = '#auth'; return; }
    try {
        const resp = await fetch(`${API_BASE}/api/auth/users/${userId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` },
        });
        if (resp.status === 204) {
            showToast('Kullanıcı silindi', 'success');
            loadUsers();
        } else {
            const err = await resp.json().catch(() => ({}));
            showToast(err.detail || `Silinemedi (${resp.status})`, 'error');
        }
    } catch (e) {
        showToast('Sunucuya ulaşılamadı', 'error');
    }
}
