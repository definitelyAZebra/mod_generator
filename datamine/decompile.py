# -*- coding: utf-8 -*-
"""
从 data.win 反编译 GML 代码并导出结构元数据。

用法:
    python datamine/decompile.py                             # 使用 datamine/input/data.win
    python datamine/decompile.py <path_to_data.win>          # 指定 data.win
    python datamine/decompile.py --gml-only
    python datamine/decompile.py --meta-only

前置条件:
    python datamine/setup_cli.py               (下载 UTMT_CLI)
    python datamine/fetch_data_win.py -u ...   (可选，下载干净 data.win)

数据源: Stoneshard data.win
输出:
    datamine/output/CodeEntries/       反编译 GML 代码
    datamine/output/meta/              结构元数据 JSON
    datamine/output/provenance.json    版本溯源信息
"""

from __future__ import annotations

import datetime
import io
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

# ── paths ──────────────────────────────────────────────────────────
DATAMINE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = DATAMINE_DIR / "output"
GML_DIR = OUTPUT_DIR / "CodeEntries"
META_DIR = OUTPUT_DIR / "meta"
DUMP_GML_CSX = DATAMINE_DIR / "dump_gml.csx"
EXPORT_META_CSX = DATAMINE_DIR / "export_meta.csx"
DEFAULT_DATA_WIN = DATAMINE_DIR / "input" / "data.win"
OUTPUT_PROVENANCE = OUTPUT_DIR / "provenance.json"

# Ensure stdout handles Unicode
if sys.stdout.encoding and sys.stdout.encoding.lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def _get_cli() -> Path:
    """Import and return CLI exe path."""
    # Ensure datamine/ is importable regardless of cwd
    sys.path.insert(0, str(DATAMINE_DIR))
    from setup_cli import get_cli_exe
    return get_cli_exe()


def _run(args: list[str], label: str) -> None:
    """Run a subprocess with live output, raising on failure."""
    print(f"\n{'─' * 60}")
    print(f"  {label}")
    print(f"  CMD: {' '.join(str(a) for a in args)}")
    print(f"{'─' * 60}")

    t0 = time.perf_counter()
    result = subprocess.run(
        args,
        cwd=str(DATAMINE_DIR),
        capture_output=False,
        text=True,
    )
    elapsed = time.perf_counter() - t0

    if result.returncode != 0:
        print(f"\n✗ {label} FAILED (exit code {result.returncode}, {elapsed:.1f}s)")
        sys.exit(result.returncode)
    else:
        print(f"\n✓ {label} done ({elapsed:.1f}s)")


def dump_gml(cli: Path, data_win: Path) -> None:
    """Decompile all code entries to datamine/output/CodeEntries/.

    Uses a custom C# script (dump_gml.csx) based on UndertaleModTool's
    built-in ExportAllCode.csx / ExportAllCodeSync.csx, with additions:
      - Filters parent vs child entries (ParentEntry check) to avoid false failures
      - Uses Parallel.ForEach for speed
      - Falls back to disassembly on decompile failure
      - Truncates filenames for Windows MAX_PATH
      - Writes manifest + error log

    Output structure:
      CodeEntries/           — main decompiled .gml files
      CodeEntries/Failed/    — main entries that failed (with exception + disassembly)
      CodeEntries/Duplicates/        — child/duplicate entries
      CodeEntries/Duplicates/Failed/ — child entries that failed
    """
    if not DUMP_GML_CSX.exists():
        print(f"✗ {DUMP_GML_CSX} not found")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    _run(
        [str(cli), "load", str(data_win), "-s", str(DUMP_GML_CSX)],
        f"Dumping all GML code → {GML_DIR}",
    )

    # Count exported files
    if GML_DIR.exists():
        main_count = sum(1 for _ in GML_DIR.glob("*.gml"))
        failed_dir = GML_DIR / "Failed"
        failed_count = sum(1 for _ in failed_dir.glob("*.gml")) if failed_dir.exists() else 0
        dup_dir = GML_DIR / "Duplicates"
        dup_count = sum(1 for _ in dup_dir.glob("*.gml")) if dup_dir.exists() else 0
        dup_failed_dir = dup_dir / "Failed" if dup_dir.exists() else None
        dup_failed_count = sum(1 for _ in dup_failed_dir.glob("*.gml")) if dup_failed_dir and dup_failed_dir.exists() else 0

        print(f"  {main_count} main .gml files exported")
        if failed_count:
            print(f"  {failed_count} main entries failed (see Failed/)")
        if dup_count:
            print(f"  {dup_count} duplicate .gml files exported")
        if dup_failed_count:
            print(f"  {dup_failed_count} duplicate entries failed")

        errors_log = GML_DIR / "_errors.log"
        if errors_log.exists():
            print(f"  Error log: {errors_log}")
    else:
        print(f"  ⚠ CodeEntries/ directory not created — check CLI output above")


def export_meta(cli: Path, data_win: Path) -> None:
    """Run export_meta.csx to export structural metadata."""
    if not EXPORT_META_CSX.exists():
        print(f"✗ {EXPORT_META_CSX} not found")
        sys.exit(1)

    _run(
        [str(cli), "load", str(data_win), "-s", str(EXPORT_META_CSX)],
        f"Exporting meta → {META_DIR}",
    )

    # List exported files
    if META_DIR.exists():
        for f in sorted(META_DIR.glob("*.json")):
            size_kb = f.stat().st_size / 1024
            print(f"  {f.name} ({size_kb:.0f} KB)")


def _write_provenance(cli: Path, data_win: Path, elapsed: float) -> None:
    """Write output/provenance.json linking CLI version + input provenance."""
    # Read CLI version
    sys.path.insert(0, str(DATAMINE_DIR))
    from setup_cli import get_installed_version
    cli_ver = get_installed_version()

    # Read input provenance if available
    input_prov = None
    input_prov_path = DATAMINE_DIR / "input" / "provenance.json"
    if input_prov_path.exists():
        input_prov = json.loads(input_prov_path.read_text(encoding="utf-8"))

    # Count outputs
    gml_count = sum(1 for _ in GML_DIR.glob("*.gml")) if GML_DIR.exists() else 0
    failed_dir = GML_DIR / "Failed"
    gml_failed = sum(1 for _ in failed_dir.glob("*.gml")) if failed_dir.exists() else 0
    dup_dir = GML_DIR / "Duplicates"
    gml_duplicates = sum(1 for _ in dup_dir.glob("*.gml")) if dup_dir.exists() else 0
    meta_files = sorted(f.name for f in META_DIR.glob("*.json")) if META_DIR.exists() else []

    prov = {
        "schema": 2,
        "utmt_cli": {
            "version": cli_ver,
            "exe": str(cli),
        },
        "data_win": {
            "path": str(data_win),
            # Copy key fields from input provenance
            "sha256": (input_prov or {}).get("data_win", {}).get("sha256"),
            "game_version": (input_prov or {}).get("data_win", {}).get("game_version"),
        },
        "output": {
            "gml_files": gml_count,
            "gml_failed": gml_failed,
            "gml_duplicates": gml_duplicates,
            "meta_files": meta_files,
        },
        "decompiled_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "elapsed_seconds": round(elapsed, 1),
    }

    # If input provenance has source info, include it
    if input_prov and "source" in input_prov:
        prov["source"] = input_prov["source"]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PROVENANCE.write_text(
        json.dumps(prov, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\n✓ Provenance: {OUTPUT_PROVENANCE}")
    if cli_ver:
        print(f"  UTMT_CLI:     {cli_ver}")
    gv = prov["data_win"].get("game_version")
    if gv:
        print(f"  Game version: {gv}")
    print(f"  GML files:    {gml_count}")
    if gml_failed:
        print(f"  GML failed:   {gml_failed}")
    if gml_duplicates:
        print(f"  Duplicates:   {gml_duplicates}")
    print(f"  Meta files:   {len(meta_files)}")


def main():
    args = sys.argv[1:]

    # Parse flags
    gml_only = "--gml-only" in args
    meta_only = "--meta-only" in args
    positional = [a for a in args if not a.startswith("--")]

    # Resolve data.win path: explicit arg or default
    if positional:
        data_win = Path(positional[0]).resolve()
    else:
        data_win = DEFAULT_DATA_WIN

    if not data_win.exists():
        if not positional:
            print(f"✗ Default data.win not found: {data_win}")
            print(f"  Run: python datamine/fetch_data_win.py -u <steam_user>")
            print(f"  Or:  python datamine/decompile.py <path_to_data.win>")
        else:
            print(f"✗ data.win not found: {data_win}")
        sys.exit(1)

    cli = _get_cli()
    print(f"UTMT_CLI: {cli}")
    print(f"data.win: {data_win}")
    print(f"Output:   {OUTPUT_DIR}")

    t_total = time.perf_counter()

    if not meta_only:
        dump_gml(cli, data_win)

    if not gml_only:
        export_meta(cli, data_win)

    elapsed = time.perf_counter() - t_total

    # Write provenance
    _write_provenance(cli, data_win, elapsed)

    print(f"\n{'=' * 60}")
    print(f"  All done! ({elapsed:.1f}s total)")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
