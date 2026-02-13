# -*- coding: utf-8 -*-
"""
Stoneshard 版本追踪：manifest 注册表 + changelog 缓存。

功能:
    - 从 Steam News API 抓取 patch notes (公开, 无需登录)
    - 用 DepotDownloader 探测当前 branch 的 manifest ID (需登录)
    - 维护本地注册表: manifest ↔ game_version ↔ date
    - 每次 fetch_data_win 时自动记录

用法:
    python datamine/versions.py changelog              # 显示最近 changelog
    python datamine/versions.py changelog --fetch      # 强制刷新
    python datamine/versions.py registry               # 显示已知版本
    python datamine/versions.py probe -u <steam_user>  # 探测当前 manifest

数据源: Steam News API (ISteamNews/GetNewsForApp)
缓存:   datamine/input/changelog_cache.json
注册表: datamine/input/manifest_registry.json
"""

from __future__ import annotations

import datetime
import json
import re
import sys
import subprocess
import urllib.request
from pathlib import Path

# ── paths ──────────────────────────────────────────────────────────
DATAMINE_DIR = Path(__file__).resolve().parent
INPUT_DIR = DATAMINE_DIR / "input"
CHANGELOG_CACHE = INPUT_DIR / "changelog_cache.json"
MANIFEST_REGISTRY = INPUT_DIR / "manifest_registry.json"

# ── Steam constants ────────────────────────────────────────────────
STONESHARD_APP_ID = 625960
STONESHARD_DEPOT_ID = 625961
NEWS_API = (
    f"https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/"
    f"?appid={STONESHARD_APP_ID}&count=50"
    f"&feeds=steam_community_announcements"
)

# ── changelog ──────────────────────────────────────────────────────

def _strip_bbcode(text: str) -> str:
    """Minimal BBCode → plain text."""
    # Remove [img ...][/img]
    text = re.sub(r'\[img[^\]]*\]\[/img\]', '', text)
    # Remove [url=...] and [/url]
    text = re.sub(r'\[url=[^\]]*\]', '', text)
    text = text.replace('[/url]', '')
    # Convert headers
    text = re.sub(r'\[h[123]\]', '\n## ', text)
    text = re.sub(r'\[/h[123]\]', '\n', text)
    # Convert list items
    text = re.sub(r'\[\*\]', '  • ', text)
    # Remove remaining tags
    text = re.sub(r'\[/?[a-zA-Z][^\]]*\]', '', text)
    # Collapse whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _extract_version_from_title(title: str) -> str | None:
    """Extract version like '0.9.3.13' from a news title."""
    # Patterns: "Hotfixes 0.9.3.11-0.9.3.13", "0.9.3.10 Content Patch"
    versions = re.findall(r'(\d+\.\d+\.\d+(?:\.\d+)?)', title)
    if versions:
        return versions[-1]  # Last version is the latest in range
    return None


def fetch_changelog(force: bool = False) -> list[dict]:
    """Fetch patch notes from Steam News API. Caches locally.

    Returns list of {title, version, date, date_str, content, gid, is_patchnotes}.
    """
    # Check cache
    if not force and CHANGELOG_CACHE.exists():
        cache = json.loads(CHANGELOG_CACHE.read_text(encoding="utf-8"))
        age_hours = (
            datetime.datetime.now(datetime.timezone.utc)
            - datetime.datetime.fromisoformat(cache["fetched_at"])
        ).total_seconds() / 3600
        if age_hours < 24:
            return cache["entries"]

    print("Fetching changelog from Steam News API...")
    req = urllib.request.Request(NEWS_API)
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())

    items = data.get("appnews", {}).get("newsitems", [])
    entries = []
    for item in items:
        title = item.get("title", "")
        version = _extract_version_from_title(title)
        tags = item.get("tags", [])
        is_patch = "patchnotes" in tags
        date = datetime.datetime.fromtimestamp(
            item["date"], tz=datetime.timezone.utc
        )
        entries.append({
            "title": title,
            "version": version,
            "date": item["date"],
            "date_str": date.strftime("%Y-%m-%d"),
            "content": _strip_bbcode(item.get("contents", "")),
            "gid": item.get("gid"),
            "is_patchnotes": is_patch,
            "url": item.get("url", ""),
        })

    # Save cache
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    cache = {
        "fetched_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "entries": entries,
    }
    CHANGELOG_CACHE.write_text(
        json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"✓ Cached {len(entries)} news entries to {CHANGELOG_CACHE}")
    return entries


def get_patchnotes(force: bool = False) -> list[dict]:
    """Return only patchnotes entries (has version in title or tagged)."""
    entries = fetch_changelog(force=force)
    return [
        e for e in entries
        if e["is_patchnotes"] or e["version"]
    ]


# ── manifest registry ──────────────────────────────────────────────

def _load_registry() -> dict:
    """Load manifest registry from disk."""
    if MANIFEST_REGISTRY.exists():
        return json.loads(MANIFEST_REGISTRY.read_text(encoding="utf-8"))
    return {"schema": 1, "entries": []}


def _save_registry(reg: dict) -> None:
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_REGISTRY.write_text(
        json.dumps(reg, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def register_manifest(
    *,
    manifest: str | None,
    game_version: str | None,
    sha256: str | None = None,
    branch: str = "modbranch",
    source: str = "fetch",
) -> None:
    """Record a manifest → game_version mapping in the local registry.

    Called automatically after each fetch_data_win.
    """
    if not manifest and not game_version:
        return

    reg = _load_registry()
    entries: list[dict] = reg.get("entries", [])

    # Check for duplicate
    for e in entries:
        if manifest and e.get("manifest") == manifest:
            # Update existing
            if game_version and not e.get("game_version"):
                e["game_version"] = game_version
            if sha256 and not e.get("sha256"):
                e["sha256"] = sha256
            e["last_seen"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            _save_registry(reg)
            return

    # New entry
    entry = {
        "manifest": manifest,
        "game_version": game_version,
        "sha256": sha256,
        "branch": branch,
        "source": source,
        "first_seen": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "last_seen": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    entries.append(entry)

    # Sort by first_seen descending
    entries.sort(key=lambda e: e.get("first_seen", ""), reverse=True)
    reg["entries"] = entries
    _save_registry(reg)

    v_label = game_version or "unknown"
    m_label = manifest or "unknown"
    print(f"✓ Registered: {v_label} (manifest {m_label})")


def get_registry() -> list[dict]:
    """Return all registered manifests."""
    return _load_registry().get("entries", [])


# ── manifest probing ───────────────────────────────────────────────

def probe_current_manifest(
    username: str | None = None,
    branch: str = "modbranch",
) -> str | None:
    """Use DepotDownloader -manifest-only to discover current manifest ID.

    Requires Steam authentication (interactive login on first use).
    Returns manifest ID string or None on failure.
    """
    sys.path.insert(0, str(DATAMINE_DIR))
    from fetch_data_win import get_dd_exe, DD_DIR

    exe = get_dd_exe()
    probe_dir = INPUT_DIR / "_manifest_probe"
    probe_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        str(exe),
        "-app", str(STONESHARD_APP_ID),
        "-depot", str(STONESHARD_DEPOT_ID),
        "-branch", branch,
        "-manifest-only",
        "-dir", str(probe_dir),
        "-remember-password",
    ]
    if username:
        cmd.extend(["-username", username])

    print(f"Probing current manifest for branch '{branch}'...")
    result = subprocess.run(
        cmd,
        cwd=str(DD_DIR),
        capture_output=True,
        text=True,
    )

    # Parse output for manifest ID
    # DepotDownloader outputs lines like:
    #   "Got depot key for depot 625961 ..."
    #   "Processing depot 625961 - Manifest 1234567890123456789"
    output = result.stdout + result.stderr
    manifest = None
    for line in output.splitlines():
        m = re.search(r'[Mm]anifest\s+(\d{10,})', line)
        if m:
            manifest = m.group(1)
            break

    # Also check for manifest file on disk
    if not manifest:
        for f in probe_dir.rglob("*.txt"):
            content = f.read_text(encoding="utf-8", errors="replace")
            m = re.search(r'manifest\s*[:=]?\s*(\d{10,})', content, re.IGNORECASE)
            if m:
                manifest = m.group(1)
                break

    # Cleanup
    import shutil
    if probe_dir.exists():
        shutil.rmtree(probe_dir, ignore_errors=True)

    if manifest:
        print(f"✓ Current manifest: {manifest}")
        register_manifest(manifest=manifest, game_version=None, branch=branch, source="probe")
    else:
        if result.returncode != 0:
            print(f"✗ DepotDownloader exited with code {result.returncode}")
            # Show relevant error lines
            for line in output.splitlines():
                if "Error" in line or "Failed" in line or "Unable" in line:
                    print(f"  {line.strip()}")
        else:
            print("✗ Could not parse manifest ID from output")

    return manifest


# ── display helpers ────────────────────────────────────────────────

def print_changelog(max_entries: int = 10, patchnotes_only: bool = True) -> None:
    """Pretty-print recent changelog entries."""
    if patchnotes_only:
        entries = get_patchnotes()
        label = "patch notes"
    else:
        entries = fetch_changelog()
        label = "news entries"

    if not entries:
        print("No entries found. Try: python datamine/versions.py changelog --fetch")
        return

    shown = entries[:max_entries]
    print(f"\n{'='*60}")
    print(f"  Stoneshard {label} ({len(entries)} total, showing {len(shown)})")
    print(f"{'='*60}\n")

    for e in shown:
        version_tag = f" [v{e['version']}]" if e['version'] else ""
        print(f"  {e['date_str']}  {e['title']}{version_tag}")

    print(f"\n  Use --all to show all entries, or --detail N to show full text")
    print(f"  Source: Steam News API (app {STONESHARD_APP_ID})")


def print_changelog_detail(index: int = 0) -> None:
    """Print full text of a specific changelog entry."""
    entries = get_patchnotes()
    if not entries:
        print("No entries cached. Run: python datamine/versions.py changelog --fetch")
        return
    if index >= len(entries):
        print(f"Only {len(entries)} entries available (0-indexed)")
        return

    e = entries[index]
    print(f"\n{'='*60}")
    print(f"  {e['title']}")
    print(f"  {e['date_str']}  {'v' + e['version'] if e['version'] else ''}")
    print(f"{'='*60}\n")
    # Truncate very long content
    content = e['content']
    if len(content) > 5000:
        content = content[:5000] + f"\n\n  ... [{len(e['content'])-5000} chars truncated]"
    print(content)


def print_registry() -> None:
    """Pretty-print the manifest registry."""
    entries = get_registry()
    if not entries:
        print("No manifests registered yet.")
        print("Manifests are recorded automatically when you fetch data.win.")
        return

    print(f"\n{'='*60}")
    print(f"  Manifest Registry ({len(entries)} entries)")
    print(f"{'='*60}\n")

    print(f"  {'Version':<12} {'Manifest':<22} {'Branch':<12} {'First seen':<12} {'Source'}")
    print(f"  {'─'*12} {'─'*22} {'─'*12} {'─'*12} {'─'*8}")

    for e in entries:
        ver = e.get('game_version') or '?'
        man = e.get('manifest') or '?'
        if len(man) > 20:
            man = man[:17] + '...'
        branch = e.get('branch', '?')
        first = e.get('first_seen', '?')[:10]
        source = e.get('source', '?')
        print(f"  {ver:<12} {man:<22} {branch:<12} {first:<12} {source}")


# ── CLI ─────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]

    if not args:
        print("Usage:")
        print("  python datamine/versions.py changelog                # 显示 patch notes")
        print("  python datamine/versions.py changelog --fetch        # 强制刷新")
        print("  python datamine/versions.py changelog --all          # 全部条目")
        print("  python datamine/versions.py changelog --detail 0     # 第 N 条详情")
        print("  python datamine/versions.py registry                 # 已知版本")
        print("  python datamine/versions.py probe -u <steam_user>    # 探测 manifest")
        return

    cmd = args[0]

    if cmd == "changelog":
        force = "--fetch" in args
        show_all = "--all" in args

        # Check for --detail N
        detail_idx = None
        for i, a in enumerate(args):
            if a == "--detail" and i + 1 < len(args):
                detail_idx = int(args[i + 1])

        if detail_idx is not None:
            if force:
                fetch_changelog(force=True)
            print_changelog_detail(detail_idx)
        else:
            max_entries = 999 if show_all else 10
            if force:
                fetch_changelog(force=True)
            print_changelog(max_entries=max_entries)

    elif cmd == "registry":
        print_registry()

    elif cmd == "probe":
        username = None
        for i, a in enumerate(args):
            if a in ("-u", "--username") and i + 1 < len(args):
                username = args[i + 1]
        probe_current_manifest(username=username)

    else:
        print(f"Unknown command: {cmd}")
        print("Commands: changelog, registry, probe")


if __name__ == "__main__":
    main()
