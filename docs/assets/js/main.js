// NSS Lab — minimal UI behavior: mobile menu, dropdown, header shadow.
(function () {
  "use strict";

  // Mobile hamburger toggle
  var toggle = document.querySelector(".nav-toggle");
  var nav = document.querySelector(".site-nav");
  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      toggle.setAttribute("aria-expanded", String(open));
    });
  }

  // "People" dropdown: tap to open on mobile (hover handles desktop via CSS)
  document.querySelectorAll(".dropdown-toggle").forEach(function (t) {
    t.addEventListener("click", function (e) {
      if (window.matchMedia("(max-width: 860px)").matches) {
        e.preventDefault();
        t.closest(".has-dropdown").classList.toggle("open");
      }
    });
  });

  // Subtle shadow on the sticky header once scrolled
  var header = document.querySelector(".site-header");
  if (header) {
    var onScroll = function () {
      header.classList.toggle("scrolled", window.scrollY > 8);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  // Gallery carousel: prev/next buttons page through the strip
  var strip = document.getElementById("galleryStrip");
  if (strip) {
    var step = function () { return strip.clientWidth; };
    var prev = document.querySelector(".gallery-prev");
    var next = document.querySelector(".gallery-next");
    if (prev) prev.addEventListener("click", function () { strip.scrollBy({ left: -step(), behavior: "smooth" }); });
    if (next) next.addEventListener("click", function () { strip.scrollBy({ left: step(), behavior: "smooth" }); });
  }
})();
