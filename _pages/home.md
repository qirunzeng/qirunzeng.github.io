---
layout: single
permalink: /
title: "Qirun Zeng"
description: "Qirun Zeng is a Ph.D. student in computer science at City University of Hong Kong, working in theoretical computer science and learning theory."
author_profile: true
---

I am a Ph.D. student in computer science at City University of Hong Kong, advised by [Prof. Jinhang Zuo](https://jhzuo.github.io). My research is in theoretical computer science and learning theory, with current work on bandit learning, hybrid feedback models, robustness, and influence maximization.

Before joining CityUHK, I received my bachelor's degree from the School of the Gifted Young at the University of Science and Technology of China in 2025, where I was advised by [Prof. Xue Chen](http://staff.ustc.edu.cn/~xuechen1989/) and [Prof. Jinhang Zuo](https://jhzuo.github.io).

{% include section-header.html title="Research Profile" description="My work uses algorithmic and theoretical tools to study sequential decision-making and learning problems. Recent projects focus on stochastic bandits, hybrid feedback, adversarial robustness, and scalable influence maximization." %}

<ul class="academic-list">
  <li><strong>Learning theory:</strong> bandit learning, best-arm identification, reward and preference feedback, and sample-efficient decision-making.</li>
  <li><strong>Theoretical computer science:</strong> approximation algorithms, influence maximization, and algorithmic guarantees under structural constraints.</li>
  <li><strong>Robustness:</strong> adversarial behavior in online learning and data-injection attacks against bandit algorithms.</li>
</ul>

{% include section-header.html title="Selected Papers and Projects" description="A short view of current and recent work. See the research page for the full list." %}

{% for paper in site.data.publications.preprints limit:1 %}
  {% include paper-card.html paper=paper compact=true %}
{% endfor %}
{% for paper in site.data.publications.conference limit:2 %}
  {% include paper-card.html paper=paper compact=true %}
{% endfor %}

<p><a class="text-link" href="/publications/">View all publications</a></p>

{% include section-header.html title="Contact" description="For research discussions, seminar invitations, and collaboration inquiries, email is the most reliable contact channel." %}

{% include contact-links.html %}
