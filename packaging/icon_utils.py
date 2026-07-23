"""Helpers for shaping app icons to match platform conventions."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

# Approximate macOS Big Sur+ app icon corner curvature.
MACOS_ICON_CORNER_RATIO = 0.2237


def apply_macos_icon_shape(
    image: Image.Image,
    *,
    corner_ratio: float = MACOS_ICON_CORNER_RATIO,
) -> Image.Image:
    """Return a square RGBA icon with macOS-style rounded corners."""
    size = min(image.size)
    if image.size != (size, size):
        image = image.resize((size, size), Image.Resampling.LANCZOS)

    rgba = image.convert("RGBA")
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    radius = max(1, round(size * corner_ratio))
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=255)

    shaped = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    shaped.paste(rgba, (0, 0), mask)
    return shaped


def shape_icon_file(path: Path, *, corner_ratio: float = MACOS_ICON_CORNER_RATIO) -> None:
    image = Image.open(path)
    shaped = apply_macos_icon_shape(image, corner_ratio=corner_ratio)
    shaped.save(path, format="PNG")
