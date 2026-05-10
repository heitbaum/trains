# description = "Enable spidev on SPI1 on pin 36(CLK), 40(MOSI), 38(MISO), 12(CS0)";
# st7789v3

# Pin  1 - VCC - Yellow
# Pin  6 - GND - Black
# Pin 12 - CS
# Pin 17 - BLK - Backlight - Yellow
# Pin 23 - DC
# Pin 24 - RES - Reset
#   Low  (0): Command (RS/A0 pin).
#   High (1): Display data (Pixel content).
# Pin 36 - SCL
# Pin 40 - SDA

#In rsetup (when looking at the GPIO output) you will see that it shows E (error) on the pins that are “taken” for the SPI.

import spidev
import time
import RPi.GPIO as GPIO # Or similar Linux GPIO library

# Display dimensions
WIDTH = 240
HEIGHT = 280 # or 320

# Pins
DC = 32
RST = 31

# SPI setup
spi = spidev.SpiDev()
spi.open(0, 0) # bus 0, device 0
spi.max_speed_hz = 40000000
spi.mode = 0b11 # Mode 3 is common for ST7789

def send_cmd(cmd):
    GPIO.output(DC, GPIO.LOW)
    spi.xfer2([cmd])

def send_data(data):
    GPIO.output(DC, GPIO.HIGH)
    spi.xfer2([data])

def init_display():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(DC, GPIO.OUT)
    GPIO.setup(RST, GPIO.OUT)

    # Reset
    GPIO.output(RST, GPIO.HIGH)
    time.sleep(0.01)
    GPIO.output(RST, GPIO.LOW)
    time.sleep(0.1)
    GPIO.output(RST, GPIO.HIGH)
    time.sleep(0.1)

    # Init commands
    send_cmd(0x01) # Software reset
    time.sleep(0.15)
    send_cmd(0x11) # Sleep out
    time.sleep(0.12)
    send_cmd(0x3A) # Color mode
    send_data(0x55) # 16-bit
    send_cmd(0x36) # Memory data access control
    send_data(0x00) # RGB order
    send_cmd(0x29) # Display on
    time.sleep(0.1)

# Usage
init_display()
# Send pixel data using send_data or spi.xfer2(...)

