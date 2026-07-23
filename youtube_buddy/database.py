"""SQLite persistence for playlist videos."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

DATABASE_SUFFIX = ".ytbud"
LEGACY_DATABASE_SUFFIX = ".db"
DEFAULT_DATABASE_NAME = f"youtube-buddy-playlist{DATABASE_SUFFIX}"

DATABASE_OPEN_FILTER = (
    f"YouTube Buddy Playlist (*{DATABASE_SUFFIX});;"
    f"Legacy Playlist (*{LEGACY_DATABASE_SUFFIX});;"
    "All Files (*)"
)
DATABASE_SAVE_FILTER = (
    f"YouTube Buddy Playlist (*{DATABASE_SUFFIX});;All Files (*)"
)


def default_database_path() -> Path:
    return Path.home() / DEFAULT_DATABASE_NAME


def ensure_database_suffix(path: Path) -> Path:
    suffix = path.suffix.lower()
    if suffix in {DATABASE_SUFFIX, LEGACY_DATABASE_SUFFIX}:
        return path
    return path.with_suffix(DATABASE_SUFFIX)


def is_legacy_database(path: Path) -> bool:
    return path.suffix.lower() == LEGACY_DATABASE_SUFFIX


def migrate_legacy_database(path: Path) -> Path:
    """Rename a legacy .db playlist to .ytbud and update stored paths."""
    resolved = path.resolve()
    if not is_legacy_database(resolved):
        return resolved

    target = resolved.with_suffix(DATABASE_SUFFIX)
    if not target.exists():
        resolved.rename(target)

    from youtube_buddy.config import replace_database_path

    replace_database_path(resolved, target)
    return target


def migrate_stored_database_paths() -> None:
    """Convert any legacy .db paths saved in config."""
    from youtube_buddy.config import get_database_path, get_recent_database_paths

    candidates: list[Path] = []
    if current := get_database_path():
        candidates.append(current)
    candidates.extend(get_recent_database_paths())

    seen: set[Path] = set()
    for path in candidates:
        resolved = path.resolve()
        if resolved in seen or not resolved.exists() or not is_legacy_database(resolved):
            continue
        seen.add(resolved)
        migrate_legacy_database(resolved)


@dataclass
class Video:
    id: int
    url: str
    video_id: str
    title: str | None
    duration_seconds: int | None
    thumbnail_url: str | None
    sort_order: int
    is_playlist: bool = False
    is_short: bool = False
    platform: str = "youtube"


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._conn = sqlite3.connect(str(path))
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL UNIQUE,
                video_id TEXT NOT NULL,
                title TEXT,
                duration_seconds INTEGER,
                thumbnail_url TEXT,
                sort_order INTEGER NOT NULL
            )
            """
        )
        self._conn.commit()
        self._migrate_schema()

    def _migrate_schema(self) -> None:
        columns = {
            row["name"] for row in self._conn.execute("PRAGMA table_info(videos)").fetchall()
        }
        if "is_playlist" not in columns:
            self._conn.execute(
                "ALTER TABLE videos ADD COLUMN is_playlist INTEGER NOT NULL DEFAULT 0"
            )
            self._conn.commit()
        columns = {
            row["name"] for row in self._conn.execute("PRAGMA table_info(videos)").fetchall()
        }
        if "is_short" not in columns:
            self._conn.execute(
                "ALTER TABLE videos ADD COLUMN is_short INTEGER NOT NULL DEFAULT 0"
            )
            self._conn.commit()
        columns = {
            row["name"] for row in self._conn.execute("PRAGMA table_info(videos)").fetchall()
        }
        if "platform" not in columns:
            self._conn.execute(
                "ALTER TABLE videos ADD COLUMN platform TEXT NOT NULL DEFAULT 'youtube'"
            )
            self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def list_videos(self) -> list[Video]:
        rows = self._conn.execute(
            "SELECT * FROM videos ORDER BY sort_order ASC, id ASC"
        ).fetchall()
        return [self._row_to_video(row) for row in rows]

    def video_by_url(self, url: str) -> Video | None:
        row = self._conn.execute(
            "SELECT * FROM videos WHERE url = ?", (url,)
        ).fetchone()
        return self._row_to_video(row) if row else None

    def next_sort_order(self) -> int:
        row = self._conn.execute(
            "SELECT COALESCE(MAX(sort_order), -1) + 1 AS next_order FROM videos"
        ).fetchone()
        return int(row["next_order"])

    def insert_video(
        self,
        *,
        url: str,
        video_id: str,
        title: str | None = None,
        duration_seconds: int | None = None,
        thumbnail_url: str | None = None,
        is_playlist: bool = False,
        is_short: bool = False,
        platform: str = "youtube",
    ) -> Video:
        sort_order = self.next_sort_order()
        cursor = self._conn.execute(
            """
            INSERT INTO videos (url, video_id, title, duration_seconds, thumbnail_url, sort_order, is_playlist, is_short, platform)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                url,
                video_id,
                title,
                duration_seconds,
                thumbnail_url,
                sort_order,
                int(is_playlist),
                int(is_short),
                platform,
            ),
        )
        self._conn.commit()
        row = self._conn.execute(
            "SELECT * FROM videos WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return self._row_to_video(row)

    def update_video_metadata(
        self,
        video_id: int,
        *,
        title: str | None,
        duration_seconds: int | None,
        thumbnail_url: str | None,
    ) -> None:
        self._conn.execute(
            """
            UPDATE videos
            SET title = ?, duration_seconds = ?, thumbnail_url = ?
            WHERE id = ?
            """,
            (title, duration_seconds, thumbnail_url, video_id),
        )
        self._conn.commit()

    def update_sort_orders(self, ordered_ids: list[int]) -> None:
        for index, video_id in enumerate(ordered_ids):
            self._conn.execute(
                "UPDATE videos SET sort_order = ? WHERE id = ?",
                (index, video_id),
            )
        self._conn.commit()

    def delete_video(self, video_id: int) -> None:
        self._conn.execute("DELETE FROM videos WHERE id = ?", (video_id,))
        self._conn.commit()

    def delete_videos(self, video_ids: list[int]) -> None:
        if not video_ids:
            return
        placeholders = ", ".join("?" for _ in video_ids)
        self._conn.execute(
            f"DELETE FROM videos WHERE id IN ({placeholders})",
            video_ids,
        )
        self._conn.commit()

    @staticmethod
    def _row_to_video(row: sqlite3.Row) -> Video:
        return Video(
            id=row["id"],
            url=row["url"],
            video_id=row["video_id"],
            title=row["title"],
            duration_seconds=row["duration_seconds"],
            thumbnail_url=row["thumbnail_url"],
            sort_order=row["sort_order"],
            is_playlist=bool(row["is_playlist"]) if "is_playlist" in row.keys() else False,
            is_short=bool(row["is_short"]) if "is_short" in row.keys() else False,
            platform=row["platform"] if "platform" in row.keys() else "youtube",
        )
