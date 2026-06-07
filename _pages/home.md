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
  <section class="home-hero" aria-labelledby="home-title">
    <p class="home-hero__eyebrow">{{ home.hero.subtitle }}</p>
    <h1 id="home-title">{{ home.hero.title }}</h1>
    <p class="home-hero__tagline">{{ home.hero.tagline }}</p>
    <p class="home-hero__topics">{{ home.hero.topics | join: " &middot; " }}</p>

    <div class="home-actions" aria-label="Primary links">
      <a class="home-action-button" href="/publications/">Publications</a>
      {% if scholar.source_url %}
        <a class="home-action-button home-action-button--secondary" href="{{ scholar.source_url }}" target="_blank" rel="noopener noreferrer">Google Scholar</a>
      {% endif %}
      <a class="home-action-button home-action-button--secondary" href="mailto:{{ site.author.email }}">Email</a>
    </div>

    <ul class="home-metrics" aria-label="Academic metrics">
      {% if scholar.total_citations %}
        <li><strong>{{ scholar.total_citations }}</strong> total citations</li>
      {% endif %}
      {% if scholar.h_index %}
        <li><strong>{{ scholar.h_index }}</strong> h-index</li>
      {% endif %}
      {% if scholar.i10_index %}
        <li><strong>{{ scholar.i10_index }}</strong> i10-index</li>
      {% endif %}
      <li><strong>{{ conference_count }}</strong> conference papers</li>
      <li><strong>{{ preprint_count }}</strong> preprints</li>
    </ul>
  </section>

  <section id="publications" class="home-section home-section--featured">
    <header class="home-section__header">
      <h2>Selected Publications</h2>
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

  <section id="research" class="home-section">
    <header class="home-section__header">
      <h2>Research Focus</h2>
    </header>

    <article class="home-card home-card--strong">
      <p>{{ home.research.summary }}</p>
      <div class="home-tags" aria-label="Research topics">
        {% for tag in home.research.tags %}
          <span>{{ tag }}</span>
        {% endfor %}
      </div>
    </article>
  </section>

  <section id="profile" class="home-section">
    <header class="home-section__header">
      <h2>Profile</h2>
      <p>{{ home.profile.summary }}</p>
    </header>

    <div class="home-prose">
      {% for paragraph in home.profile.paragraphs %}
        {{ paragraph | markdownify }}
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
        <article class="home-list-item home-list-item--card">
          <h3>{{ item.period }} | {{ item.degree }}</h3>
          <p><strong>{{ item.institution }}</strong></p>
          {{ item.detail | markdownify }}
        </article>
      {% endfor %}
    </div>
  </section>

  <section id="honors" class="home-section">
    <header class="home-section__header">
      <h2>Honors</h2>
      <p>{{ home.honors.summary }}</p>
    </header>

    <ol class="home-timeline">
      {% for item in home.honors.items %}
        <li>
          <span>{{ item.date }}</span>
          <strong>{{ item.title }}</strong>
          <em>{{ item.detail }}</em>
        </li>
      {% endfor %}
    </ol>
  </section>

  <section id="service" class="home-section">
    <header class="home-section__header">
      <h2>Service</h2>
      <p>{{ home.service.summary }}</p>
    </header>

    <ul class="home-plain-list">
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
