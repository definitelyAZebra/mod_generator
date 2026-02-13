# -*- coding: utf-8 -*-
"""
从 Steam CDN 下载干净的 modbranch data.win。

使用 DepotDownloader 从 Steam 下载 Stoneshard modbranch 的 data.win，
输出到 datamine/input/data.win，不影响本地游戏安装。

首次运行需要交互式 Steam 登录 (用户名 + Steam Guard)，
之后使用 -remember-password 缓存 session。

用法:
    python datamine/fetch_data_win.py -u <steam_user>              # 下载 latest modbranch
    python datamine/fetch_data_win.py -u <user> --manifest <id>   # 下载指定 manifest (历史版本)
    python datamine/fetch_data_win.py --setup-only                # 仅下载 DepotDownloader
    python datamine/fetch_data_win.py --check                     # 检查当前状态

数据源: Steam CDN (Stoneshard app 625960, depot 625961, branch modbranch)
输出:
    datamine/input/data.win             游戏数据文件
    datamine/input/provenance.json      版本溯源信息 (SHA256, 游戏版本, manifest 等)
"""

from __future__ import annotations

import datetime
import hashlib
import io
import json
import platform
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

# ── paths ──────────────────────────────────────────────────────────
DATAMINE_DIR = Path(__file__).resolve().parent
VENDOR_DIR = DATAMINE_DIR / "vendor"
DD_DIR = VENDOR_DIR / "DepotDownloader"
DD_VERSION_FILE = DD_DIR / ".version"
INPUT_DIR = DATAMINE_DIR / "input"
DATA_WIN = INPUT_DIR / "data.win"
PROVENANCE_FILE = INPUT_DIR / "provenance.json"

# ── Steam constants ────────────────────────────────────────────────
STONESHARD_APP_ID = 625960
STONESHARD_DEPOT_ID = 625961
BRANCH = "modbranch"

# ── DepotDownloader GitHub ─────────────────────────────────────────
DD_REPO = "SteamRE/DepotDownloader"
DD_API_BASE = f"https://api.github.com/repos/{DD_REPO}/releases"


def _dd_platform_tag() -> str:
    """Map current OS + arch to DepotDownloader asset name fragment."""
    s = platform.system()
    m = platform.machine().lower()

    if s == "Windows":
        if m in ("arm64", "aarch64"):
            return "windows-arm64"
        return "windows-x64"
    elif s == "Darwin":
        if m in ("arm64", "aarch64"):
            return "macos-arm64"
        return "macos-x64"
    elif s == "Linux":
        if m in ("arm64", "aarch64"):
            return "linux-arm64"
        elif "arm" in m:
            return "linux-arm"
        return "linux-x64"
    raise RuntimeError(f"Unsupported platform: {s} {m}")


def _dd_exe_name() -> str:
    if platform.system() == "Windows":
        return "DepotDownloader.exe"
    return "DepotDownloader"


# ── GitHub API ─────────────────────────────────────────────────────

def _api_get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def _find_dd_release() -> dict:
    return _api_get(f"{DD_API_BASE}/latest")


def _find_dd_asset(release: dict) -> dict:
    tag = _dd_platform_tag()
    for asset in release["assets"]:
        name: str = asset["name"]
        # Match e.g. "DepotDownloader-windows-x64.zip"
        if f"DepotDownloader-{tag}" in name and name.endswith(".zip"):
            return asset
    available = [a["name"] for a in release["assets"]]
    raise RuntimeError(
        f"No DepotDownloader asset for {tag} in {release['tag_name']}.\n"
        f"Available: {available}"
    )


# ── install DepotDownloader ────────────────────────────────────────

def _download_and_extract_dd(asset: dict, tag: str) -> None:
    url = asset["browser_download_url"]
    size_mb = asset["size"] / (1024 * 1024)
    print(f"Downloading {asset['name']} ({size_mb:.1f} MB)...")

    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = resp.read()

    print(f"Extracting to {DD_DIR}...")
    if DD_DIR.exists():
        shutil.rmtree(DD_DIR)
    DD_DIR.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        zf.extractall(DD_DIR)

    DD_VERSION_FILE.write_text(tag, encoding="utf-8")

    exe = DD_DIR / _dd_exe_name()
    if not exe.exists():
        raise RuntimeError(f"DepotDownloader exe not found at {exe} after extraction")

    print(f"✓ DepotDownloader {tag} installed at {DD_DIR}")


def get_dd_exe() -> Path:
    """Return path to DepotDownloader executable, or raise."""
    exe = DD_DIR / _dd_exe_name()
    if not exe.exists():
        raise FileNotFoundError(
            f"DepotDownloader not found. Run: python datamine/fetch_data_win.py --setup-only"
        )
    return exe


def get_dd_version() -> str | None:
    if DD_VERSION_FILE.exists():
        return DD_VERSION_FILE.read_text(encoding="utf-8").strip()
    return None


def setup_depot_downloader() -> Path:
    """Download and install DepotDownloader. Returns exe path."""
    release = _find_dd_release()
    tag = release["tag_name"]

    installed = get_dd_version()
    if installed == tag:
        exe = DD_DIR / _dd_exe_name()
        if exe.exists():
            print(f"✓ DepotDownloader {tag} already installed")
            return exe

    asset = _find_dd_asset(release)
    _download_and_extract_dd(asset, tag)
    return DD_DIR / _dd_exe_name()


# ── fetch data.win ─────────────────────────────────────────────────

# ── provenance helpers ──────────────────────────────────────────────

def _sha256(path: Path) -> str:
    """Compute SHA256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _extract_game_version(data_win: Path) -> str | None:
    """Try to extract game version string from data.win via UTMT_CLI info.

    Falls back to scanning raw bytes if CLI unavailable.
    """
    # Method 1: try UTMT_CLI dump -s and grep for version pattern
    # Too slow (~20s). Instead, scan the binary for the known pattern.
    # Stoneshard stores version as e.g. "0.9.3.13" near "_versionString".
    try:
        # Quick binary scan: look for X.Y.Z.W pattern near known markers
        with open(data_win, "rb") as f:
            data = f.read()
        # Look for the version string that appears near "_versionString"
        # Pattern: digits.digits.digits.digits (no leading zeros in major)
        marker = b"_versionString"
        idx = data.find(marker)
        if idx != -1:
            # Search in a window before the marker
            window = data[max(0, idx - 200):idx].decode("latin-1")
            m = re.search(r"(\d+\.\d+\.\d+\.\d+)", window)
            if m:
                return m.group(1)
        # Fallback: search entire file for the pattern (first match near start)
        # Only scan first 50MB to avoid slow full scan
        text = data[:50 * 1024 * 1024].decode("latin-1")
        for m in re.finditer(r"(?<!\d)(\d+\.\d+\.\d+\.\d+)(?!\d)", text):
            v = m.group(1)
            # Filter out things that look like IP addresses or GUIDs
            parts = v.split(".")
            if int(parts[0]) < 10 and int(parts[1]) < 100:
                return v
    except Exception:
        pass
    return None


def write_provenance(
    *,
    manifest: str | None = None,
    username: str | None = None,
) -> dict:
    """Compute and write provenance.json for the downloaded data.win."""
    if not DATA_WIN.exists():
        return {}

    stat = DATA_WIN.stat()
    sha = _sha256(DATA_WIN)
    game_ver = _extract_game_version(DATA_WIN)

    prov = {
        "schema": 1,
        "data_win": {
            "sha256": sha,
            "size_bytes": stat.st_size,
            "game_version": game_ver,
        },
        "source": {
            "app_id": STONESHARD_APP_ID,
            "depot_id": STONESHARD_DEPOT_ID,
            "branch": BRANCH,
            "manifest": manifest,
        },
        "depot_downloader": {
            "version": get_dd_version(),
        },
        "fetched_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    PROVENANCE_FILE.write_text(
        json.dumps(prov, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\n✓ Provenance: {PROVENANCE_FILE}")
    print(f"  SHA256:       {sha[:16]}...")
    print(f"  Game version: {game_ver or 'unknown'}")
    if manifest:
        print(f"  Manifest:     {manifest}")

    # Auto-register manifest → game_version in local registry
    try:
        from versions import register_manifest
        register_manifest(
            manifest=manifest,
            game_version=game_ver,
            sha256=sha,
            branch=BRANCH,
            source="fetch",
        )
    except Exception:
        pass  # Non-critical — don't break fetch workflow

    return prov


def get_provenance() -> dict | None:
    """Read existing provenance.json, or None."""
    if PROVENANCE_FILE.exists():
        return json.loads(PROVENANCE_FILE.read_text(encoding="utf-8"))
    return None


# ── fetch data.win ─────────────────────────────────────────────────

def fetch_data_win(
    username: str | None = None,
    manifest: str | None = None,
) -> Path:
    """Download data.win from Steam modbranch. Returns output path.

    Args:
        username: Steam username for authentication.
        manifest: Specific manifest ID to download (historical version).
                  If None, downloads the latest for the branch.
    """
    exe = get_dd_exe()
    INPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Create filelist (DepotDownloader requires a file)
    filelist = DD_DIR / "_filelist.txt"
    filelist.write_text("data.win\n", encoding="utf-8")

    cmd = [
        str(exe),
        "-app", str(STONESHARD_APP_ID),
        "-depot", str(STONESHARD_DEPOT_ID),
        "-branch", BRANCH,
        "-filelist", str(filelist),
        "-dir", str(INPUT_DIR),
        "-remember-password",
    ]

    if manifest:
        cmd.extend(["-manifest", manifest])

    if username:
        cmd.extend(["-username", username])

    print(f"\n{'='*60}")
    print(f"  Stoneshard data.win downloader")
    print(f"  App: {STONESHARD_APP_ID}  Depot: {STONESHARD_DEPOT_ID}  Branch: {BRANCH}")
    if manifest:
        print(f"  Manifest: {manifest} (pinned)")
    else:
        print(f"  Manifest: latest")
    print(f"  Output: {DATA_WIN}")
    print(f"{'='*60}")

    if not username:
        print("\n⚠ No -u <username> specified.")
        print("  DepotDownloader will prompt for credentials interactively.\n")

    print(f"Running: {' '.join(cmd)}\n")

    # Run interactively (stdin/stdout passed through for login prompts)
    result = subprocess.run(cmd, cwd=str(DD_DIR))

    if result.returncode != 0:
        print(f"\n✗ DepotDownloader exited with code {result.returncode}")
        sys.exit(result.returncode)

    if DATA_WIN.exists():
        size_mb = DATA_WIN.stat().st_size / (1024 * 1024)
        print(f"\n✓ Downloaded: {DATA_WIN} ({size_mb:.1f} MB)")
    else:
        # DepotDownloader might put it in a subdirectory
        found = list(INPUT_DIR.rglob("data.win"))
        if found:
            actual = found[0]
            if actual != DATA_WIN:
                shutil.move(str(actual), str(DATA_WIN))
                try:
                    actual.parent.rmdir()
                except OSError:
                    pass
            size_mb = DATA_WIN.stat().st_size / (1024 * 1024)
            print(f"\n✓ Downloaded: {DATA_WIN} ({size_mb:.1f} MB)")
        else:
            print(f"\n✗ data.win not found in {INPUT_DIR}")
            print("  Check DepotDownloader output above for errors.")
            sys.exit(1)

    # Record provenance
    write_provenance(manifest=manifest, username=username)

    return DATA_WIN


# ── CLI ─────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]

    if "--check" in args:
        dd_ver = get_dd_version()
        if dd_ver:
            exe = DD_DIR / _dd_exe_name()
            print(f"DepotDownloader: {dd_ver} ({'✓' if exe.exists() else '✗ MISSING'})")
        else:
            print("DepotDownloader: not installed")

        prov = get_provenance()
        if prov:
            dw = prov.get("data_win", {})
            src = prov.get("source", {})
            size_mb = dw.get("size_bytes", 0) / (1024 * 1024)
            print(f"data.win: ✓ {size_mb:.1f} MB")
            print(f"  Game version: {dw.get('game_version', 'unknown')}")
            print(f"  SHA256:       {dw.get('sha256', '?')[:16]}...")
            print(f"  Branch:       {src.get('branch', '?')}")
            print(f"  Manifest:     {src.get('manifest') or 'latest'}")
            print(f"  Fetched:      {prov.get('fetched_at', '?')}")
        elif DATA_WIN.exists():
            size_mb = DATA_WIN.stat().st_size / (1024 * 1024)
            mtime = datetime.datetime.fromtimestamp(DATA_WIN.stat().st_mtime)
            print(f"data.win: ✓ {size_mb:.1f} MB (modified {mtime:%Y-%m-%d %H:%M})")
            print(f"  ⚠ No provenance.json — run fetch again to generate")
        else:
            print(f"data.win: not found at {DATA_WIN}")
        return

    if "--setup-only" in args:
        setup_depot_downloader()
        return

    # Parse named arguments
    username = None
    manifest = None
    for i, arg in enumerate(args):
        if arg in ("-u", "--username") and i + 1 < len(args):
            username = args[i + 1]
        elif arg in ("-m", "--manifest") and i + 1 < len(args):
            manifest = args[i + 1]

    # Ensure DepotDownloader is installed
    setup_depot_downloader()

    # Fetch data.win
    fetch_data_win(username=username, manifest=manifest)


if __name__ == "__main__":
    main()
