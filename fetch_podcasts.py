#!/usr/bin/env python3
"""Fetch the latest few episodes of each podcast in podcasts.yml as small MP3s.

For each show it keeps the newest `keep` episodes (default 3) in
media/<slug>/<episode>.mp3, records them in _data/state.yml and writes two
feed pages (front matter that _layouts/feed.xml turns into RSS):
_feeds/<slug>.xml with only the newest episode (<slug>/feed.xml) and
_catchups/<slug>.xml with the older ones (<slug>/catchup.xml).
Episodes already downloaded are not fetched again; ones that drop out of the
newest `keep` are deleted.
"""
import hashlib
import html
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import requests
import yaml
from pydub import AudioSegment

MEDIA_DIR = Path("media")
FEED_DIR = Path("_feeds")
CATCHUP_DIR = Path("_catchups")
STATE_FILE = Path("_data/state.yml")
BOARD_FILE = Path("board.html")   # read by Home Assistant (bedside e-ink board)

DEFAULT_KEEP = 3
HTTP_TIMEOUT = (20, 300)          # connect, read (seconds)
GET_IPLAYER_TIMEOUT = 30 * 60     # one episode download
HEADERS = {"User-Agent": "Mozilla/5.0 (podcast fetcher for a Yoto player)"}

SOUNDS_API = ("https://rms.api.bbc.co.uk/v2/programmes/playable"
              "?container={pid}&sort=sequential&type=episode&limit=20")
BBC_PODCAST_RSS = "https://podcasts.files.bbci.co.uk/{pid}.rss"


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------
# STATE
# ---------------------------------------------------------------------
def load_state():
    if STATE_FILE.exists():
        return yaml.safe_load(STATE_FILE.read_text()) or {}
    return {}


def save_state(state):
    STATE_FILE.parent.mkdir(exist_ok=True)
    STATE_FILE.write_text(yaml.safe_dump(state, sort_keys=True, allow_unicode=True))


def episode_file(slug, episode_id):
    """Stable, URL-safe file name for an episode."""
    digest = hashlib.sha1(episode_id.encode()).hexdigest()[:12]
    return MEDIA_DIR / slug / f"{digest}.mp3"


def migrate_old_layout(slug, show_state):
    """Old layout: one media/<slug>.mp3 plus last_id/last_pid in the state."""
    if "episodes" in show_state:
        return
    episodes = []
    old_file = MEDIA_DIR / f"{slug}.mp3"
    last_id = show_state.get("last_id")
    if last_id and old_file.exists():
        new_file = episode_file(slug, last_id)
        new_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(old_file, new_file)
        old_meta = {}
        meta_path = FEED_DIR / f"{slug}.xml"
        if meta_path.exists():
            old_meta = next(yaml.safe_load_all(meta_path.read_text()), None) or {}
        episodes.append({
            "id": last_id,
            "title": None,
            "date": str(old_meta.get("date") or now_iso()),
            "file": str(new_file),
            "seconds": int(old_meta.get("length_seconds") or 0),
            "bytes": new_file.stat().st_size,
        })
        print(f"  → Migrated {old_file} to {new_file}")
    show_state.clear()
    show_state["episodes"] = episodes


# ---------------------------------------------------------------------
# AUDIO
# ---------------------------------------------------------------------
def save_as_mp3(source, mp3_path, trim_seconds):
    """Convert any audio file (or file-like) to a 64k MP3; returns seconds."""
    audio = AudioSegment.from_file(source)
    if trim_seconds > 0:
        print(f"  → Trimming first {trim_seconds} seconds")
        audio = audio[trim_seconds * 1000:]
    mp3_path.parent.mkdir(parents=True, exist_ok=True)
    audio.export(mp3_path, format="mp3", bitrate="64k")
    return len(audio) // 1000


def download_url(url, dest):
    with requests.get(url, headers=HEADERS, timeout=HTTP_TIMEOUT,
                      allow_redirects=True, stream=True) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)


# ---------------------------------------------------------------------
# LISTING: each returns newest-first dicts
#   {id, title, date, fetch: callable(workdir) -> downloaded file path}
# ---------------------------------------------------------------------
def list_bbc(pid):
    """BBC Sounds' list of playable episodes (has titles and dates, and gets
    new episodes before the BBC podcast RSS). Falls back to that RSS."""
    try:
        r = requests.get(SOUNDS_API.format(pid=pid), headers=HEADERS, timeout=HTTP_TIMEOUT)
        r.raise_for_status()
        items = []
        for e in r.json().get("data", []):
            ep_pid = e["urn"].split(":")[-1]
            items.append({
                "id": f"urn:bbc:podcast:{ep_pid}",
                "title": (e.get("titles") or {}).get("secondary") or (e.get("titles") or {}).get("primary"),
                "date": (e.get("release") or {}).get("date") or now_iso(),
                "fetch": lambda work, p=ep_pid: fetch_bbc_pid(p, pid, work),
            })
        if items:
            items.sort(key=lambda i: i["date"], reverse=True)
            return items
        print("  → BBC Sounds listed no episodes, trying the podcast RSS")
    except Exception as e:
        print(f"  → BBC Sounds listing failed ({e}), trying the podcast RSS")
    return list_rss(BBC_PODCAST_RSS.format(pid=pid))


def fetch_bbc_pid(ep_pid, series_pid, work):
    """Download one BBC episode with get_iplayer; if that fails, use the
    episode's enclosure from the BBC podcast RSS (if it is in there)."""
    out = work / "iplayer"
    out.mkdir()
    cmd = ["get_iplayer", f"--pid={ep_pid}", "--type=radio", "--force",
           "--nocopyright", f"--output={out}"]
    try:
        subprocess.run(cmd, check=True, timeout=GET_IPLAYER_TIMEOUT,
                       capture_output=True, text=True)
        files = [f for f in out.iterdir() if f.is_file()]
        if files:
            return files[0]
        print("  → get_iplayer produced no file")
    except subprocess.CalledProcessError as e:
        print(f"  → get_iplayer failed (exit {e.returncode}): {(e.stderr or e.stdout or '').strip()[-500:]}")
    except subprocess.TimeoutExpired:
        print("  → get_iplayer timed out")
    except OSError as e:
        print(f"  → get_iplayer could not run: {e}")
    print("  → Trying the BBC podcast RSS instead")
    for item in list_rss(BBC_PODCAST_RSS.format(pid=series_pid)):
        if item["id"] == f"urn:bbc:podcast:{ep_pid}":
            return item["fetch"](work)
    raise RuntimeError(f"{ep_pid}: get_iplayer failed and it is not in the podcast RSS")


def list_rss(feed_url):
    r = requests.get(feed_url, headers=HEADERS, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    feed = feedparser.parse(r.content)
    items = []
    for entry in feed.entries:
        media_url = None
        for enc in entry.get("enclosures", []):
            if enc.get("href"):
                media_url = enc["href"]
                break
        if not media_url:
            media_url = (entry.get("media_content") or [{}])[0].get("url")
        if not media_url:
            continue
        episode_id = entry.get("id") or entry.get("published") or entry.get("title")
        if not episode_id:
            continue
        published = entry.get("published_parsed") or entry.get("updated_parsed")
        date = (datetime(*published[:6], tzinfo=timezone.utc).isoformat()
                if published else now_iso())
        items.append({
            "id": episode_id,
            "title": entry.get("title"),
            "date": date,
            "fetch": lambda work, u=media_url: fetch_url(u, work),
        })
    items.sort(key=lambda i: i["date"], reverse=True)
    return items


def fetch_url(url, work):
    print(f"  → Downloading {url[:120]}")
    dest = work / "download"
    download_url(url, dest)
    return dest


# ---------------------------------------------------------------------
# ONE SHOW
# ---------------------------------------------------------------------
def update_show(show, kind, state):
    name, slug = show["name"], show["slug"]
    keep = int(show.get("keep", DEFAULT_KEEP))
    trim = int(show.get("trim", 0))
    print(f"Fetching {name}")

    show_state = state.setdefault(slug, {})
    migrate_old_layout(slug, show_state)
    have = {e["id"]: e for e in show_state["episodes"]}

    available = list_bbc(show["pid"]) if kind == "bbc" else list_rss(show["feed"])
    if not available:
        raise RuntimeError("feed lists no episodes")
    newest = available[:keep]
    print("  → Newest: " + "; ".join(f"{i['date'][:10]} {i['title']}" for i in newest))

    errors = []
    for item in newest:
        if item["id"] in have:
            # Refresh title/date from the listing (fills in migrated episodes).
            have[item["id"]]["title"] = item["title"] or have[item["id"]]["title"]
            have[item["id"]]["date"] = item["date"]
            continue
        print(f"  → New episode: {item['title']} ({item['id']})")
        try:
            with tempfile.TemporaryDirectory() as tmp:
                source = item["fetch"](Path(tmp))
                mp3 = episode_file(slug, item["id"])
                seconds = save_as_mp3(source, mp3, trim)
            have[item["id"]] = {
                "id": item["id"], "title": item["title"], "date": item["date"],
                "file": str(mp3), "seconds": seconds, "bytes": mp3.stat().st_size,
            }
        except Exception as e:
            print(f"  → ERROR downloading {item['title']}: {e}")
            errors.append(item["title"] or item["id"])

    # Keep the newest `keep` episodes we actually have.
    kept = sorted(have.values(), key=lambda e: e["date"], reverse=True)[:keep]
    show_state["episodes"] = kept
    show_state["checked"] = now_iso()

    # Delete files that dropped out.
    keep_files = {Path(e["file"]) for e in kept}
    show_dir = MEDIA_DIR / slug
    if show_dir.exists():
        for f in show_dir.iterdir():
            if f not in keep_files:
                print(f"  → Removing old {f}")
                f.unlink()

    write_feed_page(name, slug, kept)
    if errors:
        raise RuntimeError("could not download: " + ", ".join(errors))


def write_feed_page(name, slug, episodes):
    """Main feed = newest episode only (the Yoto plays one and stops);
    catch-up feed = the rest."""
    write_page(FEED_DIR, name, slug, episodes[:1], catchup=False)
    write_page(CATCHUP_DIR, name, slug, episodes[1:], catchup=True)


def write_page(folder, name, slug, episodes, catchup):
    meta = {
        "name": name,
        "slug": slug,
        "catchup": catchup,
        "date": episodes[0]["date"] if episodes else now_iso(),
        "episodes": [{
            "id": e["id"],
            "title": e["title"] or name,
            "date": e["date"],
            "path": "/" + e["file"],
            "seconds": e["seconds"],
            "bytes": e["bytes"],
        } for e in episodes],
    }
    folder.mkdir(exist_ok=True)
    (folder / f"{slug}.xml").write_text(
        "---\n" + yaml.safe_dump(meta, sort_keys=False, allow_unicode=True) + "---\n")


def write_board(config, state, failed):
    """board.html: one line per show, newest episode first, for Home Assistant's
    Scrape integration (#run, then #e1, #e2, ...; fields split by '|').
    Lists the episode each main feed actually serves after this run."""
    rows = []
    for kind in ("bbc", "rss"):
        for show in config.get(kind) or []:
            eps = (state.get(show["slug"]) or {}).get("episodes") or []
            if eps:
                e = eps[0]
                rows.append((e["date"], show["name"], e["title"] or show["name"],
                             "failed" if show["name"] in failed else "ok"))
    rows.sort(reverse=True)
    clean = lambda v: html.escape(str(v).replace("|", "/").replace("\n", " "))[:200]
    run = [now_iso(), os.environ.get("GITHUB_RUN_ID", "local"),
           "failed: " + ", ".join(failed) if failed else "ok"]
    lines = [f'<p id="run">{clean(run[0])}|{clean(run[1])}|{clean(run[2])}</p>']
    lines += [f'<p id="e{i}">{"|".join(clean(v) for v in r)}</p>' for i, r in enumerate(rows, 1)]
    BOARD_FILE.write_text("<!doctype html>\n<meta charset=\"utf-8\">\n<title>Yoto board</title>\n"
                          + "\n".join(lines) + "\n")


# ---------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------
def main():
    config = yaml.safe_load(Path("podcasts.yml").read_text())
    state = load_state()
    failed = []

    # One failing show (or episode) must not stop the others.
    for kind in ("bbc", "rss"):
        for show in config.get(kind) or []:
            try:
                update_show(show, kind, state)
            except Exception as e:
                print(f"ERROR: {show['name']}: {e}")
                failed.append(show["name"])
            save_state(state)
    write_board(config, state, failed)

    if failed:
        print(f"FAILED: {', '.join(failed)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
