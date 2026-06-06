---
layout: single
permalink: /
title: "Qirun Zeng"
description: "Qirun Zeng is a Ph.D. student in computer science at City University of Hong Kong, working in theoretical computer science and learning theory."
author_profile: true
mermaid: true
---

I am a Ph.D. student in computer science at City University of Hong Kong, advised by [Prof. Jinhang Zuo](https://jhzuo.github.io). I study theoretical questions in sequential decision-making, with current work on bandit learning, hybrid feedback, robustness, and influence maximization.

{% include section-header.html title="Research Profile" description="My work uses algorithmic and theoretical tools to analyze learning and decision-making systems." %}

<ul class="academic-list">
  <li><strong>Learning theory:</strong> bandit learning, best-arm identification, reward and preference feedback, and sample-efficient decision-making.</li>
  <li><strong>Theoretical computer science:</strong> approximation algorithms, influence maximization, and algorithmic guarantees under structural constraints.</li>
  <li><strong>Robustness:</strong> adversarial behavior in online learning and data-injection attacks against bandit algorithms.</li>
</ul>

{% include section-header.html title="Research Map" description="A compact view of how my current projects fit together." %}

```mermaid
flowchart LR
  A["Learning Theory"] --> B["Bandit Learning"]
  B --> C["Hybrid Feedback"]
  B --> D["Best-Arm Identification"]
  B --> E["Robustness"]
  F["Theoretical Computer Science"] --> G["Approximation Algorithms"]
  G --> H["Influence Maximization"]
```

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
