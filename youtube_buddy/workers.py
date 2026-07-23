"""Background workers for metadata and thumbnail loading."""

from __future__ import annotations

import urllib.request
from collections import deque

from PyQt6.QtCore import QThread, pyqtSignal

from youtube_buddy.media_urls import fetch_metadata

MAX_CONCURRENT_THUMBNAILS = 4


class MetadataWorker(QThread):
    finished_with_result = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, url: str, parent=None) -> None:
        super().__init__(parent)
        self.url = url

    def run(self) -> None:
        try:
            metadata = fetch_metadata(self.url)
        except Exception as exc:  # noqa: BLE001 — surface any fetch error to UI
            self.failed.emit(str(exc))
        else:
            self.finished_with_result.emit(metadata)


class ThumbnailWorker(QThread):
    loaded = pyqtSignal(int, bytes)
    failed = pyqtSignal(int)

    def __init__(self, video_row_id: int, url: str, parent=None) -> None:
        super().__init__(parent)
        self.video_row_id = video_row_id
        self.url = url

    def run(self) -> None:
        try:
            request = urllib.request.Request(
                self.url,
                headers={"User-Agent": "YouTubeBuddy/0.1"},
            )
            with urllib.request.urlopen(request, timeout=15) as response:
                data = response.read()
            if not data:
                raise ValueError("Empty thumbnail response")
        except Exception:  # noqa: BLE001
            self.failed.emit(self.video_row_id)
        else:
            self.loaded.emit(self.video_row_id, data)


class ThumbnailLoader:
    """Queue thumbnail downloads and limit concurrent workers."""

    def __init__(self, parent) -> None:
        self._parent = parent
        self._queue: deque[tuple[int, str]] = deque()
        self._active_workers: list[ThumbnailWorker] = []

    def enqueue(self, video_id: int, url: str) -> None:
        self._queue.append((video_id, url))
        self._start_pending()

    def wait_for_all(self, timeout_ms: int = 5000) -> None:
        for worker in list(self._active_workers):
            if worker.isRunning():
                worker.wait(timeout_ms)

    def clear(self, timeout_ms: int = 2000) -> None:
        self._queue.clear()
        for worker in list(self._active_workers):
            worker.loaded.disconnect()
            worker.failed.disconnect()
            worker.finished.disconnect()
            if worker.isRunning():
                worker.wait(timeout_ms)
            worker.deleteLater()
        self._active_workers.clear()

    def _start_pending(self) -> None:
        while self._queue and len(self._active_workers) < MAX_CONCURRENT_THUMBNAILS:
            video_id, url = self._queue.popleft()
            worker = ThumbnailWorker(video_id, url, parent=self._parent)
            worker.loaded.connect(self._parent._on_thumbnail_loaded)
            worker.failed.connect(self._parent._on_thumbnail_failed)
            worker.finished.connect(lambda worker=worker: self._worker_finished(worker))
            self._active_workers.append(worker)
            worker.start()

    def _worker_finished(self, worker: ThumbnailWorker) -> None:
        if worker in self._active_workers:
            self._active_workers.remove(worker)
        worker.deleteLater()
        self._start_pending()
