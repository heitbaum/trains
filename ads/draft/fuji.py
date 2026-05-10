from PIL import Image, ImageEnhance, ImageFilter
import numpy as np
import os

# Load your image
img = Image.open("input.png").convert("RGB")

# Resize to target
img = img.resize((240, 280), Image.LANCZOS)

os.makedirs("frames", exist_ok=True)

frames = []

for i in range(24):
    frame = img.copy()

    # Strong flicker (brightness pulsing)
    brightness = 1.0 + (0.25 * np.sin(i * 0.8))
    frame = ImageEnhance.Brightness(frame).enhance(brightness)

    # Contrast boost (crisp look)
    frame = ImageEnhance.Contrast(frame).enhance(1.4)

    # Occasional glitch shift
    if i % 5 == 0:
        arr = np.array(frame)
        shift = np.roll(arr, shift=3, axis=1)
        arr[:, :, 0] = shift[:, :, 0]  # red channel glitch
        frame = Image.fromarray(arr)

    # Slight sharpening
    frame = frame.filter(ImageFilter.SHARPEN)

    frame.save(f"frames/frame_{i:03d}.png")
    frames.append(frame)

# Save GIF
frames[0].save(
    "fuji_anim.gif",
    save_all=True,
    append_images=frames[1:],
    duration=60,
    loop=0
)

# Create sprite sheet (6x4 grid)
cols, rows = 6, 4
sheet = Image.new("RGB", (240 * cols, 280 * rows))

for idx, frame in enumerate(frames):
    x = (idx % cols) * 240
    y = (idx // cols) * 280
    sheet.paste(frame, (x, y))

sheet.save("fuji_spritesheet.png")
