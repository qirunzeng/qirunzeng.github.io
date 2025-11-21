---
layout: archive
title: "Publications"
permalink: /publications/
author_profile: true
---

<style>
/* ===== 通用标签样式 ===== */
.pub-tag {
    display: inline-block;
    padding: 2px 6px;
    font-size: 12px;
    color: white;
    border-radius: 4px;
    margin-right: 4px;
    font-family: sans-serif;
}

/* ===== 各种标签颜色 ===== */
.pub-tag.arxiv  { background: #d9534f; }
.pub-tag.github { background: #555; }
.pub-tag.icml   { background: #7c2dd0; }
.pub-tag.conf   { background: #0069d9; }  /* 通用会议标签 */
.pub-tag.preprint { background: #5cb85c; } /* Preprint 可选 */
</style>

<!-- ===== 自定义标签组件（调用方便）===== -->
<script>
customElements.define("arxiv-tag",  class extends HTMLElement {
  connectedCallback() { this.innerHTML = `<span class="pub-tag arxiv">arXiv</span>` }
});
customElements.define("github-tag", class extends HTMLElement {
  connectedCallback() { this.innerHTML = `<span class="pub-tag github">GitHub</span>` }
});
customElements.define("icml-tag",   class extends HTMLElement {
  connectedCallback() { this.innerHTML = `<span class="pub-tag icml">ICML 2025</span>` }
});
customElements.define("preprint-tag", class extends HTMLElement {
  connectedCallback() { this.innerHTML = `<span class="pub-tag preprint">Preprint</span>` }
});
</script>


2025
===

<div style="margin-bottom:15px;">
<b>Practical Adversarial Attacks on Stochastic Bandits via Fake Data Injection</b><br>
<b>Qirun Zeng</b>, Eric He, Richard Hoffmann, Xuchuang Wang, Jinhang Zuo.<br>

<preprint-tag></preprint-tag>
<arxiv-tag></arxiv-tag>
<a href="https://arxiv.org/abs/2505.21938">link</a>
&nbsp;
<github-tag></github-tag>
<a href="https://github.com/richardhoff88/online_learning_torank">repo</a>
</div>

<div style="margin-bottom:15px;">
<b>Fusing Reward and Dueling Feedback in Stochastic Bandits</b><br>
Xuchuang Wang, <b>Qirun Zeng</b>, Jinhang Zuo, Xutong Liu, Mohammad Hajiesmaili,
John C. S. Lui, Adam Wierman.<br>

<icml-tag></icml-tag>
<github-tag></github-tag>
<a href="https://github.com/qirunzeng/Fusing-Reward-and-Dueling">repo</a>
</div>
