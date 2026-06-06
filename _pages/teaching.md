---
layout: archive
title: "Teaching"
permalink: /teaching/
description: "Teaching assistant experience and selected course materials for Qirun Zeng."
author_profile: true
---

I have served as a teaching assistant for the following courses.

{% for item in site.data.teaching %}
  {% include teaching-entry.html item=item %}
{% endfor %}
