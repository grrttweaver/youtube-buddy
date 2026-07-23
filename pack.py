#!/usr/bin/env python3
"""Build YouTube Buddy distributables for the current or requested platform."""

from __future__ import annotations

import argparse
import importlib.util
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
PACKAGING = ROOT / "packaging"
BUILD = ROOT / "build"
DIST = ROOT / "dist"
SNAP_STAGING = ROOT / "snap" / "dist"
SNAP_DIR = PACKAGING / "snap"

APP_NAME = "YouTube Buddy"
APP_SLUG = "youtube-buddy"
VERSION = "0.1.0"
ENTRYPOINT = ROOT / "main.py"


def _icon_utils():
    spec = importlib.util.spec_from_file_location(
        "yb_icon_utils",
        PACKAGING / "icon_utils.py",
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load icon utilities.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def current_target() -> str:
    if sys.platform == "darwin":
        return "macos"
    if sys.platform in {"win32", "cygwin"}:
        return "windows"
    return "linux"


def target_platform(target: str) -> str:
    return current_target() if target == "current" else target


def ensure_pyinstaller() -> None:
    try:
        import PyInstaller  # noqa: F401
    except ImportError as exc:
        raise SystemExit(
            "PyInstaller is required. Install packaging dependencies with:\n"
            "  pip install -r requirements-packaging.txt"
        ) from exc


def ensure_runtime_deps(target: str) -> None:
    import importlib.util

    required = [
        ("PyQt6", "PyQt6"),
        ("yt_dlp", "yt-dlp"),
        ("platformdirs", "platformdirs"),
    ]
    if target == "macos":
        required.append(("pyqt_liquidglass", "pyqt-liquidglass"))

    missing: list[str] = []
    for module, pip_name in required:
        if importlib.util.find_spec(module) is None:
            missing.append(pip_name)

    if missing:
        raise SystemExit(
            "Missing runtime dependencies required for packaging:\n"
            + "\n".join(f"  - {name}" for name in missing)
            + "\n\nInstall with:\n  pip install -r requirements-packaging.txt"
        )


def run(cmd: list[str], *, cwd: Path | None = None) -> None:
    print(f"+ {' '.join(cmd)}")
    subprocess.run(cmd, cwd=cwd or ROOT, check=True)


def shaped_icon_png() -> Path:
    source = ASSETS / "icon.png"
    if not source.exists():
        raise SystemExit(f"Missing app icon: {source}")

    shaped = BUILD / "icon-macos.png"
    if shaped.exists() and shaped.stat().st_mtime >= source.stat().st_mtime:
        return shaped

    BUILD.mkdir(parents=True, exist_ok=True)
    from PIL import Image

    utils = _icon_utils()
    image = utils.apply_macos_icon_shape(Image.open(source))
    image.save(shaped, format="PNG")
    return shaped


def prepare_macos_icns() -> Path:
    icon_png = shaped_icon_png()
    icon_icns = ASSETS / "icon.icns"
    source = ASSETS / "icon.png"

    if icon_icns.exists() and icon_icns.stat().st_mtime >= source.stat().st_mtime:
        return icon_icns

    if shutil.which("sips") is None or shutil.which("iconutil") is None:
        print("Warning: sips/iconutil not found; using PNG icon for macOS build.")
        return icon_png

    iconset = BUILD / "icon.iconset"
    if iconset.exists():
        shutil.rmtree(iconset)
    iconset.mkdir(parents=True, exist_ok=True)

    for size in (16, 32, 128, 256, 512):
        run(
            [
                "sips",
                "-z",
                str(size),
                str(size),
                str(icon_png),
                "--out",
                str(iconset / f"icon_{size}x{size}.png"),
            ]
        )
        if size != 512:
            run(
                [
                    "sips",
                    "-z",
                    str(size * 2),
                    str(size * 2),
                    str(icon_png),
                    "--out",
                    str(iconset / f"icon_{size}x{size}@2x.png"),
                ]
            )

    run(["iconutil", "-c", "icns", str(iconset), "-o", str(icon_icns)])
    shutil.rmtree(iconset)
    return icon_icns


def prepare_windows_ico() -> Path:
    icon_png = ASSETS / "icon.png"
    icon_ico = ASSETS / "icon.ico"
    if not icon_png.exists():
        raise SystemExit(f"Missing app icon: {icon_png}")

    if icon_ico.exists() and icon_ico.stat().st_mtime >= icon_png.stat().st_mtime:
        return icon_ico

    try:
        from PIL import Image
    except ImportError:
        print("Warning: Pillow not installed; using PNG icon for Windows build.")
        return ASSETS / "icon.png"

    image = Image.open(shaped_icon_png())
    image.save(
        icon_ico,
        format="ICO",
        sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)],
    )
    return icon_ico


def icon_for_target(target: str) -> Path | None:
    icon_png = ASSETS / "icon.png"
    if not icon_png.exists():
        return None
    if target == "macos":
        return prepare_macos_icns()
    if target == "windows":
        return prepare_windows_ico()
    try:
        return shaped_icon_png()
    except SystemExit:
        return icon_png


def hidden_imports_for(target: str) -> list[str]:
    imports = [
        "youtube_buddy",
        "youtube_buddy.app",
        "youtube_buddy.main_window",
        "youtube_buddy.media_urls",
        "youtube_buddy.social",
        "youtube_buddy.youtube",
    ]
    if target == "macos":
        imports.extend(
            [
                "pyqt_liquidglass",
                "objc",
                "AppKit",
                "Foundation",
                "Quartz",
            ]
        )
    return imports


def data_separator(target: str) -> str:
    return ";" if target == "windows" else ":"


def executable_name(target: str) -> str:
    return "YouTube-Buddy" if target == "windows" else APP_SLUG


def pyinstaller_name(target: str) -> str:
    return APP_NAME if target == "macos" else executable_name(target)


def bundled_icon_path(target: str) -> Path:
    if target == "macos":
        return shaped_icon_png()
    icon_png = ASSETS / "icon.png"
    if not icon_png.exists():
        raise SystemExit(f"Missing app icon: {icon_png}")
    return icon_png


def pyinstaller_spec_path(target: str) -> Path:
    return PACKAGING / "pyinstaller" / f"{pyinstaller_name(target)}.spec"


def remove_stale_pyinstaller_spec(target: str) -> None:
    """Remove a cached spec so CLI collect/hidden-import flags are applied."""
    spec = pyinstaller_spec_path(target)
    if spec.exists():
        print(f"Removing stale PyInstaller spec: {spec}")
        spec.unlink()


def pyinstaller_command(target: str, *, onefile: bool, clean: bool) -> list[str]:
    sep = data_separator(target)
    icon_data = f"{bundled_icon_path(target)}{sep}assets"
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        str(ENTRYPOINT),
        "--name",
        pyinstaller_name(target),
        "--windowed",
        "--noconfirm",
        f"--add-data={icon_data}",
        "--specpath",
        str(PACKAGING / "pyinstaller"),
        "--distpath",
        str(DIST),
        "--workpath",
        str(BUILD),
    ]

    for package in ("PyQt6", "PyQt6-Qt6", "yt_dlp"):
        cmd.extend(["--collect-all", package])

    for hidden_import in hidden_imports_for(target):
        cmd.extend(["--hidden-import", hidden_import])

    icon = icon_for_target(target)
    if icon is not None:
        cmd.extend(["--icon", str(icon)])

    if target == "macos":
        cmd.extend(["--osx-bundle-identifier", "com.youtubebuddy.app"])

    if onefile:
        cmd.append("--onefile")

    if clean:
        cmd.append("--clean")

    return cmd


def artifact_path(target: str, *, onefile: bool) -> Path:
    if target == "macos":
        return DIST / f"{APP_NAME}.app"
    name = executable_name(target)
    if onefile:
        suffix = ".exe" if target == "windows" else ""
        return DIST / f"{name}{suffix}"
    suffix = ".exe" if target == "windows" else ""
    return DIST / name / f"{name}{suffix}"


def build_pyinstaller(target: str, *, onefile: bool, clean: bool) -> Path:
    if target != current_target():
        raise SystemExit(
            f"Cannot build '{target}' artifacts on {platform.system()} ({sys.platform}). "
            f"Run this command on {target} instead."
        )

    ensure_pyinstaller()
    ensure_runtime_deps(target)
    BUILD.mkdir(parents=True, exist_ok=True)
    DIST.mkdir(parents=True, exist_ok=True)
    remove_stale_pyinstaller_spec(target)
    run(pyinstaller_command(target, onefile=onefile, clean=clean))

    artifact = artifact_path(target, onefile=onefile)
    if not artifact.exists():
        raise SystemExit(f"Expected build artifact was not created: {artifact}")
    return artifact


def stage_for_snap(linux_artifact: Path) -> Path:
    if SNAP_STAGING.exists():
        shutil.rmtree(SNAP_STAGING)
    SNAP_STAGING.mkdir(parents=True, exist_ok=True)
    staged_binary = SNAP_STAGING / APP_SLUG
    shutil.copy2(linux_artifact, staged_binary)
    staged_binary.chmod(staged_binary.stat().st_mode | 0o111)
    return staged_binary


def build_snap(*, clean: bool) -> Path:
    if current_target() != "linux":
        raise SystemExit("Snap packages must be built on Linux with snapcraft installed.")

    if shutil.which("snapcraft") is None:
        raise SystemExit(
            "snapcraft was not found. Install it with:\n"
            "  sudo snap install snapcraft --classic"
        )

    artifact = build_pyinstaller("linux", onefile=True, clean=clean)
    stage_for_snap(artifact)
    run(["snapcraft"], cwd=SNAP_DIR)

    snap_files = sorted(SNAP_DIR.glob("*.snap"), key=lambda path: path.stat().st_mtime)
    if not snap_files:
        snap_files = sorted(ROOT.glob("*.snap"), key=lambda path: path.stat().st_mtime)
    if not snap_files:
        raise SystemExit("Snap build finished but no .snap file was found.")
    return snap_files[-1]


def print_result(label: str, artifact: Path) -> None:
    print()
    print(f"Built {label} artifact:")
    print(f"  {artifact}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Package YouTube Buddy")
    parser.add_argument(
        "--target",
        choices=["current", "macos", "windows", "linux", "snap", "all"],
        default="current",
        help="Platform artifact to build (default: current platform)",
    )
    parser.add_argument(
        "--onefile",
        action="store_true",
        help="Build a single-file executable where supported",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean PyInstaller cache before building",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.target == "all":
        native = current_target()
        use_onefile = args.onefile or native == "windows"
        built = build_pyinstaller(native, onefile=use_onefile, clean=args.clean)
        print_result(native, built)
        if native == "linux":
            snap = build_snap(clean=args.clean)
            print_result("snap", snap)
        else:
            print("Skipped snap build because snapcraft requires Linux.")
        return 0

    if args.target in {"current", "macos", "windows", "linux"}:
        target = target_platform(args.target)
        use_onefile = args.onefile or target == "windows"
        artifact = build_pyinstaller(target, onefile=use_onefile, clean=args.clean)
        print_result(target, artifact)
        return 0

    snap = build_snap(clean=args.clean)
    print_result("snap", snap)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
