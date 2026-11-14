# /// script
# requires-python = ">=3.10"
# dependencies = ["yt-dlp", "youtube-transcript-api>=1.0"]
# ///
"""Save the transcript of every video in a YouTube playlist as a Markdown file.

Usage:
    uv run fetch_transcripts.py <playlist_url> [--out transcripts] [--langs en hi] [--translate-to en]
"""

import argparse
import re
import time
from pathlib import Path

import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import NoTranscriptFound, TranscriptsDisabled


def list_playlist(url: str) -> list[dict]:
    opts = {"extract_flat": True, "quiet": True, "skip_download": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    return [{"id": e["id"], "title": e.get("title") or e["id"]} for e in info["entries"] if e]


def pick_transcript(api: YouTubeTranscriptApi, video_id: str, langs: list[str]):
    transcripts = api.list(video_id)
    try:
        # Prefer manually created captions, then auto-generated, in the given language order.
        return transcripts.find_transcript(langs)
    except NoTranscriptFound:
        # Fall back to whatever exists, translated to the first preferred language if possible.
        first = next(iter(transcripts))
        if first.is_translatable and first.language_code != langs[0]:
            return first.translate(langs[0])
        return first


def fmt_ts(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[\s_-]+", "-", text)[:80]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("playlist_url")
    parser.add_argument("--out", default="transcripts")
    parser.add_argument("--langs", nargs="+", default=["en", "hi"])
    parser.add_argument("--translate-to", help="language code to machine-translate captions into, e.g. en")
    parser.add_argument("--delay",type=float, default=2.0, help="seconds between videos (avoids rate limits)")
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    api = YouTubeTranscriptApi()
    videos = list_playlist(args.playlist_url)
    print(f"Found {len(videos)} videos")

    failed = []
    for i, v in enumerate(videos, 1):
        path = out / f"{i:02d}-{slugify(v['title'])}.md"
        if path.exists():
            print(f"[{i}/{len(videos)}] skip (exists): {v['title']}")
            continue
        try:
            t = pick_transcript(api, v["id"], args.langs)
            if args.translate_to and t.language_code != args.translate_to and t.is_translatable:
                t = t.translate(args.translate_to)
            snippets = t.fetch()
        except (TranscriptsDisabled, NoTranscriptFound, StopIteration) as e:
            print(f"[{i}/{len(videos)}] NO TRANSCRIPT: {v['title']} ({type(e).__name__})")
            failed.append(v)
            continue
        except Exception as e:  # network errors, IP blocks, etc.
            print(f"[{i}/{len(videos)}] ERROR: {v['title']}: {e}")
            failed.append(v)
            continue

        kind = "auto-generated" if t.is_generated else "manual"
        lines = [
            f"# {v['title']}",
            "",
            f"- URL: https://www.youtube.com/watch?v={v['id']}",
            f"- Transcript: {t.language} ({t.language_code}, {kind})",
            "",
        ]
        lines += [f"[{fmt_ts(s.start)}] {s.text.replace(chr(10), ' ')}" for s in snippets]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"[{i}/{len(videos)}] saved: {path.name}")
        time.sleep(args.delay)

    print(f"\nDone. {len(videos) - len(failed)} saved/skipped, {len(failed)} failed.")
    for v in failed:
        print(f"  - {v['title']} https://www.youtube.com/watch?v={v['id']}")


if __name__ == "__main__":
    main()
