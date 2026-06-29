---
layout: page
permalink: /awards/
title: Award
subtitle: Honors and recognitions.
---
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
