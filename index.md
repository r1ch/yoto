---
layout: none
---

<h2>Feeds:</h2>
{%- for feed in site.feeds -%}
<a href = '{{ feed.url | absolute_url }}'>{{feed.title}}</a><br>
{%- endfor -%}

<h2>Media:</h2>
{%- assign episodes = site.static_files | where_exp: "file", "file.path contains 'media'" | where: "extname", ".mp3" -%}
<table>
  <thead>
    <tr>
      <th>Name</th><th>Date</th>
    </tr>
  </thead>
  <tbody>
      {%- for episode in episodes -%}
    <tr>
      <td><a href = "{{episode.path | absolute_url}}">episode.basename</a></td><td>{{file.modified_time}}</td>
    </tr>
      {%- endfor -%}
  </tbody>  
</table>
