from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse


def youtube_video_id(text: str) -> str:
    value = (text or "").strip()
    urls = re.findall(r"https?://[^\s]+", value)
    for raw in urls:
        try:
            u = urlparse(raw.rstrip(".,;)]"))
            host = u.netloc.lower().split(":")[0]
            if host in {"youtu.be", "www.youtu.be"}:
                vid = u.path.strip("/").split("/")[0]
            elif host.endswith("youtube.com"):
                if u.path == "/watch":
                    vid = (parse_qs(u.query).get("v") or [""])[0]
                elif u.path.startswith("/shorts/") or u.path.startswith("/embed/") or u.path.startswith("/live/"):
                    vid = u.path.strip("/").split("/")[1]
                else:
                    vid = ""
            else:
                vid = ""
            if re.fullmatch(r"[A-Za-z0-9_-]{6,20}", vid or ""):
                return vid
        except Exception:
            continue
    return ""


def youtube_transcript(text: str, max_chars: int = 24000) -> dict:
    vid = youtube_video_id(text)
    if not vid:
        return {"matched": False, "video_id": "", "text": "", "source": None, "error": None}
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        api = YouTubeTranscriptApi()
        fetched = api.fetch(vid)
        rows = []
        for item in fetched:
            chunk = getattr(item, "text", None)
            if chunk is None and isinstance(item, dict):
                chunk = item.get("text")
            if chunk:
                rows.append(str(chunk).strip())
        transcript = " ".join(rows)
        return {
            "matched": True,
            "video_id": vid,
            "text": transcript[:max_chars],
            "source": {"title": "YouTube transcript", "url": f"https://www.youtube.com/watch?v={vid}"},
            "error": None,
        }
    except Exception as exc:
        return {"matched": True, "video_id": vid, "text": "", "source": None, "error": f"{type(exc).__name__}: {exc}"[:500]}
