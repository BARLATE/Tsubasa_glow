#!/usr/bin/env python3
"""Fetch a YouTube transcript and print it as "[mm:ss] text" lines.

Usage: fetch_transcript.py <url-or-id> [--lang ja,en] [--no-timestamps]
Requires: pip install youtube-transcript-api yt-dlp
Tries youtube-transcript-api first; if YouTube blocks it (common from cloud IPs),
falls back to yt-dlp subtitle download.
"""
import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path
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


def _vtt_ts(t: str) -> float:
    parts = t.split(":")
    secs = float(parts[-1])
    mins = int(parts[-2]) if len(parts) > 1 else 0
    hrs = int(parts[-3]) if len(parts) > 2 else 0
    return hrs * 3600 + mins * 60 + secs


def parse_vtt(text: str):
    """Parse WebVTT into (start, text), removing the rolling duplicates of auto captions."""
    out, seen_last = [], None
    for block in re.split(r"\n\s*\n", text):
        lines = block.strip().splitlines()
        idx = next((i for i, l in enumerate(lines) if "-->" in l), None)
        if idx is None:
            continue
        start = _vtt_ts(lines[idx].split("-->")[0].strip())
        for line in lines[idx + 1:]:
            line = re.sub(r"<[^>]+>", "", line).strip()
            if not line or line == seen_last:
                continue
            seen_last = line
            out.append((start, line))
    return out


def fetch_with_ytdlp(video_id: str, langs: list[str]):
    url = f"https://www.youtube.com/watch?v={video_id}"
    with tempfile.TemporaryDirectory() as d:
        for auto in (False, True):
            for lang in langs:
                cmd = [sys.executable, "-m", "yt_dlp", "--skip-download", "--quiet", "--no-warnings",
                       "--write-auto-subs" if auto else "--write-subs",
                       "--sub-langs", f"{lang},{lang}-orig" if auto else lang,
                       "--sub-format", "vtt", "-o", str(Path(d) / "%(id)s"), url]
                subprocess.run(cmd, capture_output=True, text=True)
                files = sorted(Path(d).glob("*.vtt"))
                if files:
                    snippets = parse_vtt(files[0].read_text(encoding="utf-8"))
                    if snippets:
                        return lang, auto, snippets
    raise RuntimeError("yt-dlp found no subtitles (or is not installed: pip install yt-dlp)")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("video")
    p.add_argument("--lang", default="ja,en", help="comma-separated preference order")
    p.add_argument("--no-timestamps", action="store_true")
    a = p.parse_args()

    vid = extract_video_id(a.video)
    langs = [l.strip() for l in a.lang.split(",") if l.strip()]
    try:
        lang, generated, snippets = fetch(vid, langs)
    except BaseException as e1:
        first = f"{type(e1).__name__}: {str(e1).strip().splitlines()[0] if str(e1).strip() else ''}"
        print(f"# youtube-transcript-api failed ({first}); trying yt-dlp", file=sys.stderr)
        try:
            lang, generated, snippets = fetch_with_ytdlp(vid, langs)
        except Exception as e2:
            sys.exit(f"error: failed to fetch transcript for {vid}: {first} / yt-dlp: {e2}")

    print(f"# video_id={vid} lang={lang} auto_generated={generated} snippets={len(snippets)}")
    for start, text in snippets:
        text = " ".join(text.split())
        if not text:
            continue
        print(text if a.no_timestamps else f"[{fmt(start)}] {text}")


if __name__ == "__main__":
    main()
