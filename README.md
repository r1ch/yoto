Grabs some podcasts and creates a single episode feed so Yoto will stop after a single podcast

## `podcasts.yml`
Contains definitions of feeds like so:

```yaml
---
bbc: #from BBC iPlayer
  - name: "Name"
    slug: "hyphen-ated-name"
    pid: "BBC PID"
    trim: 0 #seconds to cut from start
    
rss: #from the internets
  - name: "Name"
    slug: "with-hyphens"
    feed: "https://feeds.url.com" #feed rss
    trim: 10 #seconds to cut from start
---
```


