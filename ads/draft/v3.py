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
    pip3 install spidev pillow --break-system-packages
    sudo apt install python3-gpiod
"""

import gpiod
import spidev
import time
from PIL import Image, ImageDraw, ImageFont
import os

# ── Config ────────────────────────────────────────────────────────────────────
GPIOCHIP    = "/dev/gpiochip1"
DC_LINE     = 44        # PIN_23
RST_LINE    = 43        # PIN_24

SPI_PORT    = 1
SPI_DEVICE  = 0
SPI_SPEED   = 40000000  # 40 MHz

WIDTH       = 240
HEIGHT      = 280
X_OFFSET    = 0
Y_OFFSET    = 20        # ST7789V3 240x280 requires this


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
        self._cmd(0x36); self._data([0x00]) # MADCTL

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
        pixels = img.tobytes()

        # Convert RGB888 → RGB565
        buf = []
        for i in range(0, len(pixels), 3):
            r, g, b = pixels[i], pixels[i+1], pixels[i+2]
            rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
            buf.append((rgb565 >> 8) & 0xFF)
            buf.append(rgb565 & 0xFF)

        self._set_window()
        self._dc.set_value(DC_LINE, gpiod.line.Value.ACTIVE)  # fix here

        chunk = 4096
        for i in range(0, len(buf), chunk):
            self._spi.writebytes2(buf[i:i+chunk])

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


def demo_animation(device, frames=500):
    print("  Animation...")
    x, y   = WIDTH // 2, HEIGHT // 2
    dx, dy = 4, 3
    radius = 12
    for _ in range(frames):
        x += dx; y += dy
        if x - radius < 0 or x + radius > WIDTH:  dx = -dx
        if y - radius < 0 or y + radius > HEIGHT: dy = -dy
        img  = Image.new("RGB", (WIDTH, HEIGHT), "black")
        draw = ImageDraw.Draw(img)
        draw.ellipse(
            [x-radius, y-radius, x+radius, y+radius],
            fill="orangered", outline="white"
        )
        device.display(img)
        time.sleep(0.00)


if __name__ == "__main__":
    print("ST7789V3 demo starting...")
    device = ST7789V3()

    print("  [1/5] Colour fills")
    demo_colour_fill(device)

    print("  [2/5] Text")
    demo_text(device)

    print("  [3/5] Shapes")
    demo_shapes(device)

    print("  [4/5] Gradient")
    demo_gradient(device)

    print("  [5/5] Animation")
    demo_animation(device)

    print("Done.")
    device.clear()
    device.close()
