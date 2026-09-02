#!/usr/bin/env python3
"""Silent cursor-click walkthrough over CommercePulse dashboard pages."""
from __future__ import annotations

import math
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1920, 1080
FPS = 30
BG = (27, 26, 25)
GOLD = (242, 200, 17)
WHITE = (248, 250, 252)
MUTED = (148, 163, 184)
GRAY = (100, 116, 139)

ROOT = Path(__file__).resolve().parents[2]
SHOTS = ROOT / "screenshots"
OUT = ROOT / "artifacts" / "commercepulse-demo.mp4"

FONT = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
FONT_B = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"

# Approximate tab centers on bottom strip (measured from render layout)
TABS = {
    "executive": (160, 1066),
    "sales": (360, 1066),
    "customer": (580, 1066),
    "product": (800, 1066),
    "operations": (1020, 1066),
    "models": (1220, 1066),
}

PAGES = [
    ("executive", SHOTS / "executive-overview.png"),
    ("sales", SHOTS / "sales-performance.png"),
    ("customer", SHOTS / "customer-intelligence.png"),
    ("product", SHOTS / "product-country.png"),
    ("operations", SHOTS / "operations-returns.png"),
    ("models", SHOTS / "model-insights.png"),
]


def font(path: str, size: int):
    return ImageFont.truetype(path, size)


def ease_in_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, t))
    if t < 0.5:
        return 4 * t * t * t
    return 1 - (-2 * t + 2) ** 3 / 2


def ease_out_back(t: float, overshoot: float = 1.15) -> float:
    t = max(0.0, min(1.0, t))
    c1 = 1.70158 * overshoot
    c3 = c1 + 1
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def make_cursor(scale: float = 1.0) -> Image.Image:
    s = int(32 * scale)
    cur = Image.new("RGBA", (s, int(s * 1.35)), (0, 0, 0, 0))
    d = ImageDraw.Draw(cur)
    pts = [
        (2, 2), (2, int(s * 1.05)), (int(s * 0.32), int(s * 0.78)),
        (int(s * 0.48), int(s * 1.28)), (int(s * 0.62), int(s * 1.22)),
        (int(s * 0.42), int(s * 0.72)), (int(s * 0.78), int(s * 0.72)),
    ]
    shadow = Image.new("RGBA", cur.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.polygon([(x + 2, y + 3) for x, y in pts], fill=(0, 0, 0, 90))
    shadow = shadow.filter(ImageFilter.GaussianBlur(1.5))
    cur = Image.alpha_composite(cur, shadow)
    d = ImageDraw.Draw(cur)
    d.polygon(pts, fill=(255, 255, 255, 245), outline=(20, 20, 20, 255))
    return cur


CURSOR = make_cursor(1.0)
CURSOR_CLICK = make_cursor(0.92)


def make_title_card() -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((48, 48, W - 48, H - 48), radius=18, outline=GOLD, width=2)
    d.rounded_rectangle((860, 250, 1060, 330), radius=10, fill=GOLD)
    d.text((890, 268), "PBI", font=font(FONT_B, 40), fill=BG)
    title = "CommercePulse · Retail Intelligence walkthrough"
    tb = d.textbbox((0, 0), title, font=font(FONT_B, 34))
    d.text(((W - (tb[2] - tb[0])) // 2, 400), title, font=font(FONT_B, 34), fill=WHITE)
    sub = "Online Retail II  ·  Dec 2009 – Dec 2011  ·  Silent product demo"
    sb = d.textbbox((0, 0), sub, font=font(FONT, 20))
    d.text(((W - (sb[2] - sb[0])) // 2, 470), sub, font=font(FONT, 20), fill=MUTED)
    hint = "Cursor-driven page navigation"
    hb = d.textbbox((0, 0), hint, font=font(FONT, 16))
    d.text(((W - (hb[2] - hb[0])) // 2, 560), hint, font=font(FONT, 16), fill=GRAY)
    return img


def make_end_card() -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((48, 48, W - 48, H - 48), radius=18, outline=GOLD, width=2)
    line1 = "CommercePulse"
    tb = d.textbbox((0, 0), line1, font=font(FONT_B, 44))
    d.text(((W - (tb[2] - tb[0])) // 2, 390), line1, font=font(FONT_B, 44), fill=WHITE)
    line2 = "Medallion DE  ·  RFM / churn baselines  ·  Power BI pages  ·  Insights assistant"
    sb = d.textbbox((0, 0), line2, font=font(FONT, 18))
    d.text(((W - (sb[2] - sb[0])) // 2, 470), line2, font=font(FONT, 18), fill=MUTED)
    line3 = "Data: UCI Online Retail II  ·  Portfolio sample"
    eb = d.textbbox((0, 0), line3, font=font(FONT_B, 18))
    d.text(((W - (eb[2] - eb[0])) // 2, 530), line3, font=font(FONT_B, 18), fill=GOLD)
    return img


def draw_ripple(base: Image.Image, cx: float, cy: float, age: float, duration: float = 0.35) -> None:
    if age < 0 or age > duration:
        return
    t = age / duration
    radius = 8 + t * 36
    alpha = int(200 * (1 - t))
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    r = int(radius)
    bbox = (int(cx - r), int(cy - r), int(cx + r), int(cy + r))
    if t < 0.25:
        od.ellipse(bbox, fill=(255, 255, 255, int(90 * (1 - t / 0.25))))
    od.ellipse(bbox, outline=(242, 200, 17, alpha), width=3)
    r2 = max(2, int(radius * 0.55))
    od.ellipse((int(cx - r2), int(cy - r2), int(cx + r2), int(cy + r2)), outline=(255, 255, 255, alpha // 2), width=2)
    base.alpha_composite(overlay)


class Timeline:
    def __init__(self):
        self.events = []
        self.t = 0.0

    def wait(self, dt: float):
        self.t += dt

    def move_to(self, x: float, y: float, duration: float, overshoot: bool = True):
        self.events.append(("move", self.t, self.t + duration, x, y, overshoot))
        self.t += duration

    def click(self):
        self.events.append(("click", self.t))
        self.t += 0.12

    def switch(self, page_key: str, at: float | None = None):
        self.events.append(("switch", at if at is not None else self.t, page_key))

    def show_card(self, which: str, duration: float):
        self.events.append(("card", self.t, self.t + duration, which))
        self.t += duration


def build_script() -> Timeline:
    tl = Timeline()
    tl.show_card("title", 2.0)
    tl.switch("executive")
    tl.events.append(("spawn", tl.t, 960, 520))
    tl.wait(1.1)
    tl.move_to(220, 198, 1.0)
    tl.wait(1.0)
    tl.move_to(147, 110, 0.85)
    tl.wait(0.2)
    tl.click()
    tl.wait(0.85)

    for key, hover in [
        ("sales", (420, 380)),
        ("customer", (380, 420)),
        ("product", (500, 400)),
        ("operations", (360, 450)),
        ("models", (900, 420)),
    ]:
        tl.move_to(*TABS[key], 1.1)
        tl.wait(0.15)
        tl.click()
        tl.switch(key, tl.t)
        tl.wait(0.75)
        tl.move_to(*hover, 1.0)
        tl.wait(0.95)
        tl.move_to(hover[0] + 400, hover[1] - 40, 0.85)
        tl.wait(0.7)

    tl.show_card("end", 2.0)
    return tl


def _sample_cursor_clean(tl, t, page, mode):
    if mode in ("title", "end"):
        return None, None, False, mode
    cx, cy = 960.0, 520.0
    clicking = False
    active_seg = None
    for ev in tl.events:
        if ev[0] == "spawn":
            if ev[1] <= t:
                cx, cy = float(ev[2]), float(ev[3])
            else:
                break
        elif ev[0] == "move":
            t0, t1, tx, ty, overshoot = ev[1], ev[2], ev[3], ev[4], ev[5]
            if t < t0:
                break
            if t >= t1:
                cx, cy = tx, ty
            else:
                active_seg = (t0, t1, cx, cy, tx, ty, overshoot)
                break
        elif ev[0] == "click":
            if ev[1] <= t < ev[1] + 0.12:
                clicking = True
    if active_seg:
        t0, t1, x0, y0, x1, y1, overshoot = active_seg
        u = (t - t0) / max(1e-6, t1 - t0)
        e = ease_out_back(u, 1.12) if overshoot else ease_in_out_cubic(u)
        e = max(-0.05, min(1.15, e))
        cx = lerp(x0, x1, e)
        cy = lerp(y0, y1, e)
    return cx, cy, clicking, page


def collect_ripples(tl: Timeline):
    ripples = []
    for ev in tl.events:
        if ev[0] != "click":
            continue
        t_click = ev[1]
        last_xy = (960, 520)
        for e2 in tl.events:
            if e2[0] == "spawn" and e2[1] <= t_click:
                last_xy = (e2[2], e2[3])
            if e2[0] == "move" and e2[2] <= t_click:
                last_xy = (e2[3], e2[4])
            if e2[0] == "click" and e2[1] == t_click:
                break
        ripples.append((float(last_xy[0]), float(last_xy[1]), t_click))
    return ripples


def page_at(tl: Timeline, t: float) -> str:
    mode = "title"
    page = "executive"
    for ev in tl.events:
        if ev[0] == "card":
            if ev[1] <= t < ev[2]:
                return ev[3]
            if t >= ev[2] and ev[3] == "title":
                mode = "page"
        if ev[0] == "switch" and ev[1] <= t:
            page = ev[2]
            mode = "page"
        if ev[0] == "card" and ev[3] == "end" and ev[1] <= t:
            return "end"
    return page if mode == "page" else mode


def main():
    tl = build_script()
    duration = tl.t
    print(f"timeline duration: {duration:.2f}s")
    page_imgs = {k: Image.open(p).convert("RGB") for k, p in PAGES}
    title_img = make_title_card()
    end_img = make_end_card()
    ripples = collect_ripples(tl)
    print(f"clicks: {len(ripples)}")
    n_frames = int(round(duration * FPS))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-f", "rawvideo", "-vcodec", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-an",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "18",
        "-movflags", "+faststart", str(OUT),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    switch_times = [ev[1] for ev in tl.events if ev[0] == "switch"]
    try:
        for i in range(n_frames):
            t = i / FPS
            key = page_at(tl, t)
            if key == "title":
                bg = title_img
                cx = cy = None
                clicking = False
            elif key == "end":
                bg = end_img
                cx = cy = None
                clicking = False
            else:
                bg = page_imgs[key]
                cx, cy, clicking, _ = _sample_cursor_clean(tl, t, key, "page")
            frame_bg = bg
            for st in switch_times:
                age = t - st
                if 0 <= age < 0.18:
                    flash = Image.new("RGB", (W, H), (255, 255, 255))
                    frame_bg = Image.blend(bg, flash, 0.22 * (1 - age / 0.18))
                    break
            if cx is None:
                out = frame_bg.convert("RGB")
            else:
                rgba = frame_bg.convert("RGBA")
                for rcx, rcy, t0 in ripples:
                    draw_ripple(rgba, rcx, rcy, t - t0)
                cur = CURSOR_CLICK if clicking else CURSOR
                rgba.alpha_composite(cur, (int(cx) - 2, int(cy) - 2))
                out = rgba.convert("RGB")
            proc.stdin.write(out.tobytes())
            if i % 90 == 0:
                print(f"  frame {i}/{n_frames} t={t:.1f}s key={key}")
        proc.stdin.close()
        stderr = proc.stderr.read().decode("utf-8", errors="replace")
        rc = proc.wait()
        if rc != 0:
            print(stderr[-4000:])
            raise SystemExit(rc)
    finally:
        if proc.stdin and not proc.stdin.closed:
            proc.stdin.close()
    print("wrote", OUT, OUT.stat().st_size)


if __name__ == "__main__":
    main()
