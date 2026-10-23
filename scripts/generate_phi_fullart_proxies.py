#!/usr/bin/env python3
"""One-off PHI full-art Magic proxy generator (Pillow composites).

Copies Volcanic Island reference, then frames duals + Lotus Petal + City of Traitors
to match the reference layout. Optional HF backgrounds if Inference is allowed;
otherwise procedural landscapes.
"""
from __future__ import annotations

import math
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# --- paths ---
REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / "data" / "proxy" / "originals" / "PHI"
REF_SRC = Path(
    "/Users/PhilippSchmidt/.cursor/projects/Users-PhilippSchmidt-Documents-cursor/assets"
    "/Vulkaninsel_im_tropischen_Sonnenuntergang-30f7ca90-c6a6-44b8-b7a3-410e4c1703df.jpg"
)

W, H = 733, 1024
BORDER = 12
CORNER_R = 28
MARGIN_X = 28

# UI geometry (matched to Volcanic Island reference)
NAME_Y, NAME_H = 52, 48
TYPE_Y, TYPE_H = 772, 46
TEXT_Y, TEXT_H = 828, 108
FOOTER_Y = 948

FONT_NAME = "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"
FONT_TYPE = "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"
FONT_RULES = "/System/Library/Fonts/Supplemental/Georgia Italic.ttf"
FONT_FOOT = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONT_FOOT_B = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FONT_NEWYORK = "/System/Library/Fonts/NewYork.ttf"

# Mana / accent colors (MTG-ish)
COLORS = {
    "W": (232, 226, 180),
    "U": (14, 104, 171),
    "B": (72, 40, 90),
    "R": (211, 32, 42),
    "G": (0, 115, 62),
    "C": (180, 176, 170),
    "A": (160, 140, 100),  # artifact gold-gray
}


def load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    for p in (path, FONT_NEWYORK, FONT_NAME):
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def cover_resize(im: Image.Image, tw: int, th: int) -> Image.Image:
    iw, ih = im.size
    scale = max(tw / iw, th / ih)
    nw, nh = int(iw * scale + 0.5), int(ih * scale + 0.5)
    im = im.resize((nw, nh), Image.Resampling.LANCZOS)
    left = (nw - tw) // 2
    top = (nh - th) // 2
    return im.crop((left, top, left + tw, top + th))


def fbm(h: int, w: int, seed: int, octaves: int = 5) -> np.ndarray:
    """Multi-octave value noise in [0,1]."""
    rng = np.random.default_rng(seed)
    acc = np.zeros((h, w), dtype=np.float32)
    amp, norm = 1.0, 0.0
    for o in range(octaves):
        fh, fw = max(2, h // (2 ** (o + 2))), max(2, w // (2 ** (o + 2)))
        grid = rng.random((fh, fw), dtype=np.float32)
        layer = np.asarray(
            Image.fromarray((grid * 255).astype(np.uint8)).resize((w, h), Image.Resampling.BILINEAR),
            dtype=np.float32,
        ) / 255.0
        acc += layer * amp
        norm += amp
        amp *= 0.55
    return acc / max(norm, 1e-6)


def sky_gradient(h: int, w: int, top: tuple, bot: tuple, warp: np.ndarray | None = None) -> np.ndarray:
    t = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    if warp is not None:
        t = np.clip(t + (warp - 0.5) * 0.15, 0, 1)
    t3 = t[..., None] if t.ndim == 2 else t[:, None, None]
    top_a = np.array(top, dtype=np.float32)
    bot_a = np.array(bot, dtype=np.float32)
    c = (1 - t3) * top_a + t3 * bot_a
    if c.ndim == 2:
        c = np.broadcast_to(c[:, None, :], (h, w, 3)).copy()
    return c.astype(np.float32)


def soft_horizon(h: int, y0: float, width: float = 0.08) -> np.ndarray:
    y = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    return 1 / (1 + np.exp(-(y - y0) / width))


def mountains(h: int, w: int, base_y: float, peaks: list[tuple], color, n: np.ndarray):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    elev = np.full((h, w), base_y * h, dtype=np.float32)
    for cx, height, width in peaks:
        ridge = height * h + np.abs(xx - cx * w) * (height * h / (width * w + 1))
        ridge -= n * h * 0.04
        elev = np.minimum(elev, ridge)
    mask = (yy > elev).astype(np.float32)
    # soft edge
    edge = np.clip(1 - (yy - elev) / (h * 0.03 + 1), 0, 1)
    mask = np.maximum(mask, edge * (yy > elev - h * 0.03))
    shade = 0.45 + 0.55 * np.clip(1 - (yy - elev) / (h * 0.35 + 1), 0, 1)
    shade = shade * (0.85 + 0.3 * n)
    out = np.zeros((h, w, 3), dtype=np.float32)
    for i, ch in enumerate(color):
        out[:, :, i] = ch * shade
    return out, mask


def blend(a: np.ndarray, b: np.ndarray, m) -> np.ndarray:
    if not isinstance(m, np.ndarray):
        m = np.float32(m)
    elif m.ndim == 2:
        m = m[..., None]
    return a * (1 - m) + b * m


def paint_clouds(img: np.ndarray, n: np.ndarray, amount: float, tint: tuple) -> np.ndarray:
    c = np.clip((n - 0.55) / 0.35, 0, 1) * amount
    cloud = np.full_like(img, tint, dtype=np.float32)
    # only upper sky
    h = img.shape[0]
    sky_m = (1 - soft_horizon(h, 0.45, 0.1)) * c
    return blend(img, cloud, sky_m)


def procedural_bg(theme: str, seed: int = 0) -> Image.Image:
    """Themed full-bleed fantasy landscape (no text)."""
    rng = np.random.default_rng(seed + abs(hash(theme)) % 10_000)
    h, w = H, W
    n = fbm(h, w, seed=seed + 17)
    n2 = fbm(h, w, seed=seed + 91)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)

    def badlands():
        sky = sky_gradient(h, w, (255, 170, 90), (90, 40, 50), n)
        sky = paint_clouds(sky, n2, 0.55, (255, 220, 180))
        ground = sky_gradient(h, w, (140, 60, 35), (25, 10, 15), n2)
        ground = ground + (n[..., None] - 0.5) * 35 * np.array([1.2, 0.6, 0.3])
        img = blend(sky, ground, soft_horizon(h, 0.48, 0.04))
        mtn, m = mountains(
            h, w, 0.52, [(0.18, 0.32, 0.28), (0.5, 0.22, 0.4), (0.82, 0.36, 0.22)], (110, 45, 30), n
        )
        img = blend(img, mtn, m)
        # lava seams
        seams = (np.abs(n - 0.5) < 0.03) & (yy / h > 0.5)
        img = blend(img, np.full_like(img, (255, 90, 20)), seams.astype(np.float32) * 0.7)
        # swamp pools foreground
        pools = (n2 > 0.62) & (yy / h > 0.68)
        img = blend(img, np.full_like(img, (12, 28, 22)), pools.astype(np.float32) * 0.8)
        return img

    def bayou():
        sky = sky_gradient(h, w, (90, 120, 100), (25, 40, 35), n)
        sky = paint_clouds(sky, n2, 0.4, (160, 180, 150))
        water = sky_gradient(h, w, (25, 70, 50), (8, 20, 18), n2)
        water = water + (n[..., None] - 0.5) * 20 * np.array([0.2, 0.8, 0.5])
        img = blend(sky, water, soft_horizon(h, 0.42, 0.05))
        for x in rng.integers(30, w - 30, 16):
            tw = int(rng.integers(6, 16))
            top = int(rng.uniform(0.22, 0.42) * h)
            img[top:, x : x + tw] = blend(
                img[top:, x : x + tw],
                np.full_like(img[top:, x : x + tw], (35, 25, 18)),
                0.85,
            )
            cy, cx = top, x + tw // 2
            blob = ((yy - cy) ** 2 / (70 + 40 * n) ** 2 + (xx - cx) ** 2 / (55 + 30 * n2) ** 2) < 1
            img = blend(img, np.full_like(img, (22, 70, 38)), blob.astype(np.float32) * 0.65)
        # Spanish moss haze
        img = blend(img, np.full_like(img, (40, 55, 40)), (n > 0.7).astype(np.float32) * 0.15 * (1 - soft_horizon(h, 0.35)))
        return img

    def tropical():
        sky = sky_gradient(h, w, (140, 210, 255), (60, 140, 200), n)
        sky = paint_clouds(sky, n2, 0.5, (255, 255, 255))
        # sun glow
        sun = np.exp(-(((xx - w * 0.75) / (w * 0.2)) ** 2 + ((yy - h * 0.22) / (h * 0.15)) ** 2))
        sky = blend(sky, np.full_like(sky, (255, 240, 180)), sun * 0.45)
        sea = sky_gradient(h, w, (30, 190, 200), (10, 70, 110), n2)
        # reef mottling
        sea = sea + (n[..., None] - 0.5) * 40 * np.array([0.2, 0.9, 0.7])
        # shallow → deep
        depth = soft_horizon(h, 0.55, 0.08)
        sea = blend(np.full_like(sea, (80, 210, 200)), sea, depth)
        img = blend(sky, sea, soft_horizon(h, 0.4, 0.035))
        # archipelago islands
        for cx_f, cy_f, sx, sy in ((0.35, 0.52, 0.22, 0.08), (0.62, 0.58, 0.14, 0.05), (0.78, 0.5, 0.1, 0.06)):
            island = ((xx - cx_f * w) ** 2 / (sx * w) ** 2 + (yy - cy_f * h) ** 2 / (sy * h) ** 2) < (0.85 + 0.3 * n)
            sand = np.full_like(img, (230, 210, 160))
            green = np.full_like(img, (25, 110, 50))
            img = blend(img, sand, island.astype(np.float32) * 0.9)
            canopy = island & (yy < cy_f * h + 8)
            img = blend(img, green, canopy.astype(np.float32) * (0.55 + 0.35 * n2))
        # palm silhouettes
        for px in (int(0.3 * w), int(0.55 * w), int(0.7 * w)):
            base = int(0.5 * h)
            for i in range(90):
                y = base - i
                if 0 <= y < h:
                    img[y, px : px + 3] = (30, 40, 20)
            for ang in (-0.8, -0.3, 0.3, 0.8):
                for t in range(40):
                    x = int(px + t * math.cos(ang))
                    y = int(base - 90 + t * math.sin(ang) * 0.3 + abs(ang) * t * 0.2)
                    if 0 <= x < w and 0 <= y < h:
                        img[y, max(0, x - 1) : min(w, x + 2)] = (20, 80, 35)
        return img

    def tundra():
        sky = sky_gradient(h, w, (180, 210, 255), (100, 140, 190), n)
        # aurora
        aur = np.sin(xx / w * 6 + n * 4) * np.exp(-((yy / h - 0.2) ** 2) / 0.04)
        sky = blend(sky, np.full_like(sky, (80, 220, 160)), np.clip(aur, 0, 1) * 0.35)
        snow = sky_gradient(h, w, (245, 248, 255), (170, 185, 210), n2)
        snow = snow + (n[..., None] - 0.5) * 20
        img = blend(sky, snow, soft_horizon(h, 0.42, 0.04))
        mtn, m = mountains(h, w, 0.48, [(0.28, 0.26, 0.32), (0.68, 0.2, 0.38)], (230, 235, 245), n)
        img = blend(img, mtn, m)
        # frozen shore
        ice = (n2 > 0.55) & (yy / h > 0.62) & (yy / h < 0.78)
        img = blend(img, np.full_like(img, (140, 190, 220)), ice.astype(np.float32) * 0.55)
        return img

    def underground():
        cave = sky_gradient(h, w, (25, 35, 55), (8, 10, 18), n)
        water = sky_gradient(h, w, (15, 55, 90), (5, 15, 30), n2)
        water = water + (n[..., None] - 0.5) * 30 * np.array([0.2, 0.5, 1.0])
        img = blend(cave, water, soft_horizon(h, 0.58, 0.05))
        for x in rng.integers(15, w - 15, 22):
            length = int(rng.uniform(0.12, 0.38) * h)
            tw = max(2, int(rng.integers(3, 14)))
            for i in range(length):
                half = max(1, tw * (1 - i / length) / 2)
                x0, x1 = int(x - half), int(x + half)
                img[i, x0:x1] = (45 + 10 * n[i, x0:x1].mean(), 50, 60)
        # biolum pools
        glow = np.exp(-((yy / h - 0.72) ** 2) / 0.04) * (0.5 + 0.5 * n)
        img[..., 2] = np.clip(img[..., 2] + glow * 90, 0, 255)
        img[..., 1] = np.clip(img[..., 1] + glow * 35, 0, 255)
        # swamp shoreline
        shore = (n > 0.6) & (np.abs(yy / h - 0.58) < 0.06)
        img = blend(img, np.full_like(img, (20, 30, 25)), shore.astype(np.float32) * 0.7)
        return img

    def savannah():
        sky = sky_gradient(h, w, (255, 200, 110), (120, 70, 40), n)
        sky = paint_clouds(sky, n2, 0.35, (255, 230, 180))
        grass = sky_gradient(h, w, (160, 155, 55), (80, 90, 40), n2)
        grass = grass + (n[..., None] - 0.5) * 25 * np.array([0.5, 0.8, 0.2])
        img = blend(sky, grass, soft_horizon(h, 0.4, 0.04))
        for x in rng.integers(50, w - 50, 6):
            trunk_h = int(rng.uniform(0.32, 0.48) * h)
            img[trunk_h : int(0.7 * h), x : x + 5] = (55, 35, 22)
            canopy = ((yy - trunk_h) ** 2 / (35 + 20 * n) ** 2 + (xx - x) ** 2 / (100 + 40 * n2) ** 2) < 1
            img = blend(img, np.full_like(img, (40, 85, 35)), canopy.astype(np.float32) * 0.75)
        # heat shimmer plains highlight
        img = blend(img, np.full_like(img, (255, 230, 150)), (yy / h > 0.75).astype(np.float32) * 0.12)
        return img

    def scrubland():
        sky = sky_gradient(h, w, (200, 175, 150), (70, 50, 55), n)
        dirt = sky_gradient(h, w, (130, 105, 80), (45, 30, 35), n2)
        dirt = dirt + (n[..., None] - 0.5) * 30 * np.array([1.0, 0.7, 0.4])
        img = blend(sky, dirt, soft_horizon(h, 0.4, 0.045))
        for _ in range(55):
            cx, cy = int(rng.integers(0, w)), int(rng.integers(int(0.42 * h), h))
            rx, ry = int(rng.integers(12, 40)), int(rng.integers(8, 25))
            blob = ((yy - cy) ** 2 / ry**2 + (xx - cx) ** 2 / rx**2) < (0.8 + 0.4 * n[cy, cx])
            col = (28, 22, 25) if rng.random() > 0.45 else (55, 75, 40)
            img = blend(img, np.full_like(img, col), blob.astype(np.float32) * 0.7)
        # pale plains wash left
        img = blend(img, np.full_like(img, (210, 200, 170)), ((xx / w < 0.35) & (yy / h > 0.5)).astype(np.float32) * 0.2)
        return img

    def plateau():
        sky = sky_gradient(h, w, (255, 130, 70), (70, 35, 55), n)
        sky = paint_clouds(sky, n2, 0.4, (255, 200, 150))
        rock = sky_gradient(h, w, (180, 80, 55), (90, 45, 35), n2)
        rock = rock + (n[..., None] - 0.5) * 35 * np.array([1.1, 0.5, 0.3])
        img = blend(sky, rock, soft_horizon(h, 0.36, 0.04))
        for i, (yf, inset) in enumerate(((0.42, 0.12), (0.52, 0.18), (0.62, 0.22))):
            y0 = int(yf * h)
            col = np.array([210 - i * 25, 170 - i * 15, 120 - i * 10], dtype=np.float32)
            band = (yy >= y0) & (yy < y0 + 22) & (xx > inset * w) & (xx < (1 - inset) * w)
            img = blend(img, np.full_like(img, col), band.astype(np.float32) * 0.85)
        plains = soft_horizon(h, 0.72, 0.05)
        img = blend(img, np.full_like(img, (235, 215, 150)), plains * 0.45)
        return img

    def taiga():
        sky = sky_gradient(h, w, (100, 120, 145), (35, 45, 55), n)
        sky = paint_clouds(sky, n2, 0.35, (180, 190, 200))
        ground = sky_gradient(h, w, (50, 70, 40), (22, 28, 20), n2)
        img = blend(sky, ground, soft_horizon(h, 0.4, 0.04))
        mtn, m = mountains(h, w, 0.45, [(0.22, 0.28, 0.3), (0.72, 0.24, 0.32)], (75, 60, 55), n)
        # snow caps
        caps = m * (yy < 0.38 * h).astype(np.float32)
        mtn = blend(mtn, np.full_like(mtn, (230, 235, 240)), caps * 0.7)
        img = blend(img, mtn, m)
        for x in rng.integers(25, w - 25, 28):
            base = int(rng.uniform(0.52, 0.78) * h)
            th = int(rng.uniform(70, 170))
            for i in range(th):
                half = int((16 + 8 * n[min(base, h - 1), x]) * (1 - i / th) + 2)
                y = base - i
                if 0 <= y < h:
                    img[y, max(0, x - half) : min(w, x + half)] = (
                        18 + 10 * n2[y, x],
                        60 + 20 * n[y, x],
                        28,
                    )
        # ember / magma near peaks
        img[..., 0] = np.clip(img[..., 0] + m * n * 55, 0, 255)
        img[..., 1] = np.clip(img[..., 1] + m * n * 15, 0, 255)
        return img

    def lotus():
        base = sky_gradient(h, w, (35, 28, 48), (8, 6, 12), n)
        # ambient glow
        glow = np.exp(-(((xx - w / 2) / (w * 0.35)) ** 2 + ((yy - h * 0.48) / (h * 0.35)) ** 2))
        base = blend(base, np.full_like(base, (60, 40, 90)), glow * 0.5)
        cx, cy = w * 0.5, h * 0.46
        petals = np.zeros_like(base)
        for k in range(8):
            ang = k * math.pi / 4 + 0.15
            xr = (xx - cx) * math.cos(ang) + (yy - cy) * math.sin(ang)
            yr = -(xx - cx) * math.sin(ang) + (yy - cy) * math.cos(ang)
            petal = (xr**2 / (w * 0.11) ** 2 + ((yr - 50) ** 2) / (h * 0.2) ** 2) < (0.9 + 0.2 * n)
            hue = np.array(
                [
                    160 + 50 * math.sin(k * 0.9),
                    110 + 60 * math.cos(k * 1.2),
                    150 + 45 * math.sin(k * 0.6 + 1),
                ],
                dtype=np.float32,
            )
            shade = 0.65 + 0.35 * n2
            petals = blend(petals, np.full_like(base, hue) * shade[..., None], petal.astype(np.float32) * 0.8)
        center = ((xx - cx) ** 2 + (yy - cy) ** 2) < (w * 0.055) ** 2
        petals = blend(petals, np.full_like(base, (255, 230, 120)), center.astype(np.float32))
        # metallic sheen
        sheen = np.clip((n - 0.55) * 3, 0, 1) * (petals.max(axis=2) > 0)
        petals = blend(petals, np.full_like(petals, (240, 240, 255)), sheen * 0.35)
        return blend(base, petals, (petals.max(axis=2) > 0).astype(np.float32))

    def city():
        sky = sky_gradient(h, w, (45, 40, 65), (12, 10, 18), n)
        sky = paint_clouds(sky, n2, 0.25, (70, 60, 90))
        ground = sky_gradient(h, w, (55, 50, 45), (18, 14, 12), n2)
        img = blend(sky, ground, soft_horizon(h, 0.58, 0.04))
        for x, bw, bh, lean in (
            (0.12, 0.07, 0.42, 0),
            (0.28, 0.1, 0.55, 2),
            (0.48, 0.14, 0.62, -1),
            (0.68, 0.09, 0.48, 1),
            (0.82, 0.07, 0.38, 0),
        ):
            x0 = int(x * w)
            x1 = x0 + int(bw * w)
            y0 = int((0.92 - bh) * h)
            for yi in range(y0, int(0.92 * h)):
                shift = int(lean * (yi - y0) / 40)
                xa, xb = max(0, x0 + shift), min(w, x1 + shift)
                img[yi, xa:xb] = (50 + 15 * n[yi, xa:xb].mean(), 48, 46)
            for wy in range(y0 + 12, int(0.9 * h), 20):
                for wx in range(x0 + 5, x1 - 5, 12):
                    if rng.random() > 0.35:
                        img[wy : wy + 8, wx : wx + 5] = (220, 170, 70)
                    else:
                        img[wy : wy + 8, wx : wx + 5] = (18, 16, 14)
        cracks = ((np.abs(n - 0.5) < 0.02) | (np.abs(n2 - 0.5) < 0.015)) & (yy / h > 0.7)
        img = blend(img, np.full_like(img, (210, 205, 190)), cracks.astype(np.float32) * 0.65)
        # fog
        img = blend(img, np.full_like(img, (40, 35, 50)), soft_horizon(h, 0.75, 0.08) * 0.25)
        return img

    builders = {
        "badlands": badlands,
        "bayou": bayou,
        "tropical": tropical,
        "tundra": tundra,
        "underground": underground,
        "savannah": savannah,
        "scrubland": scrubland,
        "plateau": plateau,
        "taiga": taiga,
        "lotus": lotus,
        "city": city,
    }
    img = builders[theme]()
    # film grain + soft blur for painterly feel
    grain = (fbm(h, w, seed=seed + 200) - 0.5) * 14
    img = np.clip(img + grain[..., None], 0, 255).astype(np.uint8)
    im = Image.fromarray(img, "RGB")
    im = im.filter(ImageFilter.GaussianBlur(radius=0.8))
    # light vignette
    vig = 1 - 0.28 * (((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    arr = np.asarray(im).astype(np.float32) * np.clip(vig, 0.6, 1.0)[..., None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


def try_hf_background(prompt: str, seed: int) -> Image.Image | None:
    """Attempt HF Inference; return None on any failure."""
    try:
        from huggingface_hub import InferenceClient, get_token

        token = os.environ.get("HF_TOKEN") or get_token()
        if not token:
            return None
        client = InferenceClient(token=token)
        for model in (
            "black-forest-labs/FLUX.1-schnell",
            "stabilityai/stable-diffusion-xl-base-1.0",
        ):
            try:
                img = client.text_to_image(prompt, model=model)
                return cover_resize(img.convert("RGB"), W, H)
            except Exception:
                continue
    except Exception:
        return None
    return None


def rounded_rect_mask(size: tuple[int, int], radius: int) -> Image.Image:
    w, h = size
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=255)
    return m


def draw_gradient_border_panel(
    base: Image.Image,
    box: tuple[int, int, int, int],
    color_l: tuple[int, int, int],
    color_r: tuple[int, int, int],
    fill_alpha: int = 175,
    border: int = 3,
    radius: int = 14,
) -> None:
    """Semi-transparent dark panel with L→R accent border."""
    x0, y0, x1, y1 = box
    pw, ph = x1 - x0, y1 - y0
    panel = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
    # fill
    fill = Image.new("RGBA", (pw, ph), (12, 12, 14, fill_alpha))
    mask = rounded_rect_mask((pw, ph), radius)
    panel.paste(fill, (0, 0), mask)
    # gradient border ring
    border_img = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
    bd = ImageDraw.Draw(border_img)
    for i in range(border):
        bd.rounded_rectangle(
            [i, i, pw - 1 - i, ph - 1 - i],
            radius=max(1, radius - i),
            outline=(255, 255, 255, 0),
        )
    # paint gradient onto border pixels
    arr = np.asarray(border_img).copy()
    # create gradient colors
    xs = np.linspace(0, 1, pw, dtype=np.float32)
    grad = np.stack(
        [
            (1 - xs) * color_l[0] + xs * color_r[0],
            (1 - xs) * color_l[1] + xs * color_r[1],
            (1 - xs) * color_l[2] + xs * color_r[2],
        ],
        axis=1,
    ).astype(np.uint8)
    # outer ring mask
    outer = rounded_rect_mask((pw, ph), radius)
    inner = Image.new("L", (pw, ph), 0)
    idr = ImageDraw.Draw(inner)
    idr.rounded_rectangle(
        [border, border, pw - 1 - border, ph - 1 - border],
        radius=max(1, radius - border),
        fill=255,
    )
    ring = ImageChops_subtract(outer, inner)
    ring_a = np.asarray(ring)
    for y in range(ph):
        row = arr[y]
        m = ring_a[y] > 0
        row[m, 0] = grad[m, 0]
        row[m, 1] = grad[m, 1]
        row[m, 2] = grad[m, 2]
        row[m, 3] = 230
        arr[y] = row
    border_img = Image.fromarray(arr, "RGBA")
    panel = Image.alpha_composite(panel, border_img)
    # slight inner highlight
    base.paste(Image.alpha_composite(base.crop((x0, y0, x1, y1)).convert("RGBA"), panel), (x0, y0))


def ImageChops_subtract(a: Image.Image, b: Image.Image) -> Image.Image:
    aa = np.asarray(a).astype(np.int16)
    bb = np.asarray(b).astype(np.int16)
    return Image.fromarray(np.clip(aa - bb, 0, 255).astype(np.uint8), mode=a.mode)


def draw_mana_symbol(draw: ImageDraw.ImageDraw, xy: tuple[int, int], kind: str, r: int = 11) -> None:
    cx, cy = xy
    fill = {
        "W": (248, 246, 216),
        "U": (14, 104, 171),
        "B": (35, 20, 40),
        "R": (211, 32, 42),
        "G": (0, 115, 62),
        "C": (190, 185, 175),
        "T": (200, 200, 200),
    }.get(kind, (180, 180, 180))
    outline = (20, 20, 20)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill, outline=outline, width=1)
    # simple glyph
    if kind == "U":
        draw.polygon([(cx, cy - 5), (cx - 4, cy + 3), (cx + 4, cy + 3)], fill=(10, 30, 60))
        draw.ellipse([cx - 2, cy + 1, cx + 2, cy + 5], fill=(10, 30, 60))
    elif kind == "R":
        draw.polygon([(cx, cy - 6), (cx - 5, cy + 2), (cx - 1, cy + 1), (cx + 2, cy + 5), (cx + 5, cy - 1)], fill=(40, 10, 5))
    elif kind == "G":
        draw.ellipse([cx - 3, cy - 4, cx + 3, cy + 2], fill=(200, 230, 180))
        draw.rectangle([cx - 1, cy + 1, cx + 1, cy + 6], fill=(40, 80, 30))
    elif kind == "B":
        draw.ellipse([cx - 3, cy - 4, cx + 3, cy + 3], fill=(200, 190, 180))
        draw.polygon([(cx - 5, cy + 2), (cx, cy + 7), (cx + 5, cy + 2)], fill=(200, 190, 180))
    elif kind == "W":
        for ang in range(0, 360, 45):
            rad = math.radians(ang)
            draw.line(
                [cx, cy, cx + int(6 * math.cos(rad)), cy + int(6 * math.sin(rad))],
                fill=(180, 150, 40),
                width=1,
            )
        draw.ellipse([cx - 2, cy - 2, cx + 2, cy + 2], fill=(180, 150, 40))
    elif kind == "C":
        draw.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], outline=(60, 60, 60), width=2)
    elif kind == "T":
        # tap arrow
        draw.arc([cx - 5, cy - 5, cx + 5, cy + 5], 40, 300, fill=(20, 20, 20), width=2)
        draw.polygon([(cx + 4, cy - 5), (cx + 7, cy - 1), (cx + 2, cy - 1)], fill=(20, 20, 20))


def render_rules_line(
    draw: ImageDraw.ImageDraw,
    img: Image.Image,
    text: str,
    xy: tuple[int, int],
    font: ImageFont.FreeTypeFont,
    fill=(245, 245, 245),
) -> None:
    """Render rules text with {X} mana/tap tokens replaced by symbols."""
    x, y = xy
    i = 0
    while i < len(text):
        if text[i] == "{" and "}" in text[i:]:
            j = text.index("}", i)
            token = text[i + 1 : j]
            draw_mana_symbol(ImageDraw.Draw(img), (x + 11, y + 8), token, r=10)
            x += 24
            i = j + 1
            continue
        # draw one char (or run until next brace)
        nxt = text.find("{", i)
        chunk = text[i:] if nxt < 0 else text[i:nxt]
        if "\n" in chunk:
            pre, _, rest = chunk.partition("\n")
            if pre:
                draw.text((x, y), pre, font=font, fill=fill)
                x += int(draw.textlength(pre, font=font))
            y += int(font.size * 1.35)
            x = xy[0]
            i += len(pre) + 1
            continue
        draw.text((x, y), chunk, font=font, fill=fill)
        x += int(draw.textlength(chunk, font=font))
        i += len(chunk)


def draw_holo_stamp(img: Image.Image, cx: int, cy: int) -> None:
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    rx, ry = 22, 14
    # crystalline oval
    for i in range(8):
        col = (180 + i * 8, 190 + i * 5, 200, 180)
        d.ellipse([cx - rx + i, cy - ry + i // 2, cx + rx - i, cy + ry - i // 2], outline=col, width=1)
    # pixel glitter
    rng = np.random.default_rng(42)
    for _ in range(40):
        px = cx + int(rng.integers(-rx + 2, rx - 2))
        py = cy + int(rng.integers(-ry + 2, ry - 2))
        if ((px - cx) / rx) ** 2 + ((py - cy) / ry) ** 2 <= 1:
            c = int(rng.integers(160, 255))
            d.point((px, py), fill=(c, c, 255, 220))
    img.alpha_composite(overlay)


def apply_card_frame(
    art: Image.Image,
    *,
    name: str,
    typeline: str,
    rules: str,
    accent_l: tuple[int, int, int],
    accent_r: tuple[int, int, int],
    collector: str,
    rarity: str = "R",
) -> Image.Image:
    art = cover_resize(art.convert("RGB"), W, H)
    canvas = art.convert("RGBA")

    # black outer frame with rounded corners
    frame = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    inner = rounded_rect_mask((W - 2 * BORDER, H - 2 * BORDER), CORNER_R)
    art_inner = canvas.crop((BORDER, BORDER, W - BORDER, H - BORDER))
    frame.paste(art_inner, (BORDER, BORDER), inner)

    # panels
    x0, x1 = MARGIN_X, W - MARGIN_X
    draw_gradient_border_panel(frame, (x0, NAME_Y, x1, NAME_Y + NAME_H), accent_l, accent_r, fill_alpha=185, radius=16)
    draw_gradient_border_panel(frame, (x0, TYPE_Y, x1, TYPE_Y + TYPE_H), accent_l, accent_r, fill_alpha=190, radius=14)
    draw_gradient_border_panel(frame, (x0, TEXT_Y, x1, TEXT_Y + TEXT_H), accent_l, accent_r, fill_alpha=200, radius=14)

    # dark footer strip
    foot = Image.new("RGBA", (W - 2 * BORDER, H - FOOTER_Y - BORDER), (0, 0, 0, 210))
    frame.paste(foot, (BORDER, FOOTER_Y), foot)

    d = ImageDraw.Draw(frame)
    f_name = load_font(FONT_NAME, 28)
    f_type = load_font(FONT_TYPE, 20)
    f_rules = load_font(FONT_RULES, 18)
    f_foot = load_font(FONT_FOOT, 13)
    f_foot_sm = load_font(FONT_FOOT, 11)

    d.text((x0 + 18, NAME_Y + 10), name, font=f_name, fill=(250, 250, 250))
    d.text((x0 + 18, TYPE_Y + 12), typeline, font=f_type, fill=(245, 245, 245))

    # rules — support multi-line with symbols
    rules_x, rules_y = x0 + 18, TEXT_Y + 16
    for line_i, line in enumerate(rules.split("\n")):
        render_rules_line(d, frame, line, (rules_x, rules_y + line_i * 28), f_rules)

    # footer
    d.text((x0 + 8, FOOTER_Y + 6), f"{rarity} {collector}", font=f_foot, fill=(240, 240, 240))
    # quill-ish mark as simple glyph
    d.text((x0 + 8, FOOTER_Y + 24), "PHI • EN  ✒  Philipp Schmidt + ChatGPT", font=f_foot_sm, fill=(230, 230, 230))
    copyright = "TM & © 2026 Wizards of the Coast"
    cw = d.textlength(copyright, font=f_foot_sm)
    d.text((W - MARGIN_X - 8 - cw, FOOTER_Y + 28), copyright, font=f_foot_sm, fill=(220, 220, 220))

    draw_holo_stamp(frame, W // 2, FOOTER_Y + 22)

    # ensure outer rounded black corners
    out = Image.new("RGB", (W, H), (0, 0, 0))
    full_mask = rounded_rect_mask((W, H), CORNER_R + 2)
    out.paste(frame.convert("RGB"), (0, 0), full_mask)
    # re-apply thin black edge
    edge = ImageDraw.Draw(out)
    edge.rounded_rectangle([0, 0, W - 1, H - 1], radius=CORNER_R + 2, outline=(0, 0, 0), width=BORDER)
    return out


@dataclass
class CardSpec:
    slug: str
    art_id: str
    name: str
    typeline: str
    rules: str
    colors: tuple[str, str]  # L, R mana keys
    theme: str
    prompt: str
    rarity: str = "R"


CARDS: list[CardSpec] = [
    CardSpec(
        "badlands",
        "phi-0002",
        "Badlands",
        "Land — Swamp Mountain",
        "({T}: Add {B} or {R}.)",
        ("B", "R"),
        "badlands",
        "fantasy full-art landscape, arid red rock badlands canyon meeting dark swamp marsh, dramatic sky, MTG illustration, no text",
    ),
    CardSpec(
        "bayou",
        "phi-0003",
        "Bayou",
        "Land — Swamp Forest",
        "({T}: Add {B} or {G}.)",
        ("B", "G"),
        "bayou",
        "fantasy bayou swamp with cypress trees black water and lush forest canopy, misty, MTG full art, no text",
    ),
    CardSpec(
        "tropical-island",
        "phi-0004",
        "Tropical Island",
        "Land — Forest Island",
        "({T}: Add {G} or {U}.)",
        ("G", "U"),
        "tropical",
        "tropical island paradise turquoise water lush jungle forest coastline, fantasy MTG full art, no text",
    ),
    CardSpec(
        "tundra",
        "phi-0005",
        "Tundra",
        "Land — Plains Island",
        "({T}: Add {W} or {U}.)",
        ("W", "U"),
        "tundra",
        "frozen tundra plains and icy blue coastal waters aurora light, fantasy MTG full art, no text",
    ),
    CardSpec(
        "underground-sea",
        "phi-0006",
        "Underground Sea",
        "Land — Island Swamp",
        "({T}: Add {U} or {B}.)",
        ("U", "B"),
        "underground",
        "vast underground sea cavern bioluminescent blue water dark swamp shores, fantasy MTG full art, no text",
    ),
    CardSpec(
        "savannah",
        "phi-0007",
        "Savannah",
        "Land — Forest Plains",
        "({T}: Add {G} or {W}.)",
        ("G", "W"),
        "savannah",
        "golden savannah plains with acacia trees and sunlit grasslands forest edge, fantasy MTG full art, no text",
    ),
    CardSpec(
        "scrubland",
        "phi-0008",
        "Scrubland",
        "Land — Plains Swamp",
        "({T}: Add {W} or {B}.)",
        ("W", "B"),
        "scrubland",
        "dry scrubland plains fading into dark marshy swamp, muted light, fantasy MTG full art, no text",
    ),
    CardSpec(
        "plateau",
        "phi-0009",
        "Plateau",
        "Land — Mountain Plains",
        "({T}: Add {R} or {W}.)",
        ("R", "W"),
        "plateau",
        "red rock mountain plateau overlooking golden sunlit plains, dramatic cliffs, fantasy MTG full art, no text",
    ),
    CardSpec(
        "taiga",
        "phi-0010",
        "Taiga",
        "Land — Mountain Forest",
        "({T}: Add {R} or {G}.)",
        ("R", "G"),
        "taiga",
        "volcanic mountain taiga evergreen forest snowy peaks ember glow, fantasy MTG full art, no text",
    ),
    CardSpec(
        "lotus-petal",
        "phi-0011",
        "Lotus Petal",
        "Artifact",
        "{T}, Sacrifice Lotus Petal: Add one mana of any color.",
        ("A", "A"),
        "lotus",
        "magical metallic lotus flower artifact glowing prismatic petals on dark void, fantasy MTG full art, no text",
        rarity="U",
    ),
    CardSpec(
        "city-of-traitors",
        "phi-0012",
        "City of Traitors",
        "Land",
        "When you play another land, sacrifice City of Traitors.\n{T}: Add {C}{C}.",
        ("C", "C"),
        "city",
        "ruined traitor city broken towers colorless cracked stone glowing fissures, fantasy MTG full art, no text",
    ),
]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    notes: list[str] = []
    notes.append("# PHI full-art proxy batch notes\n")
    notes.append(f"- Output: `{OUT_DIR}`")
    notes.append(f"- Canvas: {W}×{H} (reference match); print pipeline later normalizes to 488×680")
    notes.append("- Frame: Pillow composite (name bar, type line, text box, PHI footer, black border, dual accents)")
    notes.append("- HF Inference: attempted if token present; falls back to procedural backgrounds on 403/error\n")

    # 1) copy volcanic island
    dest0 = OUT_DIR / "volcanic-island__phi-0001.jpg"
    if not REF_SRC.is_file():
        raise SystemExit(f"Missing reference: {REF_SRC}")
    shutil.copy2(REF_SRC, dest0)
    im0 = Image.open(dest0)
    notes.append(f"- `volcanic-island__phi-0001.jpg`: copied from user asset ({im0.size[0]}×{im0.size[1]})")
    print(f"copied {dest0.name} {im0.size}")

    hf_ok = False
    for i, card in enumerate(CARDS):
        out = OUT_DIR / f"{card.slug}__{card.art_id}.jpg"
        bg = try_hf_background(card.prompt, seed=1000 + i)
        src = "hf"
        if bg is None:
            src = "procedural"
            bg = procedural_bg(card.theme, seed=1000 + i)
        else:
            hf_ok = True
        cl, cr = COLORS[card.colors[0]], COLORS[card.colors[1]]
        framed = apply_card_frame(
            bg,
            name=card.name,
            typeline=card.typeline,
            rules=card.rules,
            accent_l=cl,
            accent_r=cr,
            collector=card.art_id.split("-")[1],
            rarity=card.rarity,
        )
        framed.save(out, "JPEG", quality=92, optimize=True)
        print(f"wrote {out.name} {framed.size} bg={src}")
        notes.append(f"- `{out.name}`: {framed.size[0]}×{framed.size[1]}, bg={src}, accents={card.colors}")

    notes.append("")
    notes.append(f"- HF backgrounds used: {'yes' if hf_ok else 'no (procedural fallback)'}")
    notes.append("- Artist credit footer: Philipp Schmidt + ChatGPT (matches reference)")
    notes.append("- Proxies for personal use; not official Wizards product")
    (OUT_DIR / "BATCH_NOTES.md").write_text("\n".join(notes) + "\n", encoding="utf-8")
    print("wrote BATCH_NOTES.md")


if __name__ == "__main__":
    main()
