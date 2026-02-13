# -*- coding: utf-8 -*-
"""
下载 UndertaleModTool CLI 到 datamine/vendor/UTMT_CLI/。

用法:
    python datamine/setup_cli.py              # 下载 latest stable
    python datamine/setup_cli.py 0.8.4.1      # 下载指定版本
    python datamine/setup_cli.py --check      # 仅检查是否已安装

数据源: GitHub Releases API
输出:   datamine/vendor/UTMT_CLI/
"""

from __future__ import annotations

import io
import json
import platform
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

# ── paths ──────────────────────────────────────────────────────────
DATAMINE_DIR = Path(__file__).resolve().parent
VENDOR_DIR = DATAMINE_DIR / "vendor"
CLI_DIR = VENDOR_DIR / "UTMT_CLI"
VERSION_FILE = CLI_DIR / ".version"

REPO = "UnderminersTeam/UndertaleModTool"
API_BASE = f"https://api.github.com/repos/{REPO}/releases"

# ── platform detection ─────────────────────────────────────────────

def _asset_os_tag() -> str:
    """Map current OS to the GitHub release asset tag."""
    s = platform.system()
    if s == "Windows":
        return "Windows"
    elif s == "Darwin":
        return "macOS"
    elif s == "Linux":
        return "Ubuntu"
    else:
        raise RuntimeError(f"Unsupported platform: {s}")


def _cli_exe_name() -> str:
    if platform.system() == "Windows":
        return "UndertaleModCli.exe"
    return "UndertaleModCli"


# ── GitHub API ─────────────────────────────────────────────────────

def _api_get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def _find_release(version: str | None) -> dict:
    """Fetch release info. None = latest stable."""
    if version:
        return _api_get(f"{API_BASE}/tags/{version}")
    return _api_get(f"{API_BASE}/latest")


def _find_cli_asset(release: dict) -> dict:
    """Find the UTMT_CLI asset for the current OS."""
    os_tag = _asset_os_tag()
    prefix = f"UTMT_CLI_"
    for asset in release["assets"]:
        name: str = asset["name"]
        if name.startswith(prefix) and os_tag in name and name.endswith(".zip"):
            return asset
    available = [a["name"] for a in release["assets"]]
    raise RuntimeError(
        f"No UTMT_CLI asset for {os_tag} in release {release['tag_name']}.\n"
        f"Available: {available}"
    )


# ── download & install ──────────────────────────────────────────────

def _download_and_extract(asset: dict, tag: str) -> None:
    url = asset["browser_download_url"]
    size_mb = asset["size"] / (1024 * 1024)
    print(f"Downloading {asset['name']} ({size_mb:.1f} MB)...")

    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = resp.read()

    print(f"Extracting to {CLI_DIR}...")
    if CLI_DIR.exists():
        shutil.rmtree(CLI_DIR)
    CLI_DIR.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        zf.extractall(CLI_DIR)

    # Write version marker
    VERSION_FILE.write_text(tag, encoding="utf-8")

    # Verify executable exists
    exe = CLI_DIR / _cli_exe_name()
    if not exe.exists():
        # Some zips have a subfolder — check and flatten
        subdirs = [d for d in CLI_DIR.iterdir() if d.is_dir()]
        for sub in subdirs:
            candidate = sub / _cli_exe_name()
            if candidate.exists():
                # Move contents up
                for item in sub.iterdir():
                    dest = CLI_DIR / item.name
                    if dest.exists() and dest != item:
                        if dest.is_dir():
                            shutil.rmtree(dest)
                        else:
                            dest.unlink()
                    shutil.move(str(item), str(dest))
                sub.rmdir()
                break

    exe = CLI_DIR / _cli_exe_name()
    if not exe.exists():
        raise RuntimeError(f"CLI executable not found at {exe} after extraction")

    print(f"✓ UTMT_CLI {tag} installed at {CLI_DIR}")


# ── public API ──────────────────────────────────────────────────────

def get_cli_exe() -> Path:
    """Return path to CLI executable, or raise if not installed."""
    exe = CLI_DIR / _cli_exe_name()
    if not exe.exists():
        raise FileNotFoundError(
            f"UTMT_CLI not found at {exe}.\n"
            f"Run: python datamine/setup_cli.py"
        )
    return exe


def get_installed_version() -> str | None:
    """Return installed version tag, or None."""
    if VERSION_FILE.exists():
        return VERSION_FILE.read_text(encoding="utf-8").strip()
    return None


def setup(version: str | None = None) -> Path:
    """Download and install UTMT_CLI. Returns path to executable."""
    release = _find_release(version)
    tag = release["tag_name"]

    installed = get_installed_version()
    if installed == tag:
        exe = CLI_DIR / _cli_exe_name()
        if exe.exists():
            print(f"✓ UTMT_CLI {tag} already installed at {CLI_DIR}")
            return exe

    asset = _find_cli_asset(release)
    _download_and_extract(asset, tag)
    return CLI_DIR / _cli_exe_name()


# ── CLI ─────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]

    if "--check" in args:
        v = get_installed_version()
        if v:
            exe = CLI_DIR / _cli_exe_name()
            ok = exe.exists()
            print(f"Version: {v}")
            print(f"Path:    {CLI_DIR}")
            print(f"Exe:     {'✓ found' if ok else '✗ MISSING'}")
        else:
            print("UTMT_CLI not installed.")
            print(f"Run: python datamine/setup_cli.py")
        return

    version = args[0] if args else None
    setup(version)


if __name__ == "__main__":
    main()
