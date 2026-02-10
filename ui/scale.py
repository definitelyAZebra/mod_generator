# -*- coding: utf-8 -*-
"""Spacing & Sizing Scale — Tailwind-style design tokens as IntEnum.

Replaces the runtime-asserted sz() with compile-time-safe enum constants.
Use dp() to convert tokens to DPI-aware pixel values.

Quick reference::

    from ui.scale import Sp, Cn, dp

    # DPI-aware pixel value
    width = dp(Sp.S40)            # 160 * dpi_scale()

    # Direct in layout functions
    ly.gap_y(Sp.S4)               # 16px spacing (DPI-aware)
    ly.hstack(gap=Sp.S2)          # 8px gap

    # Container scale for large dimensions
    popup_width = dp(Cn.CMD)      # 448 * dpi_scale()

    # IntEnum IS int, so arithmetic works:
    half = Sp.S4 // 2             # 8
    total = Sp.S4 + Sp.S2         # 24

Escape hatch for arbitrary pixel values (no type safety)::

    from ui.state import dpi_scale
    raw_px_value * dpi_scale()

Migration from sz()::

    sz(4)        → dp(Sp.S4)
    sz(40)       → dp(Sp.S40)
    sz_free(120) → 480 * dpi_scale()  or dp(Cn.CSM) if close enough
    gap_y(4)     → gap_y(Sp.S4)

Source: Tailwind CSS v3/v4 spacing scale + v4 container scale.
"""

from __future__ import annotations

from enum import IntEnum
from typing import TypeAlias

from ui.state import dpi_scale


class Sp(IntEnum):
    """Spacing scale — Tailwind spacing tokens as raw pixel values.

    Naming: ``S{n}`` maps to Tailwind's ``spacing-{n}`` token.
    Value: ``n × 4`` pixels (at 1× DPI).

    Example::

        Sp.S4  → 16   (Tailwind "4"   = 16px)
        Sp.S9  → 36   (Tailwind "9"   = 36px)
        Sp.S40 → 160  (Tailwind "40"  = 160px)
    """

    S0 = 0
    PX = 1        # 1px  (Tailwind "px")
    S0_5 = 2      # 0.5 × 4 = 2px
    S1 = 4
    S1_5 = 6
    S2 = 8
    S2_5 = 10
    S3 = 12
    S3_5 = 14
    S4 = 16
    S5 = 20
    S6 = 24
    S7 = 28
    S8 = 32
    S9 = 36
    S10 = 40
    S11 = 44
    S12 = 48
    S14 = 56
    S16 = 64
    S20 = 80
    S24 = 96
    S28 = 112
    S32 = 128
    S36 = 144
    S40 = 160
    S44 = 176
    S48 = 192
    S52 = 208
    S56 = 224
    S60 = 240
    S64 = 256
    S72 = 288
    S80 = 320
    S96 = 384


class Cn(IntEnum):
    """Container scale — named breakpoints for large layout dimensions (px).

    Based on Tailwind CSS v4 ``--container-*`` theme variables.
    Use for popup widths, panel sizes, breakpoint comparisons.

    Example::

        Cn.CMD  → 448   (Tailwind "md" container = 28rem = 448px)
        Cn.CLG  → 512   (Tailwind "lg" container = 32rem = 512px)
    """

    C3XS = 256    # 16rem
    C2XS = 288    # 18rem
    CXS = 320     # 20rem
    CSM = 384     # 24rem
    CMD = 448     # 28rem
    CLG = 512     # 32rem
    CXL = 576     # 36rem
    C2XL = 672    # 42rem
    C3XL = 768    # 48rem
    C4XL = 896    # 56rem
    C5XL = 1024   # 64rem
    C6XL = 1152   # 72rem
    C7XL = 1280   # 80rem


# ---------------------------------------------------------------------------
# Type aliases — tighten during migration, loosen after
# ---------------------------------------------------------------------------

# Phase 1 (strict): Pylance flags all bare-number callsites as type errors.
SpacingArg: TypeAlias = Sp
"""For gaps, padding, margin — small values from the spacing scale."""

SizingArg: TypeAlias = Sp | Cn
"""For widths, heights, dimensions — spacing scale OR container scale."""

# Phase 2 (post-migration): uncomment to allow raw int as escape hatch.
# SpacingArg: TypeAlias = Sp | int
# SizingArg: TypeAlias = Sp | Cn | int


def dp(px: SizingArg) -> float:
    """Convert a scale token to DPI-aware pixels.

    Args:
        px: ``Sp`` or ``Cn`` enum member (raw pixel count).

    Returns:
        DPI-scaled pixel value.

    Examples::

        dp(Sp.S4)   →  16 * dpi_scale()  =  16.0 at 1×
        dp(Sp.S40)  → 160 * dpi_scale()  = 160.0 at 1×
        dp(Cn.CMD)  → 448 * dpi_scale()  = 448.0 at 1×
    """
    return int(px) * dpi_scale()
