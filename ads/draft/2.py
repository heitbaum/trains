#!/usr/bin/env python3
from periphery import GPIO
import spidev, time

GPIOCHIP = "/dev/gpiochip1"
DC_LINE  = 44
RST_LINE = 43

dc  = GPIO(GPIOCHIP, DC_LINE,  "out")
rst = GPIO(GPIOCHIP, RST_LINE, "out")

# Hardware reset
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

# Minimal ST7789 init
cmd(0x01)          # Software reset
time.sleep(0.15)
cmd(0x11)          # Sleep out
time.sleep(0.12)
cmd(0x29)          # Display on

# Fill screen red
cmd(0x2A); data([0x00, 0x00, 0x00, 0xEF])          # column 0-239
cmd(0x2B); data([0x00, 0x00, 0x01, 0x13])          # row 0-279
cmd(0x2C)                                           # write pixels
dc.write(True)
for _ in range(240 * 280):
    spi.xfer2([0xF8, 0x00])                         # red in RGB565

print("Done - screen should be red")
spi.close()
dc.close()
rst.close()
