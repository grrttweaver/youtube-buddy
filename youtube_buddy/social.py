"""Instagram and Facebook Reels URL parsing and metadata extraction."""

from __future__ import annotations

import re

import yt_dlp

from youtube_buddy.youtube import VideoMetadata, _ytdlp_options

INSTAGRAM_HOSTS = {"instagram.com", "www.instagram.com"}
FACEBOOK_HOSTS = {"facebook.com", "www.facebook.com", "m.facebook.com", "fb.watch", "www.fb.watch"}

INSTAGRAM_REEL_PATH = re.compile(r"^/(?:reel|reels)/([A-Za-z0-9_-]+)/?", re.IGNORECASE)
INSTAGRAM_REEL_ID = re.compile(r"^[A-Za-z0-9_-]+$")

FACEBOOK_REEL_PATH = re.compile(r"^/reels?/(\d+)/?", re.IGNORECASE)
FACEBOOK_REEL_ID = re.compile(r"^\d+$")
FB_WATCH_PATH = re.compile(r"^/([A-Za-z0-9_-]+)/?", re.IGNORECASE)


def _prepare_url(raw: str) -> str:
    text = raw.strip()
    if not text.startswith(("http://", "https://")):
        text = "https://" + text
    return text


def extract_instagram_reel_id(url: str) -> str | None:
    from urllib.parse import urlparse

    parsed = urlparse(_prepare_url(url))
    host = parsed.netloc.lower().removeprefix("www.")
    if host not in {h.removeprefix("www.") for h in INSTAGRAM_HOSTS}:
        return None

    match = INSTAGRAM_REEL_PATH.match(parsed.path)
    if not match:
        return None

    reel_id = match.group(1)
    return reel_id if INSTAGRAM_REEL_ID.match(reel_id) else None


def normalize_instagram_reel_url(raw: str) -> str | None:
    reel_id = extract_instagram_reel_id(raw)
    if not reel_id:
        return None
    return f"https://www.instagram.com/reel/{reel_id}/"


def is_instagram_reel_url(url: str) -> bool:
    return normalize_instagram_reel_url(url) is not None


def extract_facebook_reel_id(url: str) -> str | None:
    from urllib.parse import urlparse

    parsed = urlparse(_prepare_url(url))
    host = parsed.netloc.lower().removeprefix("www.")

    if host == "fb.watch":
        match = FB_WATCH_PATH.match(parsed.path)
        if match:
            return match.group(1)
        return None

    if host not in {"facebook.com", "m.facebook.com"}:
        return None

    match = FACEBOOK_REEL_PATH.match(parsed.path)
    if not match:
        return None

    reel_id = match.group(1)
    return reel_id if FACEBOOK_REEL_ID.match(reel_id) else None


def normalize_facebook_reel_url(raw: str) -> str | None:
    from urllib.parse import urlparse

    text = _prepare_url(raw)
    parsed = urlparse(text)
    host = parsed.netloc.lower().removeprefix("www.")

    if host == "fb.watch":
        match = FB_WATCH_PATH.match(parsed.path)
        if match:
            return f"https://fb.watch/{match.group(1)}/"
        return None

    reel_id = extract_facebook_reel_id(text)
    if reel_id:
        return f"https://www.facebook.com/reel/{reel_id}"

    return None


def is_facebook_reel_url(url: str) -> bool:
    return normalize_facebook_reel_url(url) is not None


def _thumbnail_from_info(info: dict) -> str | None:
    thumbnail = info.get("thumbnail")
    if thumbnail:
        return thumbnail

    thumbnails = info.get("thumbnails") or []
    if thumbnails:
        return thumbnails[-1].get("url")

    return None


def fetch_instagram_reel_metadata(url: str) -> VideoMetadata:
    stored_url = normalize_instagram_reel_url(url) or url
    reel_id = extract_instagram_reel_id(stored_url)
    if not reel_id:
        raise ValueError("Invalid Instagram Reel URL")

    with yt_dlp.YoutubeDL(_ytdlp_options()) as ydl:
        info = ydl.extract_info(stored_url, download=False)

    duration = info.get("duration")
    return VideoMetadata(
        url=stored_url,
        video_id=str(info.get("id") or reel_id),
        title=info.get("title") or "Instagram Reel",
        duration_seconds=int(duration) if duration is not None else None,
        thumbnail_url=_thumbnail_from_info(info),
        platform="instagram",
    )


def fetch_facebook_reel_metadata(url: str) -> VideoMetadata:
    stored_url = normalize_facebook_reel_url(url) or url
    reel_id = extract_facebook_reel_id(stored_url)
    if not reel_id and "fb.watch" not in stored_url:
        raise ValueError("Invalid Facebook Reel URL")

    with yt_dlp.YoutubeDL(_ytdlp_options()) as ydl:
        info = ydl.extract_info(stored_url, download=False)

    duration = info.get("duration")
    return VideoMetadata(
        url=stored_url,
        video_id=str(info.get("id") or reel_id or stored_url.rstrip("/").split("/")[-1]),
        title=info.get("title") or "Facebook Reel",
        duration_seconds=int(duration) if duration is not None else None,
        thumbnail_url=_thumbnail_from_info(info),
        platform="facebook",
    )
