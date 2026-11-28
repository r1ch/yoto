Grabs some podcasts every night and makes two feeds per show for the Yoto,
served by GitHub Pages:
- `https://bradi.sh/yoto/<slug>/feed.xml` – only the newest episode (the Yoto plays it and stops)
- `https://bradi.sh/yoto/<slug>/catchup.xml` – the older ones (newest first), for catching up

## `podcasts.yml`
Contains definitions of feeds like so:

```yaml
bbc: # from BBC Sounds / iPlayer (downloaded with get_iplayer)
  - name: "Name"
    slug: "hyphen-ated-name"
    pid: "BBC series PID"
    trim: 0  # seconds to cut from the start
    keep: 3  # episodes kept: 1 in feed.xml, the rest in catchup.xml (optional, default 3)

rss: # from the internets
  - name: "Name"
    slug: "with-hyphens"
    feed: "https://feeds.url.com"  # feed rss
    trim: 10
```

## How it works
- `.github/workflows/download-workflow.yml` runs `fetch_podcasts.py` nightly.
- Each show keeps its newest `keep` episodes in `media/<slug>/`; new ones are
  downloaded, ones that drop off the end are deleted. `_data/state.yml` records them.
- `_feeds/<slug>.xml` holds the newest episode and `_catchups/<slug>.xml` the
  rest; `_layouts/feed.xml` renders both as RSS (catch-up titled "… (catch-up)").
  Each item's guid is the episode's own ID, so the player only sees a new episode
  when there is one.
- Every update replaces `main` with a single fresh commit (force-push), so the
  repo never accumulates old MP3s.
- If one show fails the others still update, and the run is marked failed.

## Icons
`icons/<slug>.png` is each feed's image (channel and every episode), and is the 16x16 Yoto display icon per show (transparent, no black –
black pixels don't light up). Upload one on the Make Your Own card ("Apply to all
tracks"). `python3 icons/draw.py icons` redraws them from the pixel grids in
the script; `preview.png` shows them as the player's LEDs.
