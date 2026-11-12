#!/usr/bin/env python3
"""Fetch a YouTube transcript and print it as "[mm:ss] text" lines.

Usage: fetch_transcript.py <url-or-id> [--lang ja,en] [--no-timestamps]
Requires: pip install youtube-transcript-api
"""
import argparse
import re
import sys
from urllib.parse import parse_qs, urlparse


def extract_video_id(s: str) -> str:
    s = s.strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", s):
        return s
    u = urlparse(s if "://" in s else "https://" + s)
    host = (u.hostname or "").lower()
    if host.endswith("youtu.be"):
        return u.path.lstrip("/").split("/")[0]
    if "youtube" in host:
        q = parse_qs(u.query).get("v")
        if q:
            return q[0]
        m = re.match(r"/(?:shorts|embed|live|v)/([A-Za-z0-9_-]{11})", u.path)
        if m:
            return m.group(1)
    sys.exit(f"error: could not find a video ID in {s!r}")


def fmt(t: float) -> str:
    t = int(t)
    h, m, s = t // 3600, t % 3600 // 60, t % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def fetch(video_id: str, langs: list[str]):
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        sys.exit("error: run `pip install youtube-transcript-api` first")

    api = YouTubeTranscriptApi()
    tlist = api.list(video_id)
    try:
        tr = tlist.find_transcript(langs)
    except Exception:
        # Fall back to any available transcript (manual first, then generated).
        available = list(tlist)
        if not available:
            sys.exit("error: this video has no transcripts")
        available.sort(key=lambda t: t.is_generated)
        tr = available[0]
    data = tr.fetch()
    snippets = [(s.start, s.text) for s in data]
    return tr.language_code, tr.is_generated, snippets


def main():
    p = argparse.ArgumentParser()
    p.add_argument("video")
    p.add_argument("--lang", default="ja,en", help="comma-separated preference order")
    p.add_argument("--no-timestamps", action="store_true")
    a = p.parse_args()

    vid = extract_video_id(a.video)
    try:
        lang, generated, snippets = fetch(vid, [l.strip() for l in a.lang.split(",") if l.strip()])
    except SystemExit:
        raise
    except Exception as e:
        sys.exit(f"error: failed to fetch transcript for {vid}: {type(e).__name__}: {e}")

    print(f"# video_id={vid} lang={lang} auto_generated={generated} snippets={len(snippets)}")
    for start, text in snippets:
        text = " ".join(text.split())
        if not text:
            continue
        print(text if a.no_timestamps else f"[{fmt(start)}] {text}")


if __name__ == "__main__":
    main()
