#!/usr/bin/env python3
"""
ST7789V3 Driver for Radxa Cubic A5E
------------------------------------
No luma, no RPi.GPIO — just spidev + gpiod + Pillow.

Wiring:
    VCC  → 3.3V
    GND  → GND
    SCL  → SPI1 CLK
    SDA  → SPI1 MOSI
    RES  → PIN_24 (gpiochip1 line 43)
    DC   → PIN_23 (gpiochip1 line 44)
    CS   → SPI1 CS0
    BLK  → 3.3V (hardwired)

Install deps:
    pip3 install opencv-python numpy spidev pillow --break-system-packages
    sudo apt install python3-gpiod 
    sudo apt install ffmpeg

    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo bash -
    sudo apt install -y nodejs
    node --version  # should say v20.x.x
"""

import gpiod
import spidev
import time
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from typing import List, Optional, Tuple
import os
import re
import queue
import threading
import subprocess
import numpy as np
import cv2
import shutil
from concurrent.futures import ThreadPoolExecutor


CLIPS_DIR  = Path("/home/radxa/clips")
LIST_FILE  = Path("/home/radxa/list.txt")
YTDLP      = Path("/home/radxa/yt-dlp_linux_aarch64")

EXTENSIONS = {".mkv", ".mp4", ".webm"}
TARGET_W, TARGET_H = 280, 240

SUFFIX     = f"_{TARGET_W}x{TARGET_H}"

# yt-dlp output template — saves as clips/Title [video_id].%(ext)s
YTDLP_TMPL = str(CLIPS_DIR / "%(title)s [%(id)s].%(ext)s")

YT_ID_RE = re.compile(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})")

# Lock registry: dst_path -> Lock, prevents double-conversion
_conversion_locks: dict = {}
_locks_mutex = threading.Lock()

def _get_conversion_lock(dst: Path) -> threading.Lock:
    with _locks_mutex:
        if dst not in _conversion_locks:
            _conversion_locks[dst] = threading.Lock()
        return _conversion_locks[dst]

def parse_list(path: Path) -> List[str]: ...
def already_downloaded(video_id: str) -> Optional[Path]: ...
def download(video_id: str) -> Optional[Path]: ...
def ensure_downloads(video_ids: List[str]) -> List[Path]: ...


# ── Config ────────────────────────────────────────────────────────────────────
GPIOCHIP    = "/dev/gpiochip1"
DC_LINE     = 44        # PIN_23
RST_LINE    = 43        # PIN_24

SPI_PORT    = 1
SPI_DEVICE  = 0
SPI_SPEED   = 40000000  # 40 MHz

WIDTH       = 280
HEIGHT      = 240
X_OFFSET    = 20
Y_OFFSET    = 0        # ST7789V3 240x280 requires this


# ── Driver ────────────────────────────────────────────────────────────────────
class ST7789V3:
    def __init__(self):
        # GPIO - gpiod v2 API
        self._dc  = gpiod.request_lines(
            GPIOCHIP,
            consumer="st7789_dc",
            config={DC_LINE:  gpiod.LineSettings(direction=gpiod.line.Direction.OUTPUT)}
        )
        self._rst = gpiod.request_lines(
            GPIOCHIP,
            consumer="st7789_rst",
            config={RST_LINE: gpiod.LineSettings(direction=gpiod.line.Direction.OUTPUT)}
        )

        # SPI
        self._spi = spidev.SpiDev()
        self._spi.open(SPI_PORT, SPI_DEVICE)
        self._spi.max_speed_hz = SPI_SPEED
        self._spi.mode = 0

        self._reset()
        self._init()

    def _reset(self):
        self._rst.set_value(RST_LINE, gpiod.line.Value.INACTIVE); time.sleep(0.1)
        self._rst.set_value(RST_LINE, gpiod.line.Value.ACTIVE);   time.sleep(0.2)

    def _cmd(self, c):
        self._dc.set_value(DC_LINE, gpiod.line.Value.INACTIVE)
        self._spi.xfer2([c])

    def _data(self, d):
        self._dc.set_value(DC_LINE, gpiod.line.Value.ACTIVE)
        self._spi.xfer2(d if isinstance(d, list) else [d])


    def _init(self):
        self._cmd(0x01); time.sleep(0.15)   # software reset
        self._cmd(0x11); time.sleep(0.12)   # sleep out

        self._cmd(0x3A); self._data([0x05]) # 16-bit RGB565
        # self._cmd(0x36); self._data([0x00]) # MADCTL
        self._cmd(0x36); self._data([0x60])  # 90 degrees clockwise
        # self._cmd(0x36); self._data([0xC0])  # 180 degrees
        # self._cmd(0x36); self._data([0xA0])  # 270 degrees

        self._cmd(0xB2); self._data([0x0C, 0x0C, 0x00, 0x33, 0x33])  # PORCTRL
        self._cmd(0xB7); self._data([0x35])                            # GCTRL
        self._cmd(0xBB); self._data([0x19])                            # VCOMS
        self._cmd(0xC0); self._data([0x2C])                            # LCMCTRL
        self._cmd(0xC2); self._data([0x01])                            # VDVVRHEN
        self._cmd(0xC3); self._data([0x12])                            # VRHS
        self._cmd(0xC4); self._data([0x20])                            # VDVS
        self._cmd(0xC6); self._data([0x0F])                            # FRCTRL2
        self._cmd(0xD0); self._data([0xA4, 0xA1])                      # PWCTRL1

        self._cmd(0xE0); self._data([                                  # PVGAMCTRL
            0xD0, 0x04, 0x0D, 0x11, 0x13, 0x2B,
            0x3F, 0x54, 0x4C, 0x18, 0x0D, 0x0B, 0x1F, 0x23])
        self._cmd(0xE1); self._data([                                  # NVGAMCTRL
            0xD0, 0x04, 0x0C, 0x11, 0x13, 0x2C,
            0x3F, 0x44, 0x51, 0x2F, 0x1F, 0x1F, 0x20, 0x23])

        self._cmd(0x21)                     # inversion on (V3 needs this)
        self._cmd(0x29)                     # display on

    def _set_window(self, x0=0, y0=0, x1=None, y1=None):
        x1 = x1 if x1 is not None else WIDTH  - 1
        y1 = y1 if y1 is not None else HEIGHT - 1
        xs = x0 + X_OFFSET
        xe = x1 + X_OFFSET
        ys = y0 + Y_OFFSET
        ye = y1 + Y_OFFSET
        self._cmd(0x2A); self._data([(xs>>8)&0xFF, xs&0xFF, (xe>>8)&0xFF, xe&0xFF])
        self._cmd(0x2B); self._data([(ys>>8)&0xFF, ys&0xFF, (ye>>8)&0xFF, ye&0xFF])
        self._cmd(0x2C)

    def display(self, image):
        """Send a PIL Image (RGB) to the display."""
        img = image.convert("RGB").resize((WIDTH, HEIGHT))
        arr = np.array(img, dtype=np.uint8)

        r = arr[:,:,0].astype(np.uint16)
        g = arr[:,:,1].astype(np.uint16)
        b = arr[:,:,2].astype(np.uint16)
        rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

        # Correct byte order for ST7789 big-endian SPI
        buf = np.empty(rgb565.size * 2, dtype=np.uint8)
        buf[0::2] = (rgb565 >> 8).flatten()    # high byte first
        buf[1::2] = (rgb565 & 0xFF).flatten()  # low byte second

        self._set_window()
        self._dc.set_value(DC_LINE, gpiod.line.Value.ACTIVE)

        mv = memoryview(buf)
        chunk = 4096
        for i in range(0, len(buf), chunk):
            self._spi.writebytes2(mv[i:i+chunk])

    def display_region(self, image, x0, y0):
        """Send a partial image to the display at position (x0, y0)."""
        w, h = image.size
        x1 = x0 + w - 1
        y1 = y0 + h - 1

        arr = np.array(image.convert("RGB"), dtype=np.uint8)
        r = arr[:,:,0].astype(np.uint16)
        g = arr[:,:,1].astype(np.uint16)
        b = arr[:,:,2].astype(np.uint16)
        rgb565  = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        buf = np.empty(rgb565.size * 2, dtype=np.uint8)
        buf[0::2] = (rgb565 >> 8).flatten()
        buf[1::2] = (rgb565 & 0xFF).flatten()

        # Set window to dirty rect only
        xs = x0 + X_OFFSET; xe = x1 + X_OFFSET
        ys = y0 + Y_OFFSET; ye = y1 + Y_OFFSET
        self._cmd(0x2A); self._data([(xs>>8)&0xFF, xs&0xFF, (xe>>8)&0xFF, xe&0xFF])
        self._cmd(0x2B); self._data([(ys>>8)&0xFF, ys&0xFF, (ye>>8)&0xFF, ye&0xFF])
        self._cmd(0x2C)

        self._dc.set_value(DC_LINE, gpiod.line.Value.ACTIVE)
        chunk = 4096
        mv = memoryview(buf)
        for i in range(0, len(buf), chunk):
            self._spi.writebytes2(mv[i:i+chunk])

    def fill(self, color):
        """Fill screen with a solid RGB tuple e.g. (255, 0, 0)."""
        img = Image.new("RGB", (WIDTH, HEIGHT), color)
        self.display(img)

    def clear(self):
        self.fill((0, 0, 0))

    def close(self):
        self.clear()
        self._spi.close()
        self._dc.release()
        self._rst.release()

# ── Downloads ─────────────────────────────────────────────────────────────────
def parse_list(path: Path) -> List[str]:
    """
    Return YouTube video IDs from list.txt.
    Skips blank lines and lines whose first non-space char is #.
    Commented-out URLs (e.g. #https://...) are also skipped.
    """
    ids: List[str] = []
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = YT_ID_RE.search(line)
        if m:
            ids.append(m.group(1))
        else:
            print(f"  [warn] no video ID found in: {line}")
    return ids

def already_downloaded(video_id: str) -> Optional[Path]:
    """Return the existing file path if this video_id is already in clips/.
    Matches both plain '<id>.ext' and 'Title [id].ext' filename formats.
    Prefers the original (non-sized) file over a _280x240 copy.
    """
    original = None
    sized = None
    for p in CLIPS_DIR.iterdir():
        if p.suffix.lower() not in EXTENSIONS:
            continue
        stem = p.stem
        is_sized = stem.endswith(SUFFIX)
        base_stem = stem[: -len(SUFFIX)] if is_sized else stem
        if base_stem == video_id or base_stem.endswith(f"[{video_id}]"):
            if is_sized:
                sized = p
            else:
                original = p
    return original or sized

def download(video_id: str) -> Optional[Path]:
    """Run yt-dlp to download a single video. Returns the downloaded path or None."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    print(f"  -> downloading {video_id}  ({url})")

    if not YTDLP.exists():
        print(f"  x yt-dlp binary not found at {YTDLP}")
        return None

    import shutil as _shutil
    node_bin = _shutil.which("node") or _shutil.which("nodejs") or "node"

    cmd = [
        str(YTDLP),
        "--no-playlist",
        "--js-runtimes", f"node:{node_bin}",
        "--cookies", str(Path.home() / "cookies.txt"),
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "-o", YTDLP_TMPL,
        url,
    ]
    result = subprocess.run(cmd, stderr=subprocess.PIPE)
    if result.returncode != 0:
        print(f"  x yt-dlp error:\n{result.stderr.decode()}")
        return None

    path = already_downloaded(video_id)
    if path:
        print(f"  + saved {path.name}")
    else:
        print(f"  x download finished but file not found for {video_id}")
    return path


def ensure_downloads(video_ids: List[str]) -> List[Path]:
    """Guarantee every video_id has a local file. Returns list of local paths."""
    paths: List[Path] = []
    for vid in video_ids:
        existing = already_downloaded(vid)
        if existing:
            print(f"[skip] {vid} already downloaded -> {existing.name}")
            paths.append(existing)
        else:
            p = download(vid)
            if p:
                paths.append(p)
    return paths

# ── Helpers ───────────────────────────────────────────────────────────────────

def is_sized_copy(path: Path) -> bool:
    """True if the filename already carries the _280x240 suffix."""
    return path.stem.endswith(SUFFIX)


def sized_path(path: Path) -> Path:
    """Return the expected _280x240 path for a given source file."""
    return path.with_name(path.stem + SUFFIX + path.suffix)


def probe_dimensions(path: Path) -> Optional[Tuple[int, int]]:
    """Return (width, height) via ffprobe, or None on failure."""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=p=0",
        str(path),
    ]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True).strip()
        w, h = out.split(",")
        return int(w), int(h)
    except Exception:
        return None

def convert_to_280x240(src: Path, dst: Path) -> bool:
    """
    Convert src to dst at 280x240, preserving aspect ratio with black padding.
    Writes to a .tmp file first, renames atomically on success.
    Uses a per-dst lock to prevent duplicate conversions.
    """
    lock = _get_conversion_lock(dst)
    if not lock.acquire(blocking=False):
        # Another thread is already converting this file — wait for it
        lock.acquire()
        lock.release()
        return dst.exists()

    try:
        if dst.exists():
            return True  # completed while we waited

        tmp = dst.with_suffix(".tmp" + dst.suffix)
        print(f"  -> converting {src.name} -> {dst.name}")
        cmd = [
            "ffmpeg", "-y",
            "-i", str(src),
            "-vf", f"scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=decrease,"
                   f"pad={TARGET_W}:{TARGET_H}:(ow-iw)/2:(oh-ih)/2",
            "-r", "24",
            str(tmp),
        ]
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        if result.returncode != 0:
            print(f"  x ffmpeg error:\n{result.stderr.decode()}")
            tmp.unlink(missing_ok=True)
            return False

        tmp.rename(dst)
        print(f"  + saved {dst.name}")
        return True
    finally:
        lock.release()

def _convert_and_enqueue(src: Path, dst: Path, q: "queue.Queue[Optional[Path]]") -> None:
    """Worker: convert src, push dst to queue (or None on failure)."""
    ok = convert_to_280x240(src, dst)
    q.put(dst if ok else None)

def schedule_conversions(sources: List[Path]) -> "queue.Queue[Optional[Path]]":
    """
    For each source:
      - already a sized copy → put directly on queue
      - already converted    → put directly on queue
      - needs conversion     → submit to thread pool, enqueues when done
    Returns a queue that will receive exactly len(sources) items (Path or None).
    """
    q: "queue.Queue[Optional[Path]]" = queue.Queue()
    executor = ThreadPoolExecutor(max_workers=2)

    for src in sources:
        if is_sized_copy(src):
            q.put(src)
            continue

        dst = sized_path(src)

        if dst.exists():
            print(f"[skip] {dst.name} already exists")
            q.put(dst)
            continue

        dims = probe_dimensions(src)
        if dims == (TARGET_W, TARGET_H):
            print(f"[skip] {src.name} is already {TARGET_W}x{TARGET_H}, copying")
            shutil.copy2(src, dst)
            q.put(dst)
            continue

        # submit background conversion
        print(f"  [queued] {src.name}")
        executor.submit(_convert_and_enqueue, src, dst, q)

    executor.shutdown(wait=False)
    return q

# ── Demo ──────────────────────────────────────────────────────────────────────
def load_font(size=20):
    for path in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

def demo_colour_fill(device):
    print("  Colour fills...")
    for colour in [(255,0,0), (0,255,0), (0,0,255), (255,255,255), (0,0,0)]:
        device.fill(colour)
        time.sleep(0.4)

def demo_text(device):
    print("  Text...")
    font_large = load_font(28)
    font_small = load_font(16)
    img  = Image.new("RGB", (WIDTH, HEIGHT), "black")
    draw = ImageDraw.Draw(img)
    draw.text((10, 10),  "ST7789V3",        font=font_large, fill="cyan")
    draw.text((10, 50),  "Radxa Cubic A5E", font=font_small, fill="white")
    draw.text((10, 75),  "Linux / Debian",  font=font_small, fill="yellow")
    draw.text((10, 100), "No luma needed!", font=font_small, fill="lightgreen")
    device.display(img)
    time.sleep(2)

def demo_shapes(device):
    print("  Shapes...")
    img  = Image.new("RGB", (WIDTH, HEIGHT), "black")
    draw = ImageDraw.Draw(img)
    draw.rectangle([10, 10, 100, 60],   outline="red",     fill="darkred")
    draw.rectangle([130, 10, 230, 60],  outline="cyan",    fill=None)
    draw.ellipse(  [10, 80, 110, 180],  outline="yellow",  fill="goldenrod")
    draw.line(     [130, 80, 230, 180], fill="magenta",    width=3)
    draw.polygon(  [(120,230),(70,140),(170,140)], outline="white", fill="teal")
    for x in range(10, 230, 15):
        draw.ellipse([x, 200, x+6, 206], fill="lime")
    device.display(img)
    time.sleep(2)

def demo_image(device, path="test_image.png"):
    if os.path.exists(path):
        img = Image.open(path).convert("RGB").resize((WIDTH, HEIGHT))
    else:
        # Generate a simple colour-gradient test pattern
        img = Image.new("RGB", (WIDTH, HEIGHT))
        d = ImageDraw.Draw(img)
        for x in range(WIDTH):
            r = int(255 * x / WIDTH)
            for y in range(HEIGHT):
                g = int(255 * y / HEIGHT)
                b = 128
                d.point((x, y), fill=(r, g, b))
        d.text((10, 10), "No image file found", font=font_small, fill="white")
        d.text((10, 30), "Showing gradient",    font=font_small, fill="white")

    device.display(img)
    time.sleep(20)

def demo_gradient(device):
    print("  Gradient...")
    img = Image.new("RGB", (WIDTH, HEIGHT))
    d   = ImageDraw.Draw(img)
    for x in range(WIDTH):
        r = int(255 * x / WIDTH)
        for y in range(HEIGHT):
            g = int(255 * y / HEIGHT)
            d.point((x, y), fill=(r, g, 128))
    device.display(img)
    time.sleep(2)

def demo_animation(device, frames=3000, fps=120):
    x, y   = WIDTH // 2, HEIGHT // 2
    dx, dy = 6, 5
    radius = 15
    frame_time = 1.0 / fps    # seconds per frame

    bg = Image.new("RGB", (WIDTH, HEIGHT), "black")
    device.display(bg)

    prev_rect = None

    for _ in range(frames):
        t_start = time.monotonic()

        x += dx; y += dy
        if x - radius < 0 or x + radius > WIDTH:  dx = -dx
        if y - radius < 0 or y + radius > HEIGHT: dy = -dy

        new_rect = (
            max(0, x - radius - 1),
            max(0, y - radius - 1),
            min(WIDTH  - 1, x + radius + 1),
            min(HEIGHT - 1, y + radius + 1),
        )

        dirty = (
            min(prev_rect[0], new_rect[0]),
            min(prev_rect[1], new_rect[1]),
            max(prev_rect[2], new_rect[2]),
            max(prev_rect[3], new_rect[3]),
        ) if prev_rect else new_rect

        patch = bg.crop(dirty).copy()
        draw  = ImageDraw.Draw(patch)
        ox, oy = dirty[0], dirty[1]
        draw.ellipse(
            [x - radius - ox, y - radius - oy,
             x + radius - ox, y + radius - oy],
            fill="orangered", outline="white"
        )
        device.display_region(patch, dirty[0], dirty[1])
        prev_rect = new_rect

        # Sleep only the remaining time in this frame
        elapsed = time.monotonic() - t_start
        remaining = frame_time - elapsed
        if remaining > 0:
            time.sleep(remaining)

# ── not Demos ─────────────────────────────────────────────────────────────────
def play_video_old(device, path, fps=24):
    # ffmpeg -i input.mp4 -vf "scale=240:280" -r 24 output.mp4
    # play_video(device, "/root/myvideo.mp4", fps=24)
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        print(f"Cannot open {path}")
        return

    frame_time = 1.0 / fps

    while True:
        t_start = time.monotonic()

        ret, frame = cap.read()
        if not ret:
            break  # end of video

        # OpenCV uses BGR, convert to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)

        device.display(img)  # handles resize + RGB565 conversion

        elapsed = time.monotonic() - t_start
        remaining = frame_time - elapsed
        if remaining > 0:
            time.sleep(remaining)

    cap.release()

def play_video(device, path: Path, fps: int = 24):
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        print(f"Cannot open {path}")
        return
    frame_time = 1.0 / fps
    while True:
        t_start = time.monotonic()
        ret, frame = cap.read()
        if not ret:
            break
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)
        device.display(img)
        elapsed = time.monotonic() - t_start
        remaining = frame_time - elapsed
        if remaining > 0:
            time.sleep(remaining)
    cap.release()

def play_raw(device, path, fps=15):
    # ffmpeg -i input.mp4 -vf "scale=240:280" -r 15 -f rawvideo -pix_fmt rgb565be output.raw
    frame_size = WIDTH * HEIGHT * 2  # RGB565 = 2 bytes per pixel
    frame_time = 1.0 / fps

    with open(path, "rb") as f:
        while True:
            t_start  = time.monotonic()
            buf = f.read(frame_size)
            if len(buf) < frame_size:
                break

            device._set_window()
            device._dc.set_value(DC_LINE, gpiod.line.Value.ACTIVE)
            mv = memoryview(buf)
            for i in range(0, len(buf), 4096):
                device._spi.writebytes2(mv[i:i+4096])

            elapsed = time.monotonic() - t_start
            remaining = frame_time - elapsed
            if remaining > 0:
                time.sleep(remaining)

def fuji_image_sequence(device):
    frame_delay = 1 / 27  # frames 01-27 spread across 1 second

    def load_and_display(path, duration):
        if os.path.exists(path):
            img = Image.open(path).convert("RGB").resize((WIDTH, HEIGHT))
            device.display(img)
            time.sleep(duration)

    # Frame 00 — hold for 3 seconds
    load_and_display("images/fuji_film_00_280x240.png", 3)

    # Frames 01–27 — forward, total 1 second
    for i in range(1, 28):
        load_and_display(f"images/fuji_film_{i:02d}_280x240.png", frame_delay)

    # Frame 28 — hold for 3 seconds
    load_and_display("images/fuji_film_28_280x240.png", 3)

    # Frames 27–01 — reverse, total 1 second
    for i in range(27, 0, -1):
        load_and_display(f"images/fuji_film_{i:02d}_280x240.png", frame_delay)


# ── Main ──────────────────────────────────────────────────────────────────────
def collect_source_videos() -> List[Path]:
    """All video files in clips/ that are NOT already sized copies."""
    return sorted(
        p for p in CLIPS_DIR.iterdir()
        if p.suffix.lower() in EXTENSIONS and not is_sized_copy(p)
    )

def my_videos(device):
    CLIPS_DIR.mkdir(exist_ok=True)

    # --- Step 1: parse list.txt ---
    if LIST_FILE.exists():
        print(f"=== Step 1: parsing {LIST_FILE} ===")
        video_ids = parse_list(LIST_FILE)
        print(f"  {len(video_ids)} URL(s) found\n")

        # --- Step 2: download missing ---
        print("=== Step 2: checking / downloading clips ===")
        ensure_downloads(video_ids)
        print()
    else:
        print(f"[info] {LIST_FILE} not found -- skipping download step\n")

    # --- Step 3: schedule conversions in background ---
    print(f"=== Step 3: scanning {CLIPS_DIR} for unconverted files ===")
    sources = collect_source_videos()

    if not sources:
        raise SystemExit("No source video files found in clips/")

    print(f"  {len(sources)} source file(s):\n  " +
          "\n  ".join(p.name for p in sources) + "\n")

    play_queue = schedule_conversions(sources)

    # --- Step 4: play as files become ready ---
    print(f"=== Step 4: playing {len(sources)} video(s) ===")

    ready: List[Path] = []
    remaining = len(sources)
 
    while remaining > 0:
        # check if next clip is ready without blocking
        try:
            path = play_queue.get_nowait()
            remaining -= 1
            if path is None:
                print("  x a conversion failed, skipping slot")
            else:
                print(f"\n> {path.name} [new]")
                ready.append(path)
        except queue.Empty:
            pass
 
        if ready:
            # play the most recently added ready clip (or loop back)
            path = ready[len(ready) - 1] if len(ready) == 1 else ready[0]
            # rotate ready list so we cycle through what's available
            ready.append(ready.pop(0))
            print(f"\n> {path.name}")
            play_video(device, path, fps=24)
        else:
            # nothing ready yet — poll briefly
            time.sleep(0.5)

if __name__ == "__main__":
    print("ST7789V3 demo starting...")
    device = ST7789V3()

    print("  [1/7] Colour fills")
    #demo_colour_fill(device)

    print("  [2/7] Text")
    #demo_text(device)

    print("  [3/7] Shapes")
    #demo_shapes(device)

    print("  [4/7] Images")
    #demo_image(device)

    print("  [5/7] Gradient")
    #demo_gradient(device)

    print("  [6/7] Animation")
    #demo_animation(device)

    print("  [7/7] Play Video")
    #play_video(device, '/home/radxa/fujifilm3.mkv')

    print("  [7/7] Fuji Image Sequence")
    while True:
        my_videos(device)
        fuji_image_sequence(device)

    print("Done.")
    device.clear()
    device.close()
