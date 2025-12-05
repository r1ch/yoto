#!/usr/bin/env python3
import feedparser
import json
import os
import subprocess
import requests
from datetime import datetime, timezone
from pathlib import Path
from pydub import AudioSegment

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

import yaml
with open("podcasts.yml", "r") as f:
    config = yaml.safe_load(f)


# ---------------------------------------------------------------------
# BBC PODCASTS VIA get_iplayer
# ---------------------------------------------------------------------
def fetch_bbc_episode(name, pid, trim_seconds=0):
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

    # Equivalent to: tail -2 | head -1 | awk '{print $NF}'
    latest_line = lines[-2]                      # second from last
    latest_pid = latest_line.split()[-1]         # last field

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
    mp3_path = OUTPUT_DIR / f"{name}.mp3"

    convert_to_mp3(downloaded_file, mp3_path, trim_seconds)
    make_json_metadata(mp3_path, name)

    # Cleanup
    for f in files:
        f.unlink()
    Path("tmp_download").rmdir()



# ---------------------------------------------------------------------
# RSS PODCASTS
# ---------------------------------------------------------------------
def fetch_rss_episode(name, feed_url, trim_seconds=0):
    print(f"Fetching RSS podcast: {name}")

    feed = feedparser.parse(feed_url)
    if not feed.entries:
        print(f"No entries for RSS feed: {feed_url}")
        return

    entry = feed.entries[0]

    # --- Extract audio URL just like your Node approach ---
    media_url = None

    # Try feedparser's enclosure objects
    if getattr(entry, "enclosures", None):
        media_url = entry.enclosures[0].get("href")

    # Try raw fields feedparser does not surface well
    if not media_url:
        media_url = entry.get("media_content", [{}])[0].get("url")

    # Try fallback: <enclosure url="">
    if not media_url and "links" in entry:
        for link in entry.links:
            if link.get("rel") == "enclosure":
                media_url = link.get("href")
                break

    # Final fallback: use <link> (often a webpage)
    if not media_url:
        media_url = entry.get("link")

    if not media_url:
        raise RuntimeError(f"No media link found for {name}")

    print(f"  → Raw media link: {media_url}")

    # -----------------------------------------------------------------
    # **Follow redirects aggressively**, some hosts require User-Agent
    # -----------------------------------------------------------------
    headers = {
        "User-Agent": "Mozilla/5.0 (RSS Downloader; +https://example.com)"
    }

    print("Resolving redirects...")
    r = requests.get(media_url, headers=headers, allow_redirects=True, stream=True)
    final_url = r.url
    print(f"  → Final resolved audio URL: {final_url}")

    # -----------------------------------------------------------------
    # Download audio
    # -----------------------------------------------------------------
    audio_path = OUTPUT_DIR / f"{name}-raw"
    print(f"Downloading: {final_url}")

    with requests.get(final_url, headers=headers, allow_redirects=True, stream=True) as r:
        r.raise_for_status()
        with open(audio_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

    mp3_path = OUTPUT_DIR / f"{name}.mp3"
    convert_to_mp3(audio_path, mp3_path, trim_seconds)
    make_json_metadata(mp3_path, name)

    audio_path.unlink()



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
# Create JSON metadata
# ---------------------------------------------------------------------
def make_json_metadata(mp3_file, name):
    audio = AudioSegment.from_mp3(mp3_file)

    metadata = {
        "name": name,
        "date": datetime.now(timezone.utc).isoformat(),
        "length_seconds": len(audio) // 1000,
        "filename": str(mp3_file)
    }

    json_file = mp3_file.with_suffix(".json")
    with open(json_file, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"Created metadata: {json_file}")


# ---------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------
def main():
    # Process BBC podcasts
    for item in config.get("bbc", []):
        trim_seconds = item.get("trim", 0)
        fetch_bbc_episode(item["name"], item["pid"], trim_seconds)

    # Process RSS podcasts
    for item in config.get("rss", []):
        trim_seconds = item.get("trim", 0)
        fetch_rss_episode(item["name"], item["feed"], trim_seconds)

if __name__ == "__main__":
    main()
