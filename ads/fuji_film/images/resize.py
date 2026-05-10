#!/usr/bin/env python

from PIL import Image

# Load image
img = Image.open("fuji_film.png").convert("RGBA")

# Target canvas size
target_w, target_h = 280, 240

# Resize source while preserving aspect ratio
img = img.resize((280, 210), Image.LANCZOS)

# Create new 280x240 canvas (transparent or use white)
#canvas = Image.new("RGBA", (target_w, target_h), (255, 255, 255, 0)) #transparent
#canvas = Image.new("RGBA", (target_w, target_h), (255, 255, 255, 0)) #white
canvas = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0)) #black

# Center image vertically
#y_offset = (target_h - 200) // 2  # = 20
y_offset = 5 #just a bit down

canvas.paste(img, (0, y_offset))

# Save result
canvas.save("fuji_film_280x240.png")

print("Created 280x240 image with centered 280x200 content.")
