#!/usr/bin/env python

from PIL import Image
import glob
import os

# Find all files matching fuji_film_??.png
files = glob.glob("fuji_film_??.png")

# Target canvas size
target_w, target_h = 280, 240

for file in files:
    # Load image
    img = Image.open(file).convert("RGBA")

    # Resize source image to 280x210
    img = img.resize((280, 210), Image.LANCZOS)

    # Create 280x240 canvas (transparent background)
    #canvas = Image.new("RGBA", (target_w, target_h), (255, 255, 255, 0)) #transparent
    #canvas = Image.new("RGBA", (target_w, target_h), (255, 255, 255, 0)) #white
    canvas = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0)) #black

    # Center vertically
    #y_offset = (target_h - 200) // 2
    y_offset = 5 #just a bit down

    # Paste resized image
    canvas.paste(img, (0, y_offset))

    # Output filename
    base, ext = os.path.splitext(file)
    output_file = f"{base}_280x240.png"

    # Save result
    canvas.save(output_file)

    print(f"Saved: {output_file}")

print("Done.")
