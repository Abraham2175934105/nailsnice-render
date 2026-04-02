(() => {
  window.addEventListener("error", () => {
    document.querySelectorAll(".reveal").forEach((el) => el.classList.add("reveal--visible"));
    const catGrid = document.getElementById("categories-grid");
    if (catGrid && !catGrid.querySelector(".service-card") && !catGrid.querySelector(".empty-state")) {
      catGrid.innerHTML = '<div class="empty-state">No se pudieron cargar categorías en este momento.</div>';
    }
  });

  const formatPriceCOP = (value) => {
    const num = typeof value === "string" ? Number(value) : value;
    if (!Number.isFinite(num)) return "";
    return new Intl.NumberFormat("es-CO", {
      style: "currency",
      currency: "COP",
      maximumFractionDigits: 0,
    }).format(num);
  };

  const escapeHtml = (str) => {
    if (str === null || str === undefined) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  };

  const toList = (payload) => {
    if (Array.isArray(payload)) return payload;
    if (payload && Array.isArray(payload.results)) return payload.results;
    return [];
  };

  const truncate = (str, maxChars) => {
    if (!str) return "";
    const s = String(str).trim();
    if (s.length <= maxChars) return s;
    return s.slice(0, Math.max(0, maxChars - 1)).trimEnd() + "…";
  };

  const resolveImageSrc = (imagen) => {
    if (!imagen) return "";
    const s = String(imagen);
    if (/^https?:\/\//i.test(s)) return s;
    if (s.startsWith("/")) return s;
    // Fallback: asumimos que se guardó como ruta relativa dentro de /static/.
    return `/static/${s}`;
  };

  const modal = document.getElementById("product-modal");
  const modalTitle = document.getElementById("modal-title");
  const modalDescription = document.getElementById("modal-description");
  const modalPrice = document.getElementById("modal-price");
  const modalBadges = document.getElementById("modal-badges");
  const modalImageWrap = modal?.querySelector(".modal-image");
  const modalImage = document.getElementById("modal-image");

  const openModal = (product, maps) => {
    if (!modal) return;

    const categoryName = maps.categorias.get(product.id_categoria) || "";
    const brandName = maps.marcas.get(product.id_marca) || "";
    const colorName = maps.colores.get(product.id_color) || "";

    modalTitle.textContent = product.nombre || "";
    modalDescription.textContent = truncate(product.descripcion, 240);
    modalPrice.textContent = formatPriceCOP(product.precio);

    const badges = [];
    if (categoryName) badges.push(`<span class="badge">${escapeHtml(categoryName)}</span>`);
    if (brandName) badges.push(`<span class="badge">${escapeHtml(brandName)}</span>`);
    if (colorName) badges.push(`<span class="badge">${escapeHtml(colorName)}</span>`);
    modalBadges.innerHTML = badges.join("");

    const hasImg = Boolean(product.imagen);
    if (hasImg && modalImageWrap && modalImage) {
      modalImage.src = resolveImageSrc(product.imagen);
      modalImageWrap.classList.add("is-having-image");
    } else if (modalImageWrap) {
      modalImageWrap.classList.remove("is-having-image");
      if (modalImage) modalImage.src = "";
    }

    modal.classList.add("is-open");
    modal.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
  };

  const closeModal = () => {
    if (!modal) return;
    modal.classList.remove("is-open");
    modal.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
  };

  const setupModalListeners = () => {
    if (!modal) return;

    modal.addEventListener("click", (e) => {
      const target = e.target;
      if (target && target.getAttribute && target.getAttribute("data-close") === "true") closeModal();
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeModal();
    });
  };

  const setupSmoothScroll = () => {
    const anchors = document.querySelectorAll('a[href^="#"]');
    anchors.forEach((anchor) => {
      anchor.addEventListener("click", (e) => {
        const href = anchor.getAttribute("href") || "";
        const target = document.querySelector(href);
        if (!target) return;

        const prefersReducedMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;
        e.preventDefault();
        target.scrollIntoView({ behavior: prefersReducedMotion ? "auto" : "smooth" });
      });
    });
  };

  const setupReveal = () => {
    const els = Array.from(document.querySelectorAll(".reveal"));
    if (!("IntersectionObserver" in window)) {
      els.forEach((el) => el.classList.add("reveal--visible"));
      return () => {};
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) entry.target.classList.add("reveal--visible");
          else entry.target.classList.remove("reveal--visible");
        });
      },
      { threshold: 0.12 }
    );

    els.forEach((el) => observer.observe(el));
    return (el) => observer.observe(el);
  };

  const parseDateMs = (v) => {
    const d = new Date(v);
    const t = d.getTime();
    return Number.isFinite(t) ? t : 0;
  };

  const setupHeaderScroll = () => {
    const header = document.querySelector(".header");
    if (!header) return;
    const onScroll = () => header.classList.toggle("header--scrolled", window.scrollY > 10);
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  };

  const renderProductCard = (product, maps, observeRevealFn) => {
    const container = document.createElement("div");
    container.className = "product-card product-card--interactive reveal";
    container.setAttribute("role", "button");
    container.setAttribute("tabindex", "0");

    const categoryName = maps.categorias.get(product.id_categoria) || "";
    const brandName = maps.marcas.get(product.id_marca) || "";
    const colorName = maps.colores.get(product.id_color) || "";

    const placeholderIcon = "💅";
    const imgSrc = product.imagen ? resolveImageSrc(product.imagen) : "";
    const imgHtml = product.imagen
      ? `<img src="${escapeHtml(imgSrc)}" alt="${escapeHtml(product.nombre || "Producto")}" onerror="this.style.display='none'; this.parentElement.querySelector('.placeholder-image')?.style && (this.parentElement.querySelector('.placeholder-image').style.display = 'flex');" />`
      : "";

    const badges = [];
    if (categoryName) badges.push(escapeHtml(categoryName));
    if (brandName) badges.push(escapeHtml(brandName));
    if (colorName) badges.push(escapeHtml(colorName));

    container.innerHTML = `
      <div class="product-image">
        ${imgHtml}
        <div class="placeholder-image" style="display:${product.imagen ? "none" : "flex"}">${placeholderIcon}</div>
      </div>
      <h3>${escapeHtml(product.nombre || "")}</h3>
      <p class="product-desc">${escapeHtml(truncate(product.descripcion, 95))}</p>
      <div class="product-badges">
        ${badges.map((b) => `<span class="badge">${b}</span>`).join("")}
      </div>
      <span class="price">${escapeHtml(formatPriceCOP(product.precio))}</span>
    `;

    const activate = () => openModal(product, maps);

    container.addEventListener("click", activate);
    container.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        activate();
      }
    });

    observeRevealFn?.(container);
    return container;
  };

  const stickySearch = document.getElementById("home-sticky-search");
  const heroFocus = document.getElementById("hero-focus");
  const homeSearchInput = document.getElementById("home-search");
  const homeSearchSuggestions = document.getElementById("home-search-suggestions");
  const homeSearchGo = document.getElementById("home-search-go");

  const categoriesGrid = document.getElementById("categories-grid");

  let featuredProducts = [];
  let mapsCache = null;

  const heroProductCard = document.getElementById("hero-product-card");
  const heroProductImg = document.getElementById("hero-product-img");
  const heroProductFallback = document.getElementById("hero-product-fallback");

  const setHeroProductImage = (product) => {
    if (!heroProductCard || !heroProductImg || !heroProductFallback) return;
    if (product && product.imagen) {
      const imgSrc = resolveImageSrc(product.imagen);
      heroProductImg.src = imgSrc;
      heroProductImg.alt = product.nombre ? String(product.nombre) : "Producto";
      heroProductCard.classList.add("is-having-image");
      return;
    }

    heroProductImg.src = "";
    heroProductCard.classList.remove("is-having-image");
  };

  const renderCategories = (categorias, observeRevealFn) => {
    if (!categoriesGrid) return;

    const items = categorias || [];
    categoriesGrid.innerHTML = "";

    const pickCategoryIcon = (name) => {
      const n = String(name || "").toLowerCase();
      if (/uñas|unas|nail/.test(n)) return "💅";
      if (/maquill|cosm[ée]tic|beauty/.test(n)) return "💄";
      if (/cuidado|skin|hidrat|tratamiento/.test(n)) return "🧴";
      if (/cabello|hair/.test(n)) return "💇";
      if (/perfume|fragancia|aroma/.test(n)) return "🌸";
      if (/kit|set|combo/.test(n)) return "🎀";
      if (/decor|glitter|brillo|strass/.test(n)) return "✨";
      if (/esmalte|gel|semipermanente/.test(n)) return "💗";
      return "🛍️";
    };

    if (!items.length) {
      categoriesGrid.innerHTML = `<div class="empty-state">No hay categorías para mostrar.</div>`;
      return;
    }

    const cards = items.map((c) => {
      const name = c.nombre_categoria || "";
      const icon = pickCategoryIcon(name);

      return `
        <div class="service-card product-category-card reveal" role="button" tabindex="0" data-category-id="${c.id}">
          <div class="service-icon">${icon}</div>
          <h3>${escapeHtml(name)}</h3>
          <p style="color: var(--muted);">Explora ${escapeHtml(name.toLowerCase())} en el catálogo.</p>
        </div>
      `;
    });

    categoriesGrid.innerHTML = cards.join("");

    // Animación al entrar/salir por scroll (si el observer existe).
    const newEls = Array.from(categoriesGrid.querySelectorAll(".reveal"));
    newEls.forEach((el) => observeRevealFn?.(el));

    // Click para filtrar en /productos/
    const attach = (el) => {
      const id = el.getAttribute("data-category-id");
      const categoryName = el.querySelector("h3")?.textContent || "";
      if (!id) return;

      const go = () => {
        const params = new URLSearchParams();
        params.set("categoria", categoryName);
        params.set("categoria_id", String(id));
        window.location.href = `/productos.html?${params.toString()}`;
      };

      el.addEventListener("click", go);
      el.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          go();
        }
      });
    };

    categoriesGrid.querySelectorAll(".product-category-card").forEach(attach);
  };

  const renderFeatured = (grid, maps, list, observeRevealFn) => {
    grid.innerHTML = "";

    if (!list.length) {
      grid.innerHTML = `<div class="empty-state">No hay resultados.</div>`;
      return;
    }

    list.forEach((p) => grid.appendChild(renderProductCard(p, maps, observeRevealFn)));
  };

  const loadFeaturedProducts = async (observeRevealFn) => {
    const grid = document.getElementById("featured-products");
    if (!grid) return;

    try {
      const [productsRes, marcasRes, categoriasRes, coloresRes] = await Promise.all([
        fetch("/api/productos/"),
        fetch("/api/marcas/"),
        fetch("/api/categorias/"),
        fetch("/api/colores/"),
      ]);

      if (!productsRes.ok) throw new Error("No se pudo cargar productos.");

      const [productsRaw, marcasRaw, categoriasRaw, coloresRaw] = await Promise.all([
        productsRes.json(),
        marcasRes.ok ? marcasRes.json() : Promise.resolve([]),
        categoriasRes.ok ? categoriasRes.json() : Promise.resolve([]),
        coloresRes.ok ? coloresRes.json() : Promise.resolve([]),
      ]);

      const products = toList(productsRaw);
      const marcas = toList(marcasRaw);
      const categorias = toList(categoriasRaw);
      const colores = toList(coloresRaw);

      const marcasMap = new Map((marcas || []).map((m) => [m.id, m.nombre_marca]));
      const categoriasMap = new Map((categorias || []).map((c) => [c.id, c.nombre_categoria]));
      const coloresMap = new Map((colores || []).map((c) => [c.id, c.nombre_color]));

      const maps = { marcas: marcasMap, categorias: categoriasMap, colores: coloresMap };
      mapsCache = maps;

      const active = products.filter((p) => p.estado_producto === "Activo");
      const source = active.length ? active : products || [];

      source.sort((a, b) => parseDateMs(b.creado_en) - parseDateMs(a.creado_en));
      const featured = source.slice(0, 8);

      featuredProducts = featured;
      renderCategories(categorias, observeRevealFn);

      renderFeatured(grid, maps, featuredProducts, observeRevealFn);

      const firstWithImg = (featuredProducts || []).find((p) => p.imagen);
      setHeroProductImage(firstWithImg || null);
    } catch (err) {
      console.error(err);
      grid.innerHTML =
        '<div class="empty-state" style="grid-column:1/-1; text-align:center;">Error cargando productos.</div>';
    }
  };

  setupModalListeners();
  setupSmoothScroll();
  setupHeaderScroll();
  const observeRevealFn = setupReveal();
  loadFeaturedProducts(observeRevealFn);

  // Barra de búsqueda sticky: aparece cuando sales del hero principal.
  const setupStickySearch = () => {
    if (!stickySearch || !heroFocus) return;

    if (!("IntersectionObserver" in window)) {
      stickySearch.classList.add("is-visible");
      stickySearch.setAttribute("aria-hidden", "false");
      return;
    }

    const obs = new IntersectionObserver(
      (entries) => {
        const entry = entries[0];
        if (!entry) return;
        if (entry.isIntersecting) {
          stickySearch.classList.remove("is-visible");
          stickySearch.setAttribute("aria-hidden", "true");
        } else {
          stickySearch.classList.add("is-visible");
          stickySearch.setAttribute("aria-hidden", "false");
        }
      },
      { threshold: 0.12 }
    );

    obs.observe(heroFocus);
  };

  const debounce = (fn, ms) => {
    let t = null;
    return (...args) => {
      if (t) clearTimeout(t);
      t = setTimeout(() => fn(...args), ms);
    };
  };

  const setupHomeSearch = () => {
    if (!homeSearchInput) return;
    const grid = document.getElementById("featured-products");
    if (!grid) return;

    const goToProducts = (queryText) => {
      const q = String(queryText || "").trim();
      const params = new URLSearchParams();
      if (q) params.set("search", q);
      const suffix = params.toString();
      window.location.href = suffix ? `/productos.html?${suffix}` : "/productos.html";
    };

    const closeSuggestions = () => {
      if (!homeSearchSuggestions) return;
      homeSearchSuggestions.innerHTML = "";
      homeSearchSuggestions.classList.remove("is-open");
    };

    const fetchSuggestions = debounce(async (query) => {
      if (!homeSearchSuggestions) return;
      const term = String(query || "").trim();
      if (!term) {
        closeSuggestions();
        return;
      }

      try {
        const resp = await fetch(`/api/productos-buscar/?q=${encodeURIComponent(term)}&limit=6`);
        if (!resp.ok) {
          closeSuggestions();
          return;
        }
        const data = await resp.json();
        const matches = data.productos || [];
        const catMatches = data.categorias || [];
        if (!matches.length && !catMatches.length) {
          closeSuggestions();
          return;
        }

        const productHtml = matches
          .map((m) => {
            const stock = Number(m.stock || 0) > 0 ? "Disponible" : "Sin stock";
            return `<button type="button" class="suggestion-item" data-name="${escapeHtml(m.nombre || "")}">
              <span>${escapeHtml(m.nombre || "")}</span>
              <small>${escapeHtml(m.categoria || "Sin categoría")} · ${stock}</small>
            </button>`;
          })
          .join("");

        const categoryHtml = catMatches
          .map((c) => {
            const categoryName = escapeHtml(c.nombre_categoria || "");
            const categoryId = escapeHtml(String(c.id || ""));
            return `<button type="button" class="suggestion-item" data-category="${categoryName}" data-category-id="${categoryId}">
              <span>${categoryName}</span>
              <small>Filtrar por categoría</small>
            </button>`;
          })
          .join("");

        homeSearchSuggestions.innerHTML = `${productHtml}${categoryHtml}`;
        homeSearchSuggestions.classList.add("is-open");

        homeSearchSuggestions.querySelectorAll(".suggestion-item").forEach((btn) => {
          btn.addEventListener("click", () => {
            const categoryName = btn.getAttribute("data-category") || "";
            const categoryId = btn.getAttribute("data-category-id") || "";
            if (categoryName && categoryId) {
              const params = new URLSearchParams();
              params.set("categoria", categoryName);
              params.set("categoria_id", categoryId);
              closeSuggestions();
              window.location.href = `/productos.html?${params.toString()}`;
              return;
            }

            const selected = btn.getAttribute("data-name") || "";
            homeSearchInput.value = selected;
            closeSuggestions();
            goToProducts(selected);
          });
        });
      } catch (error) {
        closeSuggestions();
      }
    }, 180);

    const apply = debounce(() => {
      const q = (homeSearchInput.value || "").trim().toLowerCase();
      if (!mapsCache) return;

      const filtered = featuredProducts.filter((p) => {
        if (!q) return true;
        const name = String(p.nombre || "").toLowerCase();
        const desc = String(p.descripcion || "").toLowerCase();
        return name.includes(q) || desc.includes(q);
      });

      renderFeatured(grid, mapsCache, filtered, observeRevealFn);
    }, 120);

    homeSearchInput.addEventListener("input", apply);
    homeSearchInput.addEventListener("input", (e) => fetchSuggestions(e.target.value || ""));

    // Botón: guarda búsqueda y abre catálogo.
    homeSearchGo?.addEventListener("click", () => {
      goToProducts(homeSearchInput.value || "");
    });

    homeSearchInput.addEventListener("keydown", (e) => {
      if (e.key !== "Enter") return;
      closeSuggestions();
      goToProducts(homeSearchInput.value || "");
    });

    document.addEventListener("click", (e) => {
      if (!homeSearchSuggestions) return;
      if (e.target === homeSearchInput || homeSearchSuggestions.contains(e.target)) return;
      closeSuggestions();
    });
  };

  // Inicializar sticky y búsqueda después del render.
  setupStickySearch();
  setupHomeSearch();

  const setupAuthMenu = () => {
    const authItem = document.querySelector(".nav-auth");
    if (!authItem) return;

    const trigger = authItem.querySelector(".nav-auth-trigger");
    const menu = authItem.querySelector(".nav-auth-menu");
    if (!trigger || !menu) return;

    const close = () => {
      authItem.classList.remove("is-open");
      trigger.setAttribute("aria-expanded", "false");
    };

    const toggle = () => {
      const isOpen = authItem.classList.toggle("is-open");
      trigger.setAttribute("aria-expanded", isOpen ? "true" : "false");
    };

    trigger.addEventListener("click", (e) => {
      e.stopPropagation();
      toggle();
    });

    document.addEventListener("click", (e) => {
      if (!authItem.classList.contains("is-open")) return;
      if (!authItem.contains(e.target)) close();
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") close();
    });
  };

  setupAuthMenu();
})();

