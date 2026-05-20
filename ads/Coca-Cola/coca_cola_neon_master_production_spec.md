# Coca-Cola Neon Billboard — Master Production Specification

## Objective
Rebuild the entire animation natively at high resolution from scratch.

Do NOT:
- crop storyboard frames
- upscale raster thumbnails
- sharpen extracted frames
- perform stabilization passes
- use AI interpolation between storyboard panels

The storyboard is now ONLY a timing and choreography reference.

The final deliverable must be:
- native-resolution rendered animation
- locked-off geometry
- vector-clean signage
- authentic analog neon glow
- seamless looping
- consistent frame registration
- artifact-free

---

# Master Canvas

## Format
- Aspect ratio: 4:3
- Recommended render size:
  - 4096 × 3072
  - or minimum 2048 × 1536

## Camera
- perfectly straight-on orthographic view
- zero perspective distortion
- no environment
- pure black background
- billboard centered identically every frame

---

# Billboard Geometry

## Outer Border
- thick red neon tube
- always perfectly rectangular
- identical geometry in every frame
- subtle analog flicker only

## Red Neon Field
- vertical neon tubes
- evenly spaced
- saturated deep Coca-Cola red
- persistent illumination layer
- additive glow only
- NEVER blacked out behind white elements

## White Elements
- Enjoy
- Coca-Cola logo
- ribbon wave

All white neon must:
- be additive over the red field
- never erase or darken the red bars
- preserve red glow beneath

---

# Typography

## Enjoy
- small white neon
- centered above logo
- classic vintage styling

## Coca-Cola
- classic script
- correct proportions
- white neon tubing
- soft analog bloom
- no AI text distortions
- no extra strokes or artifacts

---

# Ribbon Wave

## Requirements
- authentic Coca-Cola ribbon sweep
- smooth translational movement
- NO morphing
- NO stretching
- NO retracting left
- NO shape changes

The wave must:
- enter from left
- travel right
- progressively exit right

Maintain consistent spacing beneath logo.

---

# Animation Timeline

## Frame 000
- full black

## Frame 001
- outer border only

## Frames 002–010
- red neon bars illuminate LEFT → RIGHT

## Frames 011–014
- Coca-Cola logo begins appearing
- Enjoy NOT visible yet

## Frames 015–021
- Enjoy fades in
- full logo illuminated
- red bars fully saturated

## Frames 022–030
- wave enters LEFT → RIGHT
- by Frame 030 full wave visible

## Frames 031–036
- wave progressively exits OFF RIGHT edge
- translational motion only

## Frames 037–044
- NO wave visible
- logo remains illuminated
- red bars remain illuminated

## Frames 045–050
- Coca-Cola logo extinguished
- red neon bars switch OFF LEFT → RIGHT
- last illuminated bar = far RIGHT

---

# Neon Behavior

## Desired Look
- realistic vintage analog neon
- tube bloom
- soft diffusion
- warm transformer glow
- subtle intensity variation
- slight tube inconsistency

Avoid:
- crisp vector-only rendering
- plastic CGI glow
- LED appearance
- harsh digital sharpening

---

# Registration Rules

Every frame must:
- align perfectly
- share identical border geometry
- share identical framing
- contain zero jitter
- contain zero drift

No scaling or repositioning between frames.

---

# Final Deliverables

## PNG Sequence
- lossless PNG
- sequential filenames
- native-resolution renders

## MP4
- H.264 or ProRes
- locked-off sequence
- 2× slower playback approved
- seamless looping

---

# Critical Corrections Learned During Iteration

These issues must NEVER recur:

- no black center masking
- no border drift
- no wave reappearing during shutdown
- no wave during frames 037–044
- no Enjoy during frames 011–012
- no artifacts above “ola”
- no non-4:3 panels
- no storyboard slicing
- no stabilization warping
- no oversharpened neon halos
- no frame interpolation artifacts

---

# Recommended Production Workflow

1. Build static billboard master artwork at native resolution.
2. Separate layers:
   - border
   - red bars
   - Enjoy
   - Coca-Cola logo
   - ribbon wave
3. Animate opacity and translation only.
4. Render directly to PNG sequence.
5. Assemble MP4 from true rendered frames.

This is the correct pipeline and should have been the starting point.

