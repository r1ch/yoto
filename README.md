Grabs some podcasts and creates a single episode feed so Yoto will stop after a single podcast

## `_feeds`
Contains definitions of feeds like so:

```yaml
---
title: Bugle # title of the podcast - populates the rss feed title
short: bugle # short version for filenames
handler: grabber # which tool will get the podcast - grabber works for all public feeds, BBC grabs those published on iPlayer 
source: https://feeds.acast.com/public/shows/thebugle # url for the rss feed to grab the file from 
destination: media # which folder to drop the file in
extension: mp3 # extension + filetype we expect
trim: 10 # seconds off the front to bin
uuid: 84037fb1-8456-5d0f-9834-e498bc8a67c5 # podcast guid / uuid
fetched: 2024-08-20T11:48:05.746Z # timestamp of last fetch (populated on run)
---
```


