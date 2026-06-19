/**
 * Profesional Beauty — Nav Auth Global
 * Maneja el menú desplegable "Empieza ahora" en TODAS las páginas.
 * Se carga en base.html / cualquier layout compartido.
 */
(function () {
  'use strict';

  function initNavAuth() {
    // Soporta múltiples instancias del trigger (home, productos, etc.)
    const triggers = document.querySelectorAll('.nav-auth-trigger');
    if (!triggers.length) return;

    triggers.forEach(function (trigger) {
      const parent = trigger.closest('.nav-auth');
      if (!parent) return;
      const menu = parent.querySelector('.nav-auth-menu');
      if (!menu) return;

      // Toggle al hacer clic en el botón
      trigger.addEventListener('click', function (e) {
        e.stopPropagation();
        const isOpen = trigger.getAttribute('aria-expanded') === 'true';
        closeAllMenus();
        if (!isOpen) {
          openMenu(trigger, menu);
        }
      });

      // Cerrar con Escape
      trigger.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') closeAllMenus();
      });
      menu.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
          closeAllMenus();
          trigger.focus();
        }
      });
    });

    // Cerrar al hacer clic fuera
    document.addEventListener('click', function (e) {
      if (!e.target.closest('.nav-auth')) {
        closeAllMenus();
      }
    });

    // Cerrar al hacer scroll profundo
    var lastScrollY = window.scrollY;
    window.addEventListener('scroll', function () {
      if (Math.abs(window.scrollY - lastScrollY) > 80) {
        closeAllMenus();
        lastScrollY = window.scrollY;
      }
    }, { passive: true });
  }

  function openMenu(trigger, menu) {
    trigger.setAttribute('aria-expanded', 'true');
    menu.classList.add('is-open');
    // Enfocar primer enlace del menú para accesibilidad
    var firstLink = menu.querySelector('a, button');
    if (firstLink) setTimeout(function () { firstLink.focus(); }, 80);
  }

  function closeAllMenus() {
    document.querySelectorAll('.nav-auth-trigger').forEach(function (t) {
      t.setAttribute('aria-expanded', 'false');
    });
    document.querySelectorAll('.nav-auth-menu').forEach(function (m) {
      m.classList.remove('is-open');
    });
  }

  // Inicializar cuando el DOM esté listo
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initNavAuth);
  } else {
    initNavAuth();
  }
})();
