"""YouTube URL parsing and metadata extraction."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

import yt_dlp
from yt_dlp.utils import DownloadError, ExtractorError

YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtu.be",
}

VIDEO_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")
PLAYLIST_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{10,}$")

# Mix/radio playlists are tied to a seed video and use watch URLs in YouTube.
MIX_PLAYLIST_PREFIXES = ("RD", "RL", "RDCLAK", "RDCM", "RDMV")


@dataclass
class VideoMetadata:
    url: str
    video_id: str
    title: str
    duration_seconds: int | None
    thumbnail_url: str | None
    is_playlist: bool = False
    is_short: bool = False
    platform: str = "youtube"


class _QuietLogger:
    def debug(self, msg) -> None:
        pass

    def info(self, msg) -> None:
        pass

    def warning(self, msg) -> None:
        pass

    def error(self, msg) -> None:
        pass


def _ytdlp_options(**overrides) -> dict:
    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "logger": _QuietLogger(),
    }
    options.update(overrides)
    return options


def is_mix_playlist(playlist_id: str) -> bool:
    return playlist_id.startswith(MIX_PLAYLIST_PREFIXES)


def normalize_youtube_url(raw: str) -> str | None:
    text = raw.strip()
    if not text:
        return None

    if not text.startswith(("http://", "https://")):
        text = "https://" + text

    parsed = urlparse(text)
    host = parsed.netloc.lower().removeprefix("www.")
    if host not in {h.removeprefix("www.") for h in YOUTUBE_HOSTS}:
        return None

    playlist_id = extract_playlist_id(text)
    video_id = extract_video_id(text)

    if playlist_id:
        if video_id and is_mix_playlist(playlist_id):
            return f"https://www.youtube.com/watch?v={video_id}&list={playlist_id}"
        return f"https://www.youtube.com/playlist?list={playlist_id}"

    if video_id:
        if is_short_url(text):
            return f"https://www.youtube.com/shorts/{video_id}"
        return f"https://www.youtube.com/watch?v={video_id}"

    return None


def extract_playlist_id(url: str) -> str | None:
    parsed = urlparse(url.strip())
    host = parsed.netloc.lower()

    if "youtube.com" not in host:
        return None

    query_list = parse_qs(parsed.query).get("list", [])
    if query_list and PLAYLIST_ID_PATTERN.match(query_list[0]):
        return query_list[0]

    if parsed.path.rstrip("/") == "/playlist" and query_list:
        return query_list[0] if PLAYLIST_ID_PATTERN.match(query_list[0]) else None

    return None


def extract_video_id(url: str) -> str | None:
    parsed = urlparse(url.strip())
    host = parsed.netloc.lower()

    if extract_playlist_id(url) and not parse_qs(parsed.query).get("v"):
        return None

    if host in {"youtu.be", "www.youtu.be"}:
        candidate = parsed.path.lstrip("/").split("/")[0]
        return candidate if VIDEO_ID_PATTERN.match(candidate) else None

    if "youtube.com" in host:
        if parsed.path == "/watch":
            values = parse_qs(parsed.query).get("v", [])
            if values and VIDEO_ID_PATTERN.match(values[0]):
                return values[0]
        if parsed.path.startswith("/shorts/"):
            candidate = parsed.path.split("/")[2] if len(parsed.path.split("/")) > 2 else ""
            return candidate if VIDEO_ID_PATTERN.match(candidate) else None
        if parsed.path.startswith("/embed/"):
            candidate = parsed.path.split("/")[2] if len(parsed.path.split("/")) > 2 else ""
            return candidate if VIDEO_ID_PATTERN.match(candidate) else None

    return None


def is_playlist_url(url: str) -> bool:
    return extract_playlist_id(url) is not None


def is_short_url(url: str) -> bool:
    parsed = urlparse(url.strip())
    if "youtube.com" not in parsed.netloc.lower():
        return False
    return parsed.path.startswith("/shorts/")


def extract_youtube_url_from_text(text: str) -> str | None:
    for token in re.split(r"\s+", text.strip()):
        normalized = normalize_youtube_url(token)
        if normalized:
            return normalized
    return normalize_youtube_url(text)


def fetch_metadata(url: str) -> VideoMetadata:
    playlist_id = extract_playlist_id(url)
    if playlist_id:
        return _fetch_playlist_metadata(playlist_id, url)

    video_id = extract_video_id(url)
    if not video_id:
        raise ValueError("Invalid YouTube URL")

    stored_url = normalize_youtube_url(url) or url
    return _fetch_video_metadata(
        video_id,
        stored_url,
        is_short=is_short_url(stored_url),
    )


def _fetch_video_metadata(
    video_id: str,
    url: str,
    *,
    is_short: bool = False,
) -> VideoMetadata:
    with yt_dlp.YoutubeDL(_ytdlp_options(extract_flat=False)) as ydl:
        info = ydl.extract_info(url, download=False)

    title = info.get("title") or "Untitled"
    duration = info.get("duration")
    thumbnail = info.get("thumbnail")

    return VideoMetadata(
        url=url,
        video_id=video_id,
        title=title,
        duration_seconds=int(duration) if duration is not None else None,
        thumbnail_url=thumbnail,
        is_playlist=False,
        is_short=is_short,
        platform="youtube",
    )


def _entry_thumbnail(entry: dict) -> str | None:
    thumbnail = entry.get("thumbnail")
    if thumbnail:
        return thumbnail

    thumbnails = entry.get("thumbnails") or []
    if thumbnails:
        return thumbnails[-1].get("url")

    video_id = entry.get("id")
    if video_id and VIDEO_ID_PATTERN.match(str(video_id)):
        return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"

    return None


def _first_playlist_entry(info: dict) -> dict | None:
    for entry in info.get("entries") or []:
        if entry:
            return entry
    return None


def _thumbnail_from_playlist_info(info: dict) -> str | None:
    thumbnail = info.get("thumbnail")
    if thumbnail:
        return thumbnail

    thumbnails = info.get("thumbnails") or []
    if thumbnails:
        return thumbnails[-1].get("url")

    first_entry = _first_playlist_entry(info)
    if first_entry:
        return _entry_thumbnail(first_entry)

    return None


def _default_playlist_title(playlist_id: str) -> str:
    if playlist_id.startswith(("RD", "RL", "RDCLAK", "RDCM", "RDMV")):
        return "YouTube Mix"
    if playlist_id.startswith("LL"):
        return "Liked Videos"
    if playlist_id.startswith("FL"):
        return "Favorites"
    if playlist_id.startswith("OLAK"):
        return "Album"
    return "YouTube Playlist"


def _playlist_fallback_metadata(playlist_id: str, playlist_url: str) -> VideoMetadata:
    thumbnail = _fetch_playlist_first_video_thumbnail(playlist_url)
    if not thumbnail:
        seed_video_id = extract_video_id(playlist_url)
        if seed_video_id:
            thumbnail = f"https://i.ytimg.com/vi/{seed_video_id}/hqdefault.jpg"

    return VideoMetadata(
        url=playlist_url,
        video_id=playlist_id,
        title=_default_playlist_title(playlist_id),
        duration_seconds=None,
        thumbnail_url=thumbnail,
        is_playlist=True,
        platform="youtube",
    )


def _fetch_playlist_first_video_thumbnail(playlist_url: str) -> str | None:
    for overrides in (
        {"extract_flat": "in_playlist", "playlistend": 1},
        {"extract_flat": False, "playlistend": 1},
    ):
        try:
            with yt_dlp.YoutubeDL(_ytdlp_options(**overrides)) as ydl:
                info = ydl.extract_info(playlist_url, download=False)
            thumbnail = _thumbnail_from_playlist_info(info)
            if thumbnail:
                return thumbnail
        except (DownloadError, ExtractorError, KeyError, TypeError, ValueError):
            continue
    return None


def _fetch_playlist_metadata(playlist_id: str, url: str) -> VideoMetadata:
    stored_url = normalize_youtube_url(url) or url
    if not stored_url:
        stored_url = f"https://www.youtube.com/playlist?list={playlist_id}"

    try:
        return _fetch_playlist_metadata_via_ytdlp(playlist_id, stored_url)
    except (DownloadError, ExtractorError, KeyError, TypeError, ValueError):
        pass

    seed_video_id = extract_video_id(stored_url)
    if seed_video_id:
        try:
            video_meta = _fetch_video_metadata(
                seed_video_id,
                f"https://www.youtube.com/watch?v={seed_video_id}",
            )
            title = _default_playlist_title(playlist_id)
            if is_mix_playlist(playlist_id):
                title = f"YouTube Mix · {video_meta.title}"
            return VideoMetadata(
                url=stored_url,
                video_id=playlist_id,
                title=title,
                duration_seconds=None,
                thumbnail_url=video_meta.thumbnail_url,
                is_playlist=True,
                platform="youtube",
            )
        except (DownloadError, ExtractorError, KeyError, TypeError, ValueError):
            pass

    return _playlist_fallback_metadata(playlist_id, stored_url)


def _fetch_playlist_metadata_via_ytdlp(
    playlist_id: str,
    playlist_url: str,
) -> VideoMetadata:
    with yt_dlp.YoutubeDL(
        _ytdlp_options(extract_flat="in_playlist"),
    ) as ydl:
        info = ydl.extract_info(playlist_url, download=False)

    title = info.get("title") or _default_playlist_title(playlist_id)
    thumbnail = _thumbnail_from_playlist_info(info)
    if not thumbnail:
        thumbnail = _fetch_playlist_first_video_thumbnail(playlist_url)

    return VideoMetadata(
        url=playlist_url,
        video_id=playlist_id,
        title=title,
        duration_seconds=None,
        thumbnail_url=thumbnail,
        is_playlist=True,
        platform="youtube",
    )


def format_duration(seconds: int | None) -> str:
    if seconds is None:
        return "—"
    minutes, secs = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"
