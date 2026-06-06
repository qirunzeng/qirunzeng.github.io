---
layout: archive
title: "Research and Publications"
permalink: /publications/
description: "Publications and preprints by Qirun Zeng in learning theory, bandit learning, approximation algorithms, and theoretical computer science."
author_profile: true
redirect_from:
  - /research/
---

My research is in theoretical computer science and learning theory, with current work on bandit learning, hybrid feedback, robustness, and influence maximization.

<p class="note">* Equal contribution.</p>

{% include section-header.html title="Conference Proceedings" %}

{% for paper in site.data.publications.conference %}
  {% include paper-card.html paper=paper %}
{% endfor %}

{% include section-header.html title="Preprints" %}

{% for paper in site.data.publications.preprints %}
  {% include paper-card.html paper=paper %}
{% endfor %}
