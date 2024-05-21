<?xml version="1.0" encoding="UTF-8"?>
<rss xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" version="2.0">
  <channel>
    <title>Friday Night Comedy</title>
    <link>http://bradi.sh/yoto</link>
    <itunes:author>Rich Bradish</itunes:author>
    <copyright>None</copyright>
    <language>en-gb</language>
    <pubDate>{{ site.time | date_to_rfc822 }}</pubDate>
    <lastBuildDate>{{ site.time | date_to_rfc822 }}</lastBuildDate>
    <itunes:category text="Humour">
    </itunes:category>
    <itunes:explicit>Yes</itunes:explicit>
    <generator>Jekyll v{{ jekyll.version }}</generator>
    {% for post in site.categories.podcast %}
    <item>
      <title>{{ post.number }} &mdash; {{ post.title }}</title>
      <itunes:explicit>Yes</itunes:explicit>
      <itunes:author>{{ site.author }}</itunes:author>
      <itunes:duration>{{ post.duration }}</itunes:duration>
      <pubDate>{{ post.date | date_to_rfc822 }}</pubDate>
      <guid isPermaLink="true">{{ post.mp3 }}</guid>
      <category>{{ site.podcast.category }}</category>
      <enclosure length="{{ post.length }}" url="{{ post.mp3 }}" type="audio/mpeg"/>
    </item>
    {% endfor %}
  </channel>
</rss>
