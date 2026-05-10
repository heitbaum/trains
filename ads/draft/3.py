#!/usr/bin/env python3
from periphery import GPIO
import spidev, time

GPIOCHIP = "/dev/gpiochip1"
DC_LINE  = 44
RST_LINE = 43

dc  = GPIO(GPIOCHIP, DC_LINE,  "out")
rst = GPIO(GPIOCHIP, RST_LINE, "out")

rst.write(False); time.sleep(0.1)
rst.write(True);  time.sleep(0.2)

spi = spidev.SpiDev()
spi.open(1, 0)
spi.max_speed_hz = 4000000
spi.mode = 0

def cmd(c):
    dc.write(False)
    spi.xfer2([c])

def data(d):
    dc.write(True)
    spi.xfer2(d if isinstance(d, list) else [d])

# Full ST7789V3 init
cmd(0x01); time.sleep(0.15)   # software reset
cmd(0x11); time.sleep(0.12)   # sleep out
cmd(0x3A); data([0x05])       # 16-bit RGB565
cmd(0x36); data([0x00])       # MADCTL
cmd(0x21)                     # inversion on (V3 needs this)

# Try different offsets here
Y_OFFSET = 20   # try 0, 20, 35, 40

cmd(0x2A); data([0x00, 0x00, 0x00, 0xEF])                              # CASET: cols 0-239

# RASET with offset
y_start = Y_OFFSET
y_end   = Y_OFFSET + 279
cmd(0x2B); data([
    (y_start >> 8) & 0xFF, y_start & 0xFF,
    (y_end   >> 8) & 0xFF, y_end   & 0xFF,
])

cmd(0x29)                     # display on
cmd(0x2C)                     # write pixels
dc.write(True)

# Fill solid red in RGB565 (0xF800 = red)
line = [0xFF, 0x00] * 240
for _ in range(280):
    spi.writebytes2(line)

print("Done")
spi.close()
dc.close()
rst.close()
