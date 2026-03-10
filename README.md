# TXV — Text Vision Format

**TXV is an open plain-text format for animated character art with colour.**

It is the text-native equivalent of a GIF — every frame is a grid of real ASCII characters with per-cell hex colour data. You can open a `.txv` file in any text editor and read the frames directly. You can copy and paste the characters. You can author one by hand.

```
#txv v1
#size 90x52
#fps 24
#frames 120
#mode color
---
#frame 1
`.,--iil|/\oosa@W
`,,--iil|/\oosa@W
#colors
0,0,#c43a1b
1,0,#c43a1b
7,0,#00ff41
---
```

---

## Tools

| File | Description |
|------|-------------|
| `ascii-cam.html` | Live webcam → character art, with `.txv` recorder |
| `txv-converter.html` | Drag-and-drop MP4/MOV/WEBM → `.txv` (browser) |
| `txv-player.html` | Play back `.txv` files with controls |
| `txv-convert.py` | Fast command-line video → `.txv` converter (Python) |

All browser tools run entirely locally — no server, no upload.

---

## Quick Start

### Browser tools

```bash
cd txv
python3 -m http.server 8080
```

Then open `http://localhost:8080` in Chrome and pick a tool.

> Chrome requires a local server to access the webcam. The converter and player work fine from `file://` if you don't need the cam.

### Python converter

```bash
pip install opencv-python numpy
python3 txv-convert.py myvideo.mp4
```

This creates `myvideo.txv` in the same folder. Open it in `txv-player.html`.

**Options:**

```
python3 txv-convert.py input.mp4 [options]

  -o, --output PATH       Output file (default: input name + .txv)
  --cols N                Grid width in characters (default: 80)
  --fps N                 Frames per second to capture (default: 12)
  --duration N            Max seconds to convert (default: full video)
  --contrast N            Contrast multiplier 0.3–2.5 (default: 1.2)
  --mode MODE             color | bw | rainbow | edge (default: color)
  --author NAME           Embed author name in header
  --note TEXT             Embed a description in header
  -q, --quiet             No progress output
```

**Examples:**

```bash
# Basic conversion
python3 txv-convert.py clip.mp4

# High resolution, 24fps, first 10 seconds
python3 txv-convert.py clip.mp4 --cols 120 --fps 24 --duration 10

# Edge detection mode, boosted contrast
python3 txv-convert.py clip.mp4 --mode edge --contrast 1.8

# Black and white, wide grid
python3 txv-convert.py clip.mov --mode bw --cols 140

# With metadata
python3 txv-convert.py clip.mp4 --author yourname --note "first recording"
```

---

## Player Controls

| Key | Action |
|-----|--------|
| `Space` | Play / Pause |
| `← →` | Step one frame |
| `L` | Toggle loop |
| `R` | Toggle reverse |
| `P` | Toggle ping-pong |
| `G` | Toggle glitch effect |
| `T` | Cycle colour theme (RGB → Matrix → Amber → Ice → Void) |

---

## Format

See [`TXV_SPEC.md`](TXV_SPEC.md) for the full format specification.

The short version:

- Plain UTF-8 text, open in any editor
- Header declares size, fps, frame count, mode
- Each frame: `ROWS` lines of `COLS` characters, followed by a `#colors` block
- Colours stored as `col,row,#rrggbb` — only non-black cells, so dark frames are compact
- Sections separated by `---`

---

## Suggested repo structure

```
txv/
├── README.md
├── TXV_SPEC.md
├── ascii-cam.html
├── txv-player.html
├── txv-converter.html
└── txv-convert.py
```

---

## License

The TXV format and all reference tools are released into the public domain.
Do whatever you want with them.

---

*Created March 2026.*
