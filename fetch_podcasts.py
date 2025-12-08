#!/usr/bin/env python3
import feedparser
import os
import subprocess
import requests
from datetime import datetime, timezone
from pathlib import Path
from pydub import AudioSegment
import yaml
from io import BytesIO

MEDIA_DIR = Path("media")
MEDIA_DIR.mkdir(exist_ok=True)

FEED_DIR = Path("_feeds")
FEED_DIR.mkdir(exist_ok=True)

with open("podcasts.yml", "r") as f:
    config = yaml.safe_load(f)


# ---------------------------------------------------------------------
# Convert audio → MP3 (small size)
# ---------------------------------------------------------------------
def convert_to_mp3(input_file, output_file, trim_seconds=0):
    print(f"Converting to MP3: {output_file}")
    audio = AudioSegment.from_file(input_file)
    
    if trim_seconds > 0:
        print(f"  → Trimming first {trim_seconds} seconds")
        audio = audio[trim_seconds * 1000:]  # pydub uses milliseconds

    audio.export(output_file, format="mp3", bitrate="64k")  # small file size


# ---------------------------------------------------------------------
# Create YAML metadata
# ---------------------------------------------------------------------
def make_metadata(mp3_file, name, slug, metadata_dir):
    audio = AudioSegment.from_mp3(mp3_file)

    metadata = {
        "name": name,
        "slug": slug,
        "date": datetime.now(timezone.utc).isoformat(),
        "length_seconds": len(audio) // 1000,
        "filename": str(mp3_file)
    }

    yaml_file = metadata_dir / f"{slug}.xml"
    with open(yaml_file, "w") as f:
        f.write("---\n")
        yaml.dump(metadata, f, sort_keys=False)
        f.write("---\n")

    print(f"Created metadata: {yaml_file}")


# ---------------------------------------------------------------------
# BBC PODCASTS VIA get_iplayer
# ---------------------------------------------------------------------
def fetch_bbc_episode(name, slug, pid, trim_seconds=0):
    print(f"Fetching BBC podcast series: {name}")

    # Step 1: get the list of episode PIDs
    list_cmd = [
        "get_iplayer",
        f"--pid={pid}",
        "--pid-recursive-list"
    ]

    result = subprocess.run(list_cmd, capture_output=True, text=True, check=True)
    lines = result.stdout.strip().splitlines()

    if len(lines) < 2:
        raise RuntimeError(f"No episodes found for BBC series PID: {pid}")

    latest_line = lines[-2]  # second from last
    latest_pid = latest_line.split()[-1]  # last field
    print(f"  → Latest episode PID: {latest_pid}")

    # Step 2: download the episode using resolved PID
    dl_cmd = [
        "get_iplayer",
        f"--pid={latest_pid}",
        "--type=radio",
        "--force",
        "--nocopyright",
        "--output=tmp_download"
    ]
    subprocess.run(dl_cmd, check=True)

    # Step 3: find downloaded file
    files = list(Path("tmp_download").glob("*"))
    if not files:
        raise RuntimeError("Nothing downloaded from get_iplayer.")

    downloaded_file = files[0]
    mp3_path = MEDIA_DIR / f"{slug}.mp3"

    convert_to_mp3(downloaded_file, mp3_path, trim_seconds)
    make_metadata(mp3_path, name, slug, FEED_DIR)

    # Cleanup
    for f in files:
        f.unlink()
    Path("tmp_download").rmdir()


# ---------------------------------------------------------------------
# RSS PODCASTS
# ---------------------------------------------------------------------
def fetch_rss_episode(name, slug, feed_url, trim_seconds=0):
    print(f"Fetching RSS podcast: {name}")

    feed = feedparser.parse(feed_url)
    if not feed.entries:
        print(f"No entries for RSS feed: {feed_url}")
        return

    entry = feed.entries[0]
    media_url = None

    if getattr(entry, "enclosures", None):
        media_url = entry.enclosures[0].get("href")
    if not media_url:
        media_url = entry.get("media_content", [{}])[0].get("url")
    if not media_url and "links" in entry:
        for link in entry.links:
            if link.get("rel") == "enclosure":
                media_url = link.get("href")
                break
    if not media_url:
        media_url = entry.get("link")
    if not media_url:
        raise RuntimeError(f"No media link found for {name}")

    print(f"  → Raw media link: {media_url}")

    headers = {
        "User-Agent": "Mozilla/5.0 (RSS Downloader; +https://example.com)"
    }

    print("Resolving redirects...")
    r = requests.get(media_url, headers=headers, allow_redirects=True, stream=True)
    r.raise_for_status()
    final_url = r.url
    print(f"  → Final resolved audio URL: {final_url}")

    # Stream directly into pydub
    print(f"Downloading and converting: {final_url}")
    audio_data = BytesIO(r.content)  # load entire file into memory
    audio = AudioSegment.from_file(audio_data)

    if trim_seconds > 0:
        print(f"  → Trimming first {trim_seconds} seconds")
        audio = audio[trim_seconds * 1000:]  # pydub uses milliseconds

    mp3_path = MEDIA_DIR / f"{slug}.mp3"
    audio.export(mp3_path, format="mp3", bitrate="64k")

    make_metadata(mp3_path, name, slug, FEED_DIR)


# ---------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------
def main():
    # Process BBC podcasts
    for item in config.get("bbc", []):
        trim_seconds = item.get("trim", 0)
        fetch_bbc_episode(item["name"], item["slug"], item["pid"], trim_seconds)

    # Process RSS podcasts
    for item in config.get("rss", []):
        trim_seconds = item.get("trim", 0)
        fetch_rss_episode(item["name"], item["slug"], item["feed"], trim_seconds)


if __name__ == "__main__":
    main()
