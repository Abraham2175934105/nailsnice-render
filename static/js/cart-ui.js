(function() {
    const CART_SCRIPT_ID = 'cart-data';

    function readCart() {
        const el = document.getElementById(CART_SCRIPT_ID);
        if (!el) return {};
        try {
            return JSON.parse(el.textContent);
        } catch (err) {
            console.warn('No se pudo leer el carrito embebido', err);
            return {};
        }
    }

    function countItems(cartObj) {
        return Object.values(cartObj || {}).reduce((acc, val) => acc + (parseInt(val, 10) || 0), 0);
    }

    function updateBadge(newCount) {
        const badge = document.querySelector('[data-cart-count]');
        if (!badge) return;
        const safeCount = Math.max(0, parseInt(newCount, 10) || 0);
        badge.textContent = safeCount;
        badge.dataset.cartCount = safeCount;
        badge.classList.toggle('is-empty', safeCount === 0);
    }

    function showToast(message, tone = 'success') {
        const toast = document.createElement('div');
        toast.className = `toast toast--${tone}`;
        toast.setAttribute('role', 'status');
        toast.setAttribute('aria-live', 'polite');
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(() => {
            toast.classList.add('is-visible');
        }, 10);
        setTimeout(() => {
            toast.classList.remove('is-visible');
            setTimeout(() => toast.remove(), 250);
        }, 2800);
    }

    const initialCart = readCart();
    updateBadge(countItems(initialCart));

    window.CartUI = {
        updateBadge,
        toast: showToast,
        setCount: updateBadge,
        increment(delta) {
            const badge = document.querySelector('[data-cart-count]');
            const current = parseInt(badge?.dataset.cartCount || badge?.textContent || '0', 10) || 0;
            updateBadge(current + (delta || 0));
        },
    };
})();
