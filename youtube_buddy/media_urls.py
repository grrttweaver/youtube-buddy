"""Unified media URL parsing across supported platforms."""

from __future__ import annotations

from youtube_buddy.social import (
    fetch_facebook_reel_metadata,
    fetch_instagram_reel_metadata,
    is_facebook_reel_url,
    is_instagram_reel_url,
    normalize_facebook_reel_url,
    normalize_instagram_reel_url,
)
from youtube_buddy.youtube import (
    VideoMetadata,
    fetch_metadata as fetch_youtube_metadata,
    is_playlist_url,
    is_short_url,
    normalize_youtube_url,
)


def normalize_media_url(raw: str) -> str | None:
    for normalizer in (
        normalize_youtube_url,
        normalize_instagram_reel_url,
        normalize_facebook_reel_url,
    ):
        if normalized := normalizer(raw):
            return normalized
    return None


def media_platform(url: str) -> str | None:
    if normalize_youtube_url(url):
        return "youtube"
    if is_instagram_reel_url(url):
        return "instagram"
    if is_facebook_reel_url(url):
        return "facebook"
    return None


def extract_media_url_from_text(text: str) -> str | None:
    for token in text.strip().split():
        if normalized := normalize_media_url(token):
            return normalized
    return normalize_media_url(text)


def fetch_metadata(url: str) -> VideoMetadata:
    normalized = normalize_media_url(url) or url.strip()
    platform = media_platform(normalized)

    if platform == "instagram":
        return fetch_instagram_reel_metadata(normalized)
    if platform == "facebook":
        return fetch_facebook_reel_metadata(normalized)
    if platform == "youtube":
        return fetch_youtube_metadata(normalized)

    raise ValueError("Unsupported media URL")


# Backward-compatible aliases used internally
extract_youtube_url_from_text = extract_media_url_from_text

__all__ = [
    "VideoMetadata",
    "extract_media_url_from_text",
    "extract_youtube_url_from_text",
    "fetch_metadata",
    "is_facebook_reel_url",
    "is_instagram_reel_url",
    "is_playlist_url",
    "is_short_url",
    "media_platform",
    "normalize_media_url",
    "normalize_youtube_url",
]
