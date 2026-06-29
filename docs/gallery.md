---
layout: default
permalink: /gallery/
title: Gallery
---
<section class="page-hero">
  <div class="container">
    <h1>Gallery</h1>
    <p class="page-subtitle">Moments from the lab.</p>
  </div>
</section>
<section class="section">
  <div class="container">
    <div class="gallery">
      <button class="gallery-nav gallery-prev" type="button" aria-label="Previous photo">‹</button>
      <div class="gallery-strip" id="galleryStrip">
      {% for img in site.data.gallery %}<figure class="gallery-item"><img src="{{ '/assets/img/gallery/' | append: img.file | relative_url }}" alt="{{ img.caption }}" loading="lazy">{% if img.caption %}<figcaption>{{ img.caption }}</figcaption>{% endif %}</figure>
      {% endfor %}</div>
      <button class="gallery-nav gallery-next" type="button" aria-label="Next photo">›</button>
    </div>
  </div>
</section>
