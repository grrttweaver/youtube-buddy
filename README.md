# YouTube Buddy

A cross-platform desktop app for managing an offline playlist of YouTube videos. Built with Python, PyQt6, and SQLite.

## Features

- Playlist table with **thumbnail**, **length**, and **title** columns
- Drag rows to reorder your playlist (order is saved automatically)
- Paste a YouTube URL and press **Enter**, or click **Add**
- Drag and drop YouTube links anywhere in the window
- SQLite backend with first-run setup to create or open a database

## Requirements

- Python 3.11+
- Network access when adding videos (to fetch metadata via yt-dlp)

## Setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

On first launch you'll be asked to create a new playlist database or open an existing one. Your choice is saved to your user config directory and reused on subsequent launches.

## Supported URLs

- `https://www.youtube.com/watch?v=…`
- `https://youtu.be/…`
- `https://www.youtube.com/shorts/…`

## Project layout

```
youtube-buddy/
├── main.py                 # Entry point
├── requirements.txt
└── youtube_buddy/
    ├── app.py              # Application bootstrap
    ├── config.py           # Saved preferences
    ├── database.py         # SQLite layer
    ├── main_window.py      # Main UI
    ├── setup_dialog.py     # First-run database setup
    ├── styles.py           # UI theme
    ├── video_model.py      # Table model with drag reorder
    ├── workers.py          # Background metadata/thumbnail loading
    └── youtube.py          # URL validation and metadata
```
