---
layout: single
permalink: /
title: "Qirun Zeng"
description: "Qirun Zeng is a Ph.D. student in computer science at City University of Hong Kong, working in theoretical computer science and learning theory."
author_profile: true
---

I am a Ph.D. student in computer science at City University of Hong Kong, advised by [Prof. Jinhang Zuo](https://jhzuo.github.io). I study theoretical questions in sequential decision-making, with current work on bandit learning, hybrid feedback, robustness, and influence maximization.

{% include section-header.html title="Research Positioning" description="Broadly, my work is in theoretical computer science. Within that area, I focus on learning theory and online decision-making, with a secondary algorithm-design thread in influence maximization." %}

{% include section-header.html title="Selected Work" description="A short view of current and recent projects. See the research page for the full list." %}

{% for paper in site.data.publications.preprints limit:1 %}
  {% include paper-card.html paper=paper compact=true %}
{% endfor %}
{% for paper in site.data.publications.conference limit:2 %}
  {% include paper-card.html paper=paper compact=true %}
{% endfor %}

<p><a class="text-link" href="/publications/">View all publications</a></p>

{% include section-header.html title="Contact" description="For research discussions, seminar invitations, and collaboration inquiries, email is the most reliable contact channel." %}

{% include contact-links.html %}
