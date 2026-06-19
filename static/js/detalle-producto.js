(function () {
    function readJSONScript(id, fallback) {
        const el = document.getElementById(id);
        if (!el) return fallback;
        try {
            return JSON.parse(el.textContent);
        } catch (err) {
            return fallback;
        }
    }

    function formatPrice(value) {
        const num = Number(value || 0);
        return num.toLocaleString('es-CO');
    }

    function getCSRFToken() {
        const match = document.cookie.match(/csrftoken=([^;]+)/);
        if (match) return match[1];

        const meta = document.querySelector('meta[name="csrf-token"]');
        const metaToken = (meta?.getAttribute('content') || '').trim();
        if (metaToken && metaToken !== 'NOTPROVIDED') return metaToken;
        return '';
    }

    async function refreshCSRFToken() {
        try {
            const res = await fetch('/api/csrf-token/', {
                method: 'GET',
                credentials: 'same-origin',
                cache: 'no-store',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                },
            });
            return res.ok;
        } catch (err) {
            return false;
        }
    }

    async function ensureCSRFToken() {
        let token = getCSRFToken();
        if (token) return token;
        await refreshCSRFToken();
        token = getCSRFToken();
        return token;
    }

    function renderError(message) {
        const content = document.getElementById('product-content');
        if (!content) return;
        content.innerHTML = `<div class="error-message"><strong>Error:</strong> ${message}</div>`;
    }

    const ProductDetail = {
        product: readJSONScript('product-detail-data', null),
        related: readJSONScript('related-products-data', []),
        quantity: 1,

        stockInfo() {
            const stock = Number(this.product?.stock || 0);
            if (stock <= 0) return { text: 'Agotado', cls: 'none' };
            if (stock <= 5) return { text: 'Stock limitado', cls: 'low' };
            return { text: 'Disponible', cls: '' };
        },

        renderMain() {
            if (!this.product) {
                renderError('No se pudo cargar el producto.');
                return;
            }

            const content = document.getElementById('product-content');
            if (!content) return;

            const stock = Number(this.product.stock || 0);
            const stockTag = this.stockInfo();
            const imageHtml = this.product.imagen
                ? `<img src="${this.product.imagen}" alt="${this.product.nombre}" />`
                : '<div class="no-image">💅</div>';

            content.innerHTML = `
                <div class="product-detail-wrapper">
                    <div class="product-image-section">
                        <div class="product-main-image" id="main-image">${imageHtml}</div>
                        <div class="product-gallery">
                            <div class="gallery-thumbnail active" data-image="${this.product.imagen || ''}">${imageHtml}</div>
                        </div>
                    </div>
                    <div class="product-info-section">
                        <div class="product-header">
                            <h1 class="product-title">${this.product.nombre}</h1>
                            <p class="product-subtitle">Seleccionado para ti con enfoque profesional y acabado de salon.</p>
                            <span class="product-brand">${this.product.marca || 'Profesional Beauty'}</span>
                        </div>
                        <div class="product-price-section">
                            <div class="price-current">$${formatPrice(this.product.precio)}</div>
                            <p class="price-note">Precio final con impuestos incluidos.</p>
                            <div class="stock-status">
                                <div class="stock-indicator ${stockTag.cls}"></div>
                                <span>${stockTag.text} (${stock} disponibles)</span>
                            </div>
                            <div class="product-reassurance">
                                <div class="reassurance-item">Envio 24-72h</div>
                                <div class="reassurance-item">Compra Protegida</div>
                                <div class="reassurance-item">Soporte Directo</div>
                            </div>
                        </div>
                        <div class="product-description">
                            <div class="description-title">Descripción</div>
                            <p class="description-text">${this.product.descripcion || 'Sin descripción disponible'}</p>
                        </div>
                        <div class="product-attributes">
                            <div class="attribute"><div class="attribute-label">Categoría</div><div class="attribute-value">${this.product.categoria || 'No especificada'}</div></div>
                            <div class="attribute"><div class="attribute-label">Color</div><div class="attribute-value">${this.product.color || 'No especificado'}</div></div>
                            <div class="attribute"><div class="attribute-label">Estado</div><div class="attribute-value">${this.product.estado || 'Activo'}</div></div>
                            <div class="attribute"><div class="attribute-label">Unidad</div><div class="attribute-value">${this.product.unidad_medida || 'Unidad'}</div></div>
                        </div>
                        <div class="product-actions">
                            <div class="quantity-selector">
                                <button class="quantity-btn" type="button" id="qty-down">−</button>
                                <input type="number" class="quantity-input" id="quantity" value="1" min="1" max="${Math.max(1, stock)}" readonly />
                                <button class="quantity-btn" type="button" id="qty-up">+</button>
                            </div>
                            <div class="action-buttons">
                                <button class="btn-add-cart" type="button" id="btn-add-cart" ${stock <= 0 ? 'disabled' : ''}>${stock <= 0 ? 'Agotado' : 'Agregar al Carrito'}</button>
                            </div>
                            <p class="action-note">Si ya tienes direccion guardada, en checkout se cargara automaticamente.</p>
                        </div>
                    </div>
                </div>
            `;

            const breadcrumb = document.getElementById('breadcrumb-product');
            if (breadcrumb) breadcrumb.textContent = this.product.nombre;

            const mainImage = document.getElementById('main-image');
            const thumb = content.querySelector('.gallery-thumbnail');
            if (thumb && mainImage) {
                thumb.addEventListener('click', () => {
                    const img = thumb.dataset.image;
                    mainImage.innerHTML = img ? `<img src="${img}" alt="${this.product.nombre}" />` : '<div class="no-image">💅</div>';
                });
            }
        },

        renderRelated() {
            const grid = document.getElementById('related-products-grid');
            if (!grid) return;

            if (!Array.isArray(this.related) || !this.related.length) {
                grid.innerHTML = '<div class="empty-state">No hay productos relacionados.</div>';
                return;
            }

            grid.innerHTML = this.related
                .map((item) => {
                    const img = item.imagen
                        ? `<img src="${item.imagen}" alt="${item.nombre}" />`
                        : '<div class="placeholder-image">💅</div>';
                    return `
                        <div class="product-card">
                            <div class="product-image">${img}</div>
                            <h3>${item.nombre}</h3>
                            <p>${item.descripcion || ''}</p>
                            <span class="price">$${formatPrice(item.precio)}</span>
                            <div class="product-badges">
                                ${item.marca ? `<span class="badge">${item.marca}</span>` : ''}
                                ${item.categoria ? `<span class="badge">${item.categoria}</span>` : ''}
                            </div>
                            <a class="btn-primary" style="width:100%; margin-top:12px; display:inline-block; text-align:center;" href="/detalle_producto.html?id=${item.id}">Ver Detalle</a>
                        </div>
                    `;
                })
                .join('');
        },

        bindActions() {
            const qtyInput = document.getElementById('quantity');
            const btnUp = document.getElementById('qty-up');
            const btnDown = document.getElementById('qty-down');
            const btnAdd = document.getElementById('btn-add-cart');
            const maxStock = Number(this.product?.stock || 0);

            if (btnUp && qtyInput) {
                btnUp.addEventListener('click', () => {
                    const next = Math.min(maxStock || 1, this.quantity + 1);
                    this.quantity = Math.max(1, next);
                    qtyInput.value = String(this.quantity);
                });
            }

            if (btnDown && qtyInput) {
                btnDown.addEventListener('click', () => {
                    this.quantity = Math.max(1, this.quantity - 1);
                    qtyInput.value = String(this.quantity);
                });
            }

            if (btnAdd) {
                btnAdd.addEventListener('click', async () => {
                    const inventoryId = this.product?.inventario_id;
                    if (!inventoryId) {
                        window.CartUI?.toast('Este producto no tiene inventario asociado', 'error');
                        return;
                    }

                    if (!window.NAILSNICE_IS_AUTH) {
                        const next = encodeURIComponent(window.location.pathname + window.location.search);
                        window.location.href = `/login/?next=${next}`;
                        return;
                    }

                    try {
                        let csrfToken = await ensureCSRFToken();
                        const resp = await fetch(`/carrito/agregar/${inventoryId}/`, {
                            method: 'POST',
                            credentials: 'same-origin',
                            headers: {
                                'X-CSRFToken': csrfToken,
                                'X-Requested-With': 'XMLHttpRequest',
                                'Content-Type': 'application/x-www-form-urlencoded',
                            },
                            body: new URLSearchParams({
                                cantidad: String(this.quantity),
                                csrfmiddlewaretoken: csrfToken,
                            }),
                        });

                        let data = {};
                        try {
                            data = await resp.json();
                        } catch (e) {
                            data = {};
                        }

                        if (resp.status === 403) {
                            await refreshCSRFToken();
                            csrfToken = getCSRFToken();
                            const retryResp = await fetch(`/carrito/agregar/${inventoryId}/`, {
                                method: 'POST',
                                credentials: 'same-origin',
                                headers: {
                                    'X-CSRFToken': csrfToken,
                                    'X-Requested-With': 'XMLHttpRequest',
                                    'Content-Type': 'application/x-www-form-urlencoded',
                                },
                                body: new URLSearchParams({
                                    cantidad: String(this.quantity),
                                    csrfmiddlewaretoken: csrfToken,
                                }),
                            });
                            try {
                                data = await retryResp.json();
                            } catch (e) {
                                data = {};
                            }
                            if (!retryResp.ok) {
                                window.CartUI?.toast(data.error || 'No se pudo validar seguridad. Recarga la pagina e intenta de nuevo.', 'error');
                                return;
                            }
                        }

                        if (data.ok) {
                            if (typeof data.cart_count !== 'undefined') window.CartUI?.setCount(data.cart_count);
                            window.CartUI?.toast('Producto agregado al carrito');
                        } else {
                            window.CartUI?.toast(data.error || 'No se pudo agregar al carrito', 'error');
                        }
                    } catch (error) {
                        window.CartUI?.toast('Error de conexión al agregar al carrito', 'error');
                    }
                });
            }
        },

        init() {
            if (!this.product) {
                renderError('Producto no disponible.');
                return;
            }
            this.renderMain();
            this.renderRelated();
            this.bindActions();
        },
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => ProductDetail.init());
    } else {
        ProductDetail.init();
    }
})();