---
layout: none
---
{{%- for feed in site.feeds -}}
<h2>Feeds:</h2>
<a href = '{{feed.permalink}}'>{{feed.title}}</a>
