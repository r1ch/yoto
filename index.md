---
layout: none
---

<h2>Feeds:</h2>
{%- for feed in site.feeds -%}
<a href = '{{feed.url}}'>{{feed.title}}</a>
{%- endfor -%}
