#!/usr/bin/env python3
"""
ST7789V3 Full Demo - Radxa Cubic A5E (Linux/Debian)
Dependencies:
    pip install python-periphery luma.lcd pillow
    pip3 install spidev
    sudo apt install python3-libgpiod gpiod
    sudo apt install python3-dev
    gpioinfo /dev/gpiochip1 | grep -E "line 257|line 268"
"""

#!/usr/bin/env python3

# ── Mock RPi.GPIO before ANY luma imports ────────────────────────────────────
import sys
from unittest.mock import MagicMock
sys.modules['RPi']      = MagicMock()
sys.modules['RPi.GPIO'] = MagicMock()

from luma.lcd.device import st7789
from luma.core.interface.serial import spi
from luma.core.render import canvas
from PIL import Image, ImageDraw, ImageFont
from periphery import GPIO
import time
import os

# ── Pin config ────────────────────────────────────────────────────────────────
# Adjust these to match your wiring on the A5E GPIO header
SPI_PORT     = 1       # /dev/spidev1.x
SPI_DEVICE   = 0       # Chip select: /dev/spidev1.0
SPI_SPEED    = 40000000  # 40 MHz
#SPI_SPEED    = 4000000  # 4 MHz
BACKLIGHT    = -1      # Backlight GPIO (or -1 if hardwired)

WIDTH        = 240
HEIGHT       = 280

# ── Pin definitions ───────────────────────────────────────────────────────────
# PIN_31 = PI12 → gpiochip1, line 268  (use as DC)
# PIN_32 = PI1  → gpiochip1, line 257  (use as RST)

GPIOCHIP = "/dev/gpiochip1"
DC_LINE  = 44   # PIN_23 # Data/Command GPIO (BCM or sysfs number)
RST_LINE = 43   # PIN_24 # Reset GPIO

# ── periphery shim for luma.lcd ───────────────────────────────────────────────
class PeripheryGPIOShim:
    BCM      = 11
    OUT      = 0
    IN       = 1
    HIGH     = 1
    LOW      = 0
    RISING   = 31
    FALLING  = 32
    BOTH     = 33
    PUD_UP   = 22
    PUD_DOWN = 21

    def __init__(self, chip):
        self.chip   = chip
        self._lines = {}

    def setmode(self, mode):       pass
    def setwarnings(self, flag):   pass

    def setup(self, line, mode, pull_up_down=None, initial=None):
        direction = "out" if mode == self.OUT else "in"
        self._lines[line] = GPIO(self.chip, line, direction)

    def output(self, line, value):
        self._lines[line].write(bool(value))

    def input(self, line):
        return self._lines[line].read()

    def cleanup(self):
        for g in self._lines.values():
            g.close()
        self._lines.clear()

gpio = PeripheryGPIOShim(GPIOCHIP)

# ── SPI + ST7789V3 init ───────────────────────────────────────────────────────
serial = spi(
    port=SPI_PORT,
    device=SPI_DEVICE,
    gpio=gpio,
    gpio_DC=DC_LINE,
    gpio_RST=RST_LINE,
    bus_speed_hz=SPI_SPEED,
    reset_hold_time=0.5,
    reset_release_time=0.5,
    spi_mode=3,        # try 0 if 3 doesn't work
)

device = st7789(
    serial,
    width=WIDTH,
    height=HEIGHT,
    rotate=0,
    #bgr=False,
    #h_offset=0,
    #v_offset=0,
)

# Fix for ST7789V3 240x280
#device.command(0x3A, 0x05)  # 16-bit color
device.command(0x36, 0x00)  # MADCTL reset
device.command(0x29)        # display on again

# ── Helper: try to load a font, fall back to default ─────────────────────────
def load_font(size=20):
    for path in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

font_large = load_font(28)
font_small = load_font(16)

# ─────────────────────────────────────────────────────────────────────────────
# 1. INIT SCREEN – solid colour fill
# ─────────────────────────────────────────────────────────────────────────────
def demo_colour_fill():
    colours = ["red", "green", "blue", "white", "black"]
    for colour in colours:
        with canvas(device) as draw:
            draw.rectangle(device.bounding_box, outline=colour, fill=colour)
        time.sleep(0.4)

# ─────────────────────────────────────────────────────────────────────────────
# 2. TEXT
# ─────────────────────────────────────────────────────────────────────────────
def demo_text():
    with canvas(device) as draw:
        draw.rectangle(device.bounding_box, fill="black")
        draw.text((10, 10),  "ST7789V3 Demo",  font=font_large, fill="cyan")
        draw.text((10, 50),  "Radxa Cubic A5E", font=font_small, fill="white")
        draw.text((10, 75),  "Linux / Debian",  font=font_small, fill="yellow")
        draw.text((10, 100), "luma.lcd + Pillow",font=font_small, fill="lightgreen")
    time.sleep(2)

# ─────────────────────────────────────────────────────────────────────────────
# 3. SHAPES
# ─────────────────────────────────────────────────────────────────────────────
def demo_shapes():
    with canvas(device) as draw:
        draw.rectangle(device.bounding_box, fill="black")

        # Filled rectangle
        draw.rectangle([10, 10, 100, 60], outline="red", fill="darkred")

        # Outlined rectangle
        draw.rectangle([130, 10, 230, 60], outline="cyan", fill=None)

        # Circle (ellipse)
        draw.ellipse([10, 80, 110, 180], outline="yellow", fill="goldenrod")

        # Line
        draw.line([130, 80, 230, 180], fill="magenta", width=3)

        # Triangle (polygon)
        draw.polygon([(120, 230), (70, 140), (170, 140)], outline="white", fill="teal")

        # Small dots
        for x in range(10, 230, 15):
            draw.ellipse([x, 200, x+6, 206], fill="lime")

    time.sleep(2)

# ─────────────────────────────────────────────────────────────────────────────
# 4. IMAGE – generate a test pattern if no file is present
# ─────────────────────────────────────────────────────────────────────────────
def demo_image(path="test_image.png"):
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
    time.sleep(3)

# ─────────────────────────────────────────────────────────────────────────────
# 5. ANIMATION – bouncing ball
# ─────────────────────────────────────────────────────────────────────────────
def demo_animation(frames=80):
    x, y   = WIDTH // 2, HEIGHT // 2
    dx, dy = 4, 3
    radius = 15

    for _ in range(frames):
        x += dx
        y += dy
        if x - radius < 0 or x + radius > WIDTH:
            dx = -dx
        if y - radius < 0 or y + radius > HEIGHT:
            dy = -dy

        with canvas(device) as draw:
            draw.rectangle(device.bounding_box, fill="black")
            draw.ellipse(
                [x - radius, y - radius, x + radius, y + radius],
                fill="orangered", outline="white"
            )
        time.sleep(0.02)

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("ST7789V3 full demo starting...")

    #print("  [1/5] Colour fills")
    #demo_colour_fill()

    #print("  [2/5] Text")
    #demo_text()

    #print("  [3/5] Shapes")
    #demo_shapes()

    print("  [4/5] Image")
    demo_image()

    #print("  [5/5] Animation")
    #demo_animation()

    print("Done.")
    #with canvas(device) as draw:
    #    draw.rectangle(device.bounding_box, fill="black")
