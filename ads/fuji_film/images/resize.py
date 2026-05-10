#!/usr/bin/env python

from PIL import Image

# Load the image
img = Image.open("fuji_film.png")  # replace with your filename

# Resize to 280x240
resized = img.resize((280, 220), Image.LANCZOS)

# Save the result
resized.save("fuji_film_280x240.png")

print("Image resized to 280x240")
