/**
 * Profesional Beauty - Productos Page Script
 * Gestiona: filtros dinámicos, búsqueda, productos, paginación, modal, carrito.
 */

const CONFIG = {
    apiBaseUrl: '/api',
    productsPerPage: 12,
    debounceDelay: 300,
    inventoryEndpoint: 'inventario-productos',
};

const FILTER_QUERY_KEYS = ['search', 'q', 'categoria', 'categoria_id', 'disponibilidad', 'precio_min', 'precio_max', 'view'];

const hasMeaningfulQueryFilters = () => {
    const params = new URLSearchParams(window.location.search);
    return FILTER_QUERY_KEYS.some((key) => {
        const raw = params.get(key);
        return raw !== null && String(raw).trim() !== '';
    });
};

const DEFAULT_FILTERS = () => ({
    search: '',
    marcas: [],
    categorias: [],
    colores: [],
    estado: 'Todos',
    disponibilidad: 'Todos',
    priceMin: 0,
    priceMax: Infinity,
});

window.addEventListener('error', () => {
    document.querySelectorAll('.reveal').forEach((el) => el.classList.add('reveal--visible'));
    const grid = document.getElementById('products-grid');
    if (grid && !grid.children.length) {
        grid.innerHTML = '<div class="empty-state" style="grid-column:1/-1; padding: 80px 20px;">Error de render en productos. Reintenta la carga.</div>';
    }
});

function getCSRFToken() {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    if (match) return match[1];

    const meta = document.querySelector('meta[name="csrf-token"]');
    const metaToken = (meta?.getAttribute('content') || '').trim();
    if (metaToken && metaToken !== 'NOTPROVIDED') return metaToken;

    const hiddenInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
    return (hiddenInput?.value || '').trim();
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

async function fetchAll(endpoint) {
    let results = [];
    let url = `${CONFIG.apiBaseUrl}/${endpoint}/`;
    while (url) {
        const res = await fetch(url);
        if (!res.ok) throw new Error(`No se pudo cargar ${endpoint}`);
        const data = await res.json();
        const pageResults = Array.isArray(data) ? data : (data.results || []);
        results = results.concat(pageResults);
        url = data.next || null;
    }
    return results;
}

const Utils = {
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    formatPrice(price) {
        return price.toLocaleString('es-CO');
    },

    normalizeText(value) {
        return String(value || '')
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .trim()
            .toLowerCase();
    },

    normalizeImageUrl(value) {
        const raw = String(value || '').trim().replace(/\\/g, '/');
        if (!raw) return '';
        if (/^https?:\/\//i.test(raw)) return raw;

        let url = raw;
        if (!url.startsWith('/')) {
            url = `/${url}`;
        }

        while (/^\/media\/\/media\//i.test(url)) {
            url = url.replace(/^\/media\/\/media\//i, '/media/');
        }
        if (/^\/media\/media\//i.test(url)) {
            url = url.replace(/^\/media\/media\//i, '/media/');
        }
        return url;
    },
};

const AppState = {
    allProducts: [],
    filteredProducts: [],
    currentPage: 1,
    isLoading: false,
    inventory: [],
    inventoryById: new Map(),
    inventoryByName: new Map(),
    catalogs: { marcas: [], categorias: [], colores: [] },
    maps: { categoriaIdToName: new Map(), marcaIdToName: new Map(), colorIdToName: new Map() },
    filters: DEFAULT_FILTERS(),
    sort: 'reciente',
    viewMode: 'grid',

    resetToDefaults() {
        this.filters = DEFAULT_FILTERS();
        this.sort = 'reciente';
        this.currentPage = 1;
        this.viewMode = 'grid';
    },

    init() {
        this.resetToDefaults();
        this.loadFromURL();
    },

    loadFromURL() {
        const params = new URLSearchParams(window.location.search);
        this.filters.search = params.get('search') || params.get('q') || this.filters.search;
        const categoryName = (params.get('categoria') || '').trim();
        const categoryId = (params.get('categoria_id') || '').trim();
        const disponibilidad = (params.get('disponibilidad') || '').trim();
        const view = (params.get('view') || '').trim();
        const minParam = params.get('precio_min');
        const maxParam = params.get('precio_max');
        const hasMinParam = minParam !== null && String(minParam).trim() !== '';
        const hasMaxParam = maxParam !== null && String(maxParam).trim() !== '';

        const minParsed = Number(minParam);
        const maxParsed = Number(maxParam);
        if (hasMinParam && Number.isFinite(minParsed) && minParsed >= 0) {
            this.filters.priceMin = minParsed;
        }
        if (hasMaxParam && Number.isFinite(maxParsed) && maxParsed >= 0) {
            this.filters.priceMax = maxParsed;
        }
        if (this.filters.priceMax < this.filters.priceMin) {
            this.filters.priceMax = Infinity;
        }

        if (categoryId) this.filters.categorias = ['ID:' + categoryId];
        else if (categoryName) this.filters.categorias = [categoryName];

        if (disponibilidad === 'disponible' || disponibilidad === 'agotado') {
            this.filters.disponibilidad = disponibilidad;
            const availabilityEl = document.getElementById('filter-disponibilidad');
            if (availabilityEl) availabilityEl.value = disponibilidad;
        }

        if (view === 'grid' || view === 'compact' || view === 'list') {
            this.viewMode = view;
        }

        if (this.filters.search) {
            const searchInput = document.getElementById('products-search-top');
            if (searchInput) searchInput.value = this.filters.search;
        }

        const priceMinInput = document.getElementById('filter-price-min');
        const priceMaxInput = document.getElementById('filter-price-max');
        if (priceMinInput && Number.isFinite(this.filters.priceMin) && this.filters.priceMin > 0) {
            priceMinInput.value = String(this.filters.priceMin);
        }
        if (priceMaxInput && Number.isFinite(this.filters.priceMax) && this.filters.priceMax !== Infinity) {
            priceMaxInput.value = String(this.filters.priceMax);
        }
    },

    updateURL() {
        const params = new URLSearchParams();
        if (this.filters.search) params.append('search', this.filters.search);
        if (this.filters.categorias.length) {
            const selectedRaw = String(this.filters.categorias[0] || '').trim();
            const selectedId = selectedRaw.replace(/^ID:/i, '');
            if (/^\d+$/.test(selectedId)) {
                params.append('categoria_id', selectedId);
            } else {
                const normalizedSelected = Utils.normalizeText(selectedRaw);
                const catalogMatch = (this.catalogs.categorias || []).find(([, name]) => {
                    const normalizedName = Utils.normalizeText(name || '');
                    return (
                        normalizedSelected &&
                        normalizedName &&
                        (normalizedName === normalizedSelected || normalizedName.includes(normalizedSelected) || normalizedSelected.includes(normalizedName))
                    );
                });
                if (catalogMatch && /^\d+$/.test(String(catalogMatch[0]))) {
                    params.append('categoria_id', String(catalogMatch[0]));
                } else if (selectedRaw) {
                    params.append('categoria', selectedRaw);
                }
            }
        }
        if (this.filters.disponibilidad && this.filters.disponibilidad !== 'Todos') {
            params.append('disponibilidad', this.filters.disponibilidad);
        }
        if (Number.isFinite(this.filters.priceMin) && this.filters.priceMin > 0) {
            params.append('precio_min', String(this.filters.priceMin));
        }
        if (Number.isFinite(this.filters.priceMax) && this.filters.priceMax !== Infinity) {
            params.append('precio_max', String(this.filters.priceMax));
        }
        if (this.viewMode && this.viewMode !== 'grid') {
            params.append('view', this.viewMode);
        }
        const qs = params.toString();
        window.history.replaceState({}, '', qs ? `?${qs}` : window.location.pathname);
    },
};

const CartActions = (() => {
    const goLogin = () => {
        const next = encodeURIComponent(window.location.pathname + window.location.search);
        window.location.href = `/login/?next=${next}`;
    };

    const add = async (product, retryOnCsrf = true) => {
        if (!product || !product.id_inventario) {
            CartUI?.toast('No se pudo mapear el inventario de este producto', 'error');
            return { ok: false };
        }
        if (!window.NAILSNICE_IS_AUTH) {
            goLogin();
            return { ok: false };
        }
        try {
            const csrfToken = await ensureCSRFToken();
            const res = await fetch(`/carrito/agregar/${product.id_inventario}/`, {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest',
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams({
                    cantidad: 1,
                    csrfmiddlewaretoken: csrfToken,
                }),
            });

            if (res.redirected && res.url.includes('/login')) {
                window.location.href = res.url;
                return { ok: false };
            }

            const rawText = await res.text();
            let data = {};
            try {
                data = JSON.parse(rawText || '{}');
            } catch (err) {
                data = {};
            }

            if (res.status === 403) {
                if (retryOnCsrf) {
                    await refreshCSRFToken();
                    return add(product, false);
                }
                CartUI?.toast('No se pudo validar seguridad. Recarga la página e intenta de nuevo.', 'error');
                return { ok: false };
            }

            if (data.ok) {
                if (typeof data.cart_count !== 'undefined') {
                    CartUI?.setCount(data.cart_count);
                } else {
                    CartUI?.increment(1);
                }
                CartUI?.toast('Producto agregado al carrito');
                return { ok: true };
            } else {
                CartUI?.toast(data.error || 'No se pudo agregar al carrito', 'error');
                return { ok: false };
            }
        } catch (err) {
            CartUI?.toast('No se pudo agregar al carrito', 'error');
            return { ok: false };
        }
    };

    return { add };
})();

const Products = (() => {
    const container = document.getElementById('products-grid');
    const countDisplay = document.getElementById('products-count');

    const sortProducts = (products) => {
        const sorted = [...products];
        switch (AppState.sort) {
            case 'precio-asc':
                sorted.sort((a, b) => a.precio - b.precio);
                break;
            case 'precio-desc':
                sorted.sort((a, b) => b.precio - a.precio);
                break;
            case 'nombre-asc':
                sorted.sort((a, b) => a.nombre.localeCompare(b.nombre, 'es'));
                break;
            default:
                sorted.sort((a, b) => new Date(b.creado_en).getTime() - new Date(a.creado_en).getTime());
                break;
        }
        return sorted;
    };

    const extractIdValue = (rawValue) => {
        const raw = String(rawValue || '').trim();
        if (!raw) return '';
        return raw.replace(/^ID:/i, '');
    };

    const matchesSelection = (selectedValues, productLabel, productId, idToNameMap) => {
        if (!selectedValues.length) return true;

        const productIdText = String(productId || '').trim();
        const productLabelNorm = Utils.normalizeText(productLabel || '');

        return selectedValues.some((selectedRaw) => {
            const selectedText = String(selectedRaw || '').trim();
            if (!selectedText) return false;

            const selectedId = extractIdValue(selectedText);
            if (productIdText && /^\d+$/.test(selectedId) && selectedId === productIdText) {
                return true;
            }

            if (/^\d+$/.test(selectedId) && idToNameMap instanceof Map) {
                const mappedNameNorm = Utils.normalizeText(idToNameMap.get(String(selectedId)) || '');
                if (
                    mappedNameNorm &&
                    productLabelNorm &&
                    (productLabelNorm === mappedNameNorm ||
                        productLabelNorm.includes(mappedNameNorm) ||
                        mappedNameNorm.includes(productLabelNorm))
                ) {
                    return true;
                }
            }

            const selectedNorm = Utils.normalizeText(selectedText.replace(/^ID:/i, ''));
            if (!selectedNorm || !productLabelNorm) return false;
            return (
                productLabelNorm === selectedNorm ||
                productLabelNorm.includes(selectedNorm) ||
                selectedNorm.includes(productLabelNorm)
            );
        });
    };

    const createProductCard = (product) => {
        const card = document.createElement('div');
        card.className = 'product-card reveal product-card--interactive';

        const imageHtml = product.imagen
            ? `<img src="${product.imagen}" alt="${product.nombre}" loading="lazy" />`
            : '';

        const stockLabel = product.stock > 0 ? `Stock: ${product.stock}` : 'Sin stock';

        card.innerHTML = `
            <div class="product-image">
                ${imageHtml}
                ${!imageHtml ? '<div class="placeholder-image">💅</div>' : ''}
            </div>
            <h3>${product.nombre}</h3>
            <p>${product.descripcion}</p>
            <span class="price">$${Utils.formatPrice(product.precio)}</span>
            <div class="product-badges">
                ${product.marca ? `<span class="badge">${product.marca}</span>` : ''}
                ${product.categoria ? `<span class="badge">${product.categoria}</span>` : ''}
                ${product.color ? `<span class="badge">${product.color}</span>` : ''}
            </div>
            <div class="product-meta">
                <span class="stock-chip ${product.stock > 0 ? 'is-available' : 'is-out'}">${stockLabel}</span>
            </div>
            <div class="product-actions-row">
                <button type="button" class="btn-primary btn-add-cart" ${product.stock > 0 ? '' : 'disabled'}>Agregar al carrito</button>
            </div>
        `;

        card.addEventListener('click', () => {
            window.location.href = `/detalle_producto.html?id=${product.id}`;
        });
        const addBtn = card.querySelector('.btn-add-cart');
        if (addBtn) {
            addBtn.addEventListener('click', async (ev) => {
                ev.stopPropagation();
                if (addBtn.disabled) return;
                const originalText = addBtn.textContent;
                addBtn.disabled = true;
                addBtn.textContent = 'Agregando...';
                await CartActions.add(product);
                addBtn.textContent = originalText;
                addBtn.disabled = Number(product.stock || 0) <= 0;
            });
        }
        return card;
    };

    const populateFilterOptions = () => {
        Filters.updateAvailableOptions({
            marcas: new Map(AppState.catalogs.marcas),
            categorias: new Map(AppState.catalogs.categorias),
            colores: new Map(AppState.catalogs.colores),
        });
    };

    const renderSkeletons = (count = 12) => {
        container.innerHTML = '';
        for (let i = 0; i < count; i += 1) {
            const item = document.createElement('div');
            item.className = 'product-card skeleton reveal';
            container.appendChild(item);
        }
        if (countDisplay) countDisplay.textContent = 'Cargando productos...';
    };

    const applyViewMode = () => {
        container.classList.remove('view-grid', 'view-compact', 'view-list');
        const mode = AppState.viewMode || 'grid';
        container.classList.add(`view-${mode}`);
        document.querySelectorAll('.view-switch__btn').forEach((btn) => {
            btn.classList.toggle('is-active', btn.dataset.viewMode === mode);
        });
    };

    const renderActiveFilters = () => {
        const chipsWrap = document.getElementById('active-filters');
        if (!chipsWrap) return;

        const chips = [];
        if (AppState.filters.search) chips.push(`Busqueda: ${AppState.filters.search}`);
        if (AppState.filters.categorias.length) chips.push(`Categorias: ${AppState.filters.categorias.length}`);
        if (AppState.filters.marcas.length) chips.push(`Marcas: ${AppState.filters.marcas.length}`);
        if (AppState.filters.colores.length) chips.push(`Colores: ${AppState.filters.colores.length}`);
        if (AppState.filters.disponibilidad !== 'Todos') chips.push(`Disponibilidad: ${AppState.filters.disponibilidad}`);
        if (AppState.filters.estado !== 'Todos') chips.push(`Estado: ${AppState.filters.estado}`);
        if (AppState.filters.priceMin > 0 || AppState.filters.priceMax !== Infinity) {
            const maxLabel = AppState.filters.priceMax === Infinity ? 'max' : AppState.filters.priceMax;
            chips.push(`Precio: ${AppState.filters.priceMin} - ${maxLabel}`);
        }

        if (!chips.length) {
            chipsWrap.innerHTML = '';
            return;
        }

        chipsWrap.innerHTML = chips.map((chip) => `<span class="filter-chip">${chip}</span>`).join('');
    };

    const updateCount = () => {
        const total = AppState.filteredProducts.length;
        if (countDisplay) {
            countDisplay.textContent = `${total} producto${total !== 1 ? 's' : ''} encontrado${total !== 1 ? 's' : ''}`;
        }
    };

    const render = () => {
        applyViewMode();
        renderActiveFilters();
        const start = (AppState.currentPage - 1) * CONFIG.productsPerPage;
        const end = start + CONFIG.productsPerPage;
        const paginated = AppState.filteredProducts.slice(start, end);

        container.classList.add('is-rendering');
        container.innerHTML = '';

        if (!paginated.length) {
            container.innerHTML = `
                <div class="empty-state" style="grid-column: 1/-1; padding: 80px 20px;">
                    <p>No hay productos con estos filtros.</p>
                    <button id="empty-reset-filters" type="button" class="btn-secondary">Ver todo</button>
                </div>
            `;
            const resetBtn = document.getElementById('empty-reset-filters');
            if (resetBtn) {
                resetBtn.addEventListener('click', () => {
                    Filters.resetAll(true);
                });
            }
            Pagination.render();
            window.setTimeout(() => container.classList.remove('is-rendering'), 180);
            return;
        }

        paginated.forEach((p) => container.appendChild(createProductCard(p)));
        ScrollReveal.init();
        Pagination.render();
        window.setTimeout(() => container.classList.remove('is-rendering'), 180);
    };

    const applyFilters = () => {
        let filtered = [...AppState.allProducts];

        if (AppState.filters.search) {
            const searchLower = AppState.filters.search.toLowerCase();
            filtered = filtered.filter(
                (p) =>
                    (p.nombre || '').toLowerCase().includes(searchLower) ||
                    (p.descripcion || '').toLowerCase().includes(searchLower) ||
                    (p.marca || '').toLowerCase().includes(searchLower)
            );
        }

        if (AppState.filters.marcas.length) {
            filtered = filtered.filter((p) => matchesSelection(AppState.filters.marcas, p.marca, p.id_marca, AppState.maps.marcaIdToName));
        }
        if (AppState.filters.categorias.length) {
            filtered = filtered.filter((p) =>
                matchesSelection(AppState.filters.categorias, p.categoria, p.id_categoria, AppState.maps.categoriaIdToName)
            );
        }
        if (AppState.filters.colores.length) {
            filtered = filtered.filter((p) => matchesSelection(AppState.filters.colores, p.color, p.id_color, AppState.maps.colorIdToName));
        }

        if (AppState.filters.estado !== 'Todos') {
            filtered = filtered.filter((p) => p.estado === AppState.filters.estado);
        }

        if (AppState.filters.disponibilidad === 'disponible') {
            filtered = filtered.filter((p) => Number(p.stock || 0) > 0);
        }
        if (AppState.filters.disponibilidad === 'agotado') {
            filtered = filtered.filter((p) => Number(p.stock || 0) <= 0);
        }

        filtered = filtered.filter((p) => p.precio >= AppState.filters.priceMin && p.precio <= AppState.filters.priceMax);

        filtered = sortProducts(filtered);

        AppState.filteredProducts = filtered;
        AppState.currentPage = 1;
        populateFilterOptions();
        AppState.updateURL();
        render();
        updateCount();
    };

    return {
        async init() {
            if (!container) return;
            AppState.isLoading = true;
            renderSkeletons(12);
            try {
                const [products, marcas, categorias] = await Promise.all([
                    fetchAll('productos'),
                    fetchAll('marcas'),
                    fetchAll('categorias'),
                ]);
                
                const inventario = [];
                const colores = [];

                const categoriaMap = new Map((categorias || []).map((c) => [String(c.id), c.nombre_categoria]));
                const marcaMap = new Map((marcas || []).map((m) => [String(m.id), m.nombre_marca]));
                const colorMap = new Map((colores || []).map((c) => [String(c.id), c.nombre_color]));

                const inventarioById = new Map((inventario || []).map((p) => [String(p.id_inventario), p]));
                const inventarioByName = new Map((inventario || []).map((p) => [(p.nombre || '').toLowerCase(), p]));
                AppState.inventory = inventario || [];
                AppState.inventoryById = inventarioById;
                AppState.inventoryByName = inventarioByName;

                AppState.catalogs = {
                    marcas: Array.from(marcaMap.entries()),
                    categorias: Array.from(categoriaMap.entries()),
                    colores: Array.from(colorMap.entries()),
                };
                AppState.maps = { categoriaIdToName: categoriaMap, marcaIdToName: marcaMap, colorIdToName: colorMap };

                if (AppState.filters.categorias.length === 1) {
                    const selectedCategory = String(AppState.filters.categorias[0] || '').trim();
                    const selectedCategoryId = selectedCategory.replace(/^ID:/i, '');
                    if (/^\d+$/.test(selectedCategoryId)) {
                        AppState.filters.categorias = ['ID:' + selectedCategoryId];
                    } else if (selectedCategory) {
                        const normalizedSelected = Utils.normalizeText(selectedCategory);
                        const matchedCategory = AppState.catalogs.categorias.find(([, name]) => {
                            const normalizedName = Utils.normalizeText(name || '');
                            return (
                                normalizedSelected &&
                                normalizedName &&
                                (normalizedName === normalizedSelected || normalizedName.includes(normalizedSelected) || normalizedSelected.includes(normalizedName))
                            );
                        });
                        if (matchedCategory) {
                            AppState.filters.categorias = ['ID:' + String(matchedCategory[0])];
                        }
                    }
                }

                AppState.allProducts = (products || []).map((p) => {
                    const invPk = p.inventario || p.id_inventario || p.id;
                    const invMatch = inventarioById.get(String(invPk)) || inventarioByName.get((p.nombre || '').toLowerCase());
                    const mappedId = invMatch?.id_inventario || p.inventario || p.id_inventario || p.id;
                    const mappedStock = invMatch ? Number(invMatch.stock || 0) : Number(p.stock || 0) || 0;
                    const categoriaId = p.id_categoria || p.categoria?.id || null;
                    const marcaId = p.id_marca || p.marca?.id || null;
                    const colorId = p.id_color || p.color?.id || null;

                    return {
                        id: p.id,
                        nombre: p.nombre,
                        descripcion: p.descripcion,
                        precio: Number(p.precio || 0),
                        imagen: Utils.normalizeImageUrl(p.imagen || invMatch?.imagen || ''),
                        estado: p.estado_producto,
                        categoria: (p.categoria && p.categoria.nombre_categoria) || categoriaMap.get(String(categoriaId)) || '',
                        marca: (p.marca && p.marca.nombre_marca) || marcaMap.get(String(marcaId)) || '',
                        color: (p.color && p.color.nombre_color) || colorMap.get(String(colorId)) || '',
                        id_categoria: categoriaId,
                        id_marca: marcaId,
                        id_color: colorId,
                        creado_en: p.creado_en,
                        id_inventario: mappedId,
                        stock: mappedStock,
                    };
                });
                if (!hasMeaningfulQueryFilters()) {
                    AppState.resetToDefaults();
                    Filters.syncUI?.();
                }

                AppState.isLoading = false;
                populateFilterOptions();
                applyFilters();

                if (!AppState.filteredProducts.length && !hasMeaningfulQueryFilters()) {
                    AppState.resetToDefaults();
                    Filters.syncUI?.();
                    applyFilters();
                }
            } catch (err) {
                console.error(err);
                container.innerHTML = '<div class="empty-state">Error al cargar productos</div>';
                if (countDisplay) countDisplay.textContent = 'No se pudieron cargar productos';
            } finally {
                AppState.isLoading = false;
            }
        },
        applyFilters,
        render,
    };
})();

const Filters = (() => {
    const debouncedFilter = Utils.debounce(() => {
        Products.applyFilters();
    }, CONFIG.debounceDelay);

    const syncControlsFromState = () => {
        const searchInput = document.getElementById('products-search-top');
        const sortSelect = document.getElementById('filter-sort');
        const estadoSelect = document.getElementById('filter-estado');
        const disponibilidadSelect = document.getElementById('filter-disponibilidad');
        const minInput = document.getElementById('filter-price-min');
        const maxInput = document.getElementById('filter-price-max');

        if (searchInput) searchInput.value = AppState.filters.search || '';
        if (sortSelect) sortSelect.value = AppState.sort;
        if (estadoSelect) estadoSelect.value = AppState.filters.estado;
        if (disponibilidadSelect) disponibilidadSelect.value = AppState.filters.disponibilidad;
        if (minInput) minInput.value = AppState.filters.priceMin > 0 ? String(AppState.filters.priceMin) : '';
        if (maxInput) maxInput.value = AppState.filters.priceMax !== Infinity ? String(AppState.filters.priceMax) : '';

        document.querySelectorAll('.view-switch__btn').forEach((btn) => {
            btn.classList.toggle('is-active', btn.dataset.viewMode === AppState.viewMode);
        });
    };

    const setupSearch = () => {
        const searchInput = document.getElementById('products-search-top');
        const suggestions = document.getElementById('products-suggestions');

        const closeSuggestions = () => {
            if (!suggestions) return;
            suggestions.innerHTML = '';
            suggestions.classList.remove('is-open');
        };

        const fetchSuggestions = Utils.debounce(async (term) => {
            if (!suggestions) return;
            const q = (term || '').trim();
            if (!q) {
                closeSuggestions();
                return;
            }

            try {
                const resp = await fetch(`/api/productos-buscar/?q=${encodeURIComponent(q)}&limit=6`);
                if (!resp.ok) {
                    closeSuggestions();
                    return;
                }
                const data = await resp.json();
                const items = data.productos || [];
                const categories = data.categorias || [];
                if (!items.length && !categories.length) {
                    closeSuggestions();
                    return;
                }

                const productsHtml = items
                    .map((m) => {
                        const stock = Number(m.stock || 0) > 0 ? 'Con stock' : 'Sin stock';
                        return `<button type="button" class="suggestion-item" data-name="${m.nombre}">${m.nombre} · ${m.categoria || 'Sin categoría'} · ${stock}</button>`;
                    })
                    .join('');

                const categoriesHtml = categories
                    .map((c) => {
                        const id = String(c.id || '');
                        const name = c.nombre_categoria || '';
                        return `<button type="button" class="suggestion-item" data-category-id="${id}" data-category-name="${name}">${name} · Categoría</button>`;
                    })
                    .join('');

                suggestions.innerHTML = `${productsHtml}${categoriesHtml}`;
                suggestions.classList.add('is-open');
                suggestions.querySelectorAll('.suggestion-item').forEach((btn) => {
                    btn.addEventListener('click', () => {
                        const selectedCategoryId = btn.dataset.categoryId || '';
                        const selectedCategoryName = btn.dataset.categoryName || '';
                        if (selectedCategoryId) {
                            AppState.filters.categorias = ['ID:' + selectedCategoryId];
                            searchInput.value = selectedCategoryName;
                            AppState.filters.search = '';
                            Products.applyFilters();
                            closeSuggestions();
                            return;
                        }

                        const value = btn.dataset.name || '';
                        searchInput.value = value;
                        AppState.filters.search = value;
                        Products.applyFilters();
                        closeSuggestions();
                    });
                });
            } catch (err) {
                closeSuggestions();
            }
        }, 180);

        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                AppState.filters.search = e.target.value;
                AppState.updateURL();
                debouncedFilter();
                fetchSuggestions(e.target.value || '');
            });

            document.addEventListener('click', (e) => {
                if (!suggestions) return;
                if (e.target === searchInput || suggestions.contains(e.target)) return;
                closeSuggestions();
            });
        }
    };

    const setupSort = () => {
        const sortSelect = document.getElementById('filter-sort');
        if (sortSelect) {
            sortSelect.addEventListener('change', (e) => {
                AppState.sort = e.target.value;
                Products.applyFilters();
            });
        }
    };

    const setupChecklistFilters = () => {
        const setupFilter = (containerId, filterName) => {
            const container = document.getElementById(containerId);
            if (!container) return;

            container.addEventListener('change', (e) => {
                if (e.target.type === 'checkbox') {
                    const value = String(e.target.value || '').trim();
                    if (!value) return;
                    const isChecked = e.target.checked;

                    if (isChecked) {
                        if (!AppState.filters[filterName].includes(value)) {
                            AppState.filters[filterName].push(value);
                        }
                    } else {
                        AppState.filters[filterName] = AppState.filters[filterName].filter((v) => v !== value);
                    }

                    debouncedFilter();
                }
            });
        };

        setupFilter('filter-marcas', 'marcas');
        setupFilter('filter-categorias', 'categorias');
        setupFilter('filter-colores', 'colores');
    };

    const setupStateFilter = () => {
        const estadoSelect = document.getElementById('filter-estado');
        if (estadoSelect) {
            estadoSelect.addEventListener('change', (e) => {
                AppState.filters.estado = e.target.value;
                Products.applyFilters();
            });
        }
    };

    const setupAvailabilityFilter = () => {
        const disponibilidadSelect = document.getElementById('filter-disponibilidad');
        if (disponibilidadSelect) {
            disponibilidadSelect.addEventListener('change', (e) => {
                AppState.filters.disponibilidad = e.target.value;
                Products.applyFilters();
            });
        }
    };

    const setupPriceFilter = () => {
        const priceMinInput = document.getElementById('filter-price-min');
        const priceMaxInput = document.getElementById('filter-price-max');

        const handlePriceChange = () => {
            AppState.filters.priceMin = parseInt(priceMinInput?.value) || 0;
            AppState.filters.priceMax = parseInt(priceMaxInput?.value) || Infinity;
            debouncedFilter();
        };

        priceMinInput?.addEventListener('input', handlePriceChange);
        priceMaxInput?.addEventListener('input', handlePriceChange);
        priceMinInput?.addEventListener('change', handlePriceChange);
        priceMaxInput?.addEventListener('change', handlePriceChange);
    };

    const resetAll = (scrollTop = false) => {
        AppState.resetToDefaults();

        document.querySelectorAll('.checklist input[type="checkbox"]').forEach((cb) => {
            cb.checked = false;
        });

        syncControlsFromState();
        Products.applyFilters();

        if (scrollTop) {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
    };

    const setupResetButton = () => {
        const resetBtn = document.getElementById('filter-reset');
        const resetTopBtn = document.getElementById('filter-reset-top');
        if (resetBtn) resetBtn.addEventListener('click', () => resetAll(false));
        if (resetTopBtn) resetTopBtn.addEventListener('click', () => resetAll(true));
    };

    const setupViewModeSwitch = () => {
        const buttons = document.querySelectorAll('.view-switch__btn');
        buttons.forEach((btn) => {
            btn.addEventListener('click', () => {
                const mode = btn.dataset.viewMode;
                if (!mode) return;
                AppState.viewMode = mode;
                syncControlsFromState();
                AppState.updateURL();
                Products.render();
            });
        });
    };

    const renderChecklist = (containerId, options, selected = []) => {
        const container = document.getElementById(containerId);
        if (!container) return;

        const fragment = document.createDocumentFragment();

        options.forEach(([value, labelText]) => {
            const rawValue = String(value || '').trim();
            const optionValue = /^\d+$/.test(rawValue) ? `ID:${rawValue}` : rawValue;
            const isSelected = selected.includes(optionValue) || selected.includes(rawValue);
            const labelEl = document.createElement('label');
            labelEl.innerHTML = `
                <input type="checkbox" value="${optionValue}" ${isSelected ? 'checked' : ''} />
                <span>${labelText}</span>
            `;
            fragment.appendChild(labelEl);
        });

        container.innerHTML = '';
        container.appendChild(fragment);
    };

    return {
        init() {
            syncControlsFromState();
            setupSearch();
            setupSort();
            setupChecklistFilters();
            setupStateFilter();
            setupAvailabilityFilter();
            setupPriceFilter();
            setupResetButton();
            setupViewModeSwitch();
        },

        updateAvailableOptions(available) {
            const marcas = Array.from(available.marcas?.entries?.() || []);
            const categorias = Array.from(available.categorias?.entries?.() || []);
            const colores = Array.from(available.colores?.entries?.() || []);

            renderChecklist('filter-marcas', marcas, AppState.filters.marcas);
            renderChecklist('filter-categorias', categorias, AppState.filters.categorias);
            renderChecklist('filter-colores', colores, AppState.filters.colores);
        },

        resetAll,
        syncUI: syncControlsFromState,
    };
})();

const Pagination = (() => {
    const container = document.getElementById('products-pagination');

    const render = () => {
        if (!container) return;

        const totalPages = Math.ceil(AppState.filteredProducts.length / CONFIG.productsPerPage);

        if (totalPages <= 1) {
            container.innerHTML = '';
            return;
        }

        const buttons = [];

        if (AppState.currentPage > 1) {
            buttons.push(`<button class="pagination-btn" data-page="${AppState.currentPage - 1}">← Anterior</button>`);
        }

        for (let i = 1; i <= totalPages; i++) {
            const isActive = i === AppState.currentPage ? 'active' : '';
            buttons.push(`<button class="pagination-btn ${isActive}" data-page="${i}">${i}</button>`);
        }

        if (AppState.currentPage < totalPages) {
            buttons.push(`<button class="pagination-btn" data-page="${AppState.currentPage + 1}">Siguiente →</button>`);
        }

        container.innerHTML = buttons.join('');
    };

    const attach = () => {
        if (!container) return;
        container.addEventListener('click', (e) => {
            if (e.target.matches('button[data-page]')) {
                AppState.currentPage = parseInt(e.target.dataset.page, 10);
                Products.render();
                Pagination.render();
            }
        });
    };

    return { render, attach };
})();

const ScrollReveal = (() => {
    const init = () => {
        document.querySelectorAll('.reveal').forEach((el) => el.classList.add('reveal--visible'));
    };
    return { init };
})();

const Modal = (() => {
    const modal = document.getElementById('product-modal');
    if (!modal) return { open: () => {}, close: () => {}, init: () => {} };

    const close = () => {
        modal.classList.remove('is-open');
        modal.setAttribute('aria-hidden', 'true');
    };

    const open = (product) => {
        const img = modal.querySelector('#modal-image');
        const fallback = modal.querySelector('#modal-image-fallback');
        const title = modal.querySelector('#modal-title');
        const desc = modal.querySelector('#modal-description');
        const price = modal.querySelector('#modal-price');
        const badges = modal.querySelector('#modal-badges');

        if (img) {
            if (product.imagen) {
                img.src = product.imagen;
                img.alt = product.nombre;
                img.parentElement.classList.add('is-having-image');
            } else {
                img.src = '';
                img.alt = '';
                img.parentElement.classList.remove('is-having-image');
            }
        }
        if (fallback) fallback.textContent = product.nombre || 'Profesional Beauty';
        if (title) title.textContent = product.nombre || '';
        if (desc) desc.textContent = product.descripcion || '';
        if (price) price.textContent = `$${Utils.formatPrice(product.precio || 0)}`;
        if (badges) {
            badges.innerHTML = '';
            ['marca', 'categoria', 'color'].forEach((key) => {
                if (product[key]) {
                    const span = document.createElement('span');
                    span.className = 'badge';
                    span.textContent = product[key];
                    badges.appendChild(span);
                }
            });
        }

        modal.classList.add('is-open');
        modal.setAttribute('aria-hidden', 'false');
    };

    const init = () => {
        modal.addEventListener('click', (e) => {
            if (e.target.dataset.close === 'true' || e.target.classList.contains('modal-backdrop')) {
                close();
            }
        });
    };

    return { open, close, init };
})();

window.addEventListener('DOMContentLoaded', () => {
    AppState.init();
    Filters.init();
    Products.init();
    Pagination.attach();
    Modal.init();
});

window.addEventListener('pageshow', (event) => {
    if (!event.persisted) return;

    if (!hasMeaningfulQueryFilters()) {
        AppState.resetToDefaults();
        Filters.syncUI?.();
    }

    if (AppState.allProducts.length) {
        Products.applyFilters();
    }
});
