---
layout: default
permalink: /awards/
title: Award
---
<section class="page-hero">
  <div class="container">
    <h1>Award</h1>
    <p class="page-subtitle">Honors and recognitions.</p>
  </div>
</section>
<section class="section">
  <div class="container">
    {% for yg in site.data.awards %}
    <section class="award-group">
      <h2 class="award-year">{{ yg.year }}</h2>
      {% for a in yg.awards %}
      <div class="award-item">
        <p class="award-name">{{ a.name }}</p>
        {% for it in a.items %}
        <p class="award-line">{% if it.prize %}<span class="award-prize">{{ it.prize }}</span> — {% endif %}{{ it.recipients }}</p>
        {% endfor %}
      </div>
      {% endfor %}
    </section>
    {% endfor %}
  </div>
</section>
