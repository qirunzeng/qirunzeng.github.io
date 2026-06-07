---
layout: single
permalink: /
description: "Qirun Zeng is a Ph.D. student in computer science at City University of Hong Kong, working in theoretical computer science and learning theory."
author_profile: true
---

{% assign home = site.data.home %}
{% assign scholar = site.data.scholar %}
{% assign conference_count = site.data.publications.conference | size %}
{% assign preprint_count = site.data.publications.preprints | size %}

<div class="home-profile">
  <section id="scholar-metrics" class="home-section">
    <header class="home-section__header">
      <h2>Scholar Metrics</h2>
      <p>Google Scholar metrics are refreshed by a scheduled site data workflow. The current values below are seeded from the latest successful profile snapshot.</p>
    </header>

    <div class="metric-grid">
      <article class="metric-card">
        <p class="metric-card__value">{% if scholar.total_citations %}{{ scholar.total_citations }}{% else %}Updating{% endif %}</p>
        <h3>Total citations</h3>
        <p>{% if scholar.updated_at %}Updated {{ scholar.updated_at }}{% else %}Scheduled update pending{% endif %}</p>
      </article>

      <article class="metric-card">
        <p class="metric-card__value">{% if scholar.h_index %}{{ scholar.h_index }}{% else %}Updating{% endif %}</p>
        <h3>h-index</h3>
        <p>{% if scholar.updated_at %}Google Scholar snapshot{% else %}Scheduled update pending{% endif %}</p>
      </article>

      <article class="metric-card">
        <p class="metric-card__value">{% if scholar.i10_index %}{{ scholar.i10_index }}{% else %}Updating{% endif %}</p>
        <h3>i10-index</h3>
        <p>{% if scholar.updated_at %}Google Scholar snapshot{% else %}Scheduled update pending{% endif %}</p>
      </article>

      <article class="metric-card">
        <p class="metric-card__value">{{ conference_count }}</p>
        <h3>Conference papers</h3>
        <p>From site publication data</p>
      </article>

      <article class="metric-card">
        <p class="metric-card__value">{{ preprint_count }}</p>
        <h3>Preprints</h3>
        <p>From site publication data</p>
      </article>
    </div>

    <p class="home-note">
      {% if scholar.source_url %}
        <a href="{{ scholar.source_url }}" target="_blank" rel="noopener noreferrer">Google Scholar profile</a>
      {% else %}
        Google Scholar metrics update automatically when scheduled data is available.
      {% endif %}
    </p>
  </section>

  <section id="profile" class="home-section">
    <header class="home-section__header">
      <h2>Profile</h2>
      <p>{{ home.profile.summary }}</p>
    </header>

    <div class="home-card-stack">
      {% for card in home.profile.cards %}
        <article class="home-card">
          <h3>{{ card.title }}</h3>
          {% for paragraph in card.paragraphs %}
            {{ paragraph | markdownify }}
          {% endfor %}
          {% if card.tags %}
            <div class="home-tags" aria-label="{{ card.title }} tags">
              {% for tag in card.tags %}
                <span>{{ tag }}</span>
              {% endfor %}
            </div>
          {% endif %}
        </article>
      {% endfor %}
    </div>
  </section>

  <section id="publications" class="home-section">
    <header class="home-section__header">
      <h2>Publications</h2>
      <p>{{ home.publications.summary }}</p>
    </header>

    {% for paper in site.data.publications.preprints limit:1 %}
      {% include paper-card.html paper=paper compact=true %}
    {% endfor %}
    {% for paper in site.data.publications.conference limit:2 %}
      {% include paper-card.html paper=paper compact=true %}
    {% endfor %}

    <p class="home-action"><a class="text-link" href="/publications/">View all publications</a></p>
  </section>

  <section id="honors" class="home-section">
    <header class="home-section__header">
      <h2>Honors</h2>
      <p>{{ home.honors.summary }}</p>
    </header>

    <div class="home-list-stack">
      {% for item in home.honors.items %}
        <article class="home-list-item">
          <h3>{{ item.date }} | {{ item.title }}</h3>
          <p>{{ item.detail }}</p>
        </article>
      {% endfor %}
    </div>
  </section>

  <section id="education" class="home-section">
    <header class="home-section__header">
      <h2>Education</h2>
      <p>{{ home.education.summary }}</p>
    </header>

    <div class="home-list-stack">
      {% for item in home.education.items %}
        <article class="home-list-item">
          <h3>{{ item.period }} | {{ item.degree }}</h3>
          <p><strong>{{ item.institution }}</strong></p>
          {{ item.detail | markdownify }}
        </article>
      {% endfor %}
    </div>
  </section>

  <section id="service" class="home-section">
    <header class="home-section__header">
      <h2>Service</h2>
      <p>{{ home.service.summary }}</p>
    </header>

    <ul class="home-service-list">
      {% for item in home.service.items %}
        <li>{{ item }}</li>
      {% endfor %}
    </ul>
  </section>

  <section id="contact" class="home-section">
    <header class="home-section__header">
      <h2>Contact</h2>
      <p>{{ home.contact.summary }}</p>
    </header>

    {% include contact-links.html %}
  </section>
</div>
