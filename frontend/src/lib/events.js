export const actionMap = {};

export function registerAction(name, func) {
    actionMap[name] = func;
}

export function registerActions(map) {
    Object.assign(actionMap, map);
}

export function setupEventDelegation() {
    document.addEventListener('click', e => {
        const btn = e.target.closest('[data-action]');
        if (!btn) return;
        const action = btn.dataset.action;
        if (actionMap[action]) {
            e.preventDefault();
            actionMap[action](btn, e);
        }
    });

    // Keyboard support for custom buttons (a11y)
    document.addEventListener('keydown', e => {
        if (e.key === 'Enter' || e.key === ' ') {
            const btn = e.target.closest('[data-action]');
            if (!btn) return;
            const action = btn.dataset.action;
            if (actionMap[action]) {
                e.preventDefault();
                actionMap[action](btn, e);
            }
        }
    });

    document.addEventListener('change', e => {
        const el = e.target.closest('[data-change]');
        if (!el) return;
        const action = el.dataset.change;
        if (actionMap[action]) {
            actionMap[action](el, e);
        }
    });
}
