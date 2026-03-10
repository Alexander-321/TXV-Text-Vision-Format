# TXV Format Specification
### Version 1.0

---

## What is TXV?

TXV (Text Vision) is an open, plain-text file format for storing animated sequences of character-art frames with per-character colour data. It is the text-native equivalent of a GIF — human-readable, copy-pasteable, renderable in any browser, and writable by any text editor.

A `.txv` file is valid UTF-8 plain text. Every frame is a grid of printable ASCII characters. Colour is stored as hex values alongside the character data. The format is designed to be:

- **Human-readable** — open it in any text editor and you can read the frame data directly
- **Writable by hand** — a valid `.txv` can be authored without any tools
- **Self-describing** — the header contains everything a player needs to render it correctly
- **Compact by design** — only non-black cells store colour data, whitespace is omitted

---

## File Extension

`.txv`

Suggested MIME type: `text/x-txv`

---

## Structure Overview

A `.txv` file has two parts:

1. A **file header** — metadata about the whole file
2. One or more **frame blocks** — the actual character and colour data

```
<file header>
---
<frame block>
---
<frame block>
---
...
```

Each section is separated by a line containing exactly `---`.

---

## File Header

The header appears at the top of the file before the first `---` separator. Each line is a key-value pair in the format:

```
#key value
```

### Required fields

| Field      | Description                                      | Example         |
|------------|--------------------------------------------------|-----------------|
| `#txv`     | Format identifier and version. Must be first.    | `#txv v1`       |
| `#size`    | Grid dimensions as `COLSxROWS`                   | `#size 90x52`   |
| `#fps`     | Playback frames per second                       | `#fps 24`       |
| `#frames`  | Total number of frames in the file               | `#frames 48`    |

### Optional fields

| Field      | Description                                      | Example         |
|------------|--------------------------------------------------|-----------------|
| `#mode`    | Colour mode used when capturing                  | `#mode color`   |
| `#source`  | Original filename if converted from video        | `#source clip.mp4` |
| `#author`  | Creator name                                     | `#author ben`   |
| `#created` | ISO 8601 creation timestamp                      | `#created 2026-03-10T14:32:00Z` |
| `#note`    | Free-text description                            | `#note waving at the camera` |

Unknown `#key` lines in the header must be ignored by parsers (forward compatibility).

### Valid `#mode` values

| Value     | Description                        |
|-----------|------------------------------------|
| `color`   | Full RGB from source               |
| `bw`      | Greyscale brightness only          |
| `rainbow` | HSV hue sweep across columns       |
| `edge`    | Sobel edge detection with directional chars |
| `glitch`  | Random character corruption effect |

### Example header

```
#txv v1
#size 90x52
#fps 24
#frames 120
#mode color
#source interview.mp4
#author ben
#created 2026-03-10T14:32:00Z
#note this is the first txv recording
---
```

---

## Frame Blocks

Each frame block follows this structure:

```
#frame N
<ROWS lines of character data>
#colors
col,row,#rrggbb
col,row,#rrggbb
...
---
```

### `#frame N`

Declares the start of frame number `N`. Frames are 1-indexed. Frames must appear in order.

### Character data

Immediately after `#frame N`, there are exactly `ROWS` lines of text. Each line contains exactly `COLS` characters — one character per cell. Characters are drawn from the printable ASCII set.

**The character set used by the reference implementation (light → dark):**

```
` . , - _ ~ ^ : ; ! | / \ ( ) < > [ ] { } i l 1 r t c v z + = * n u x ? e a o s y f h % k p d q b $ g w # @ W M & 8
```

Parsers should render whatever character is present — the set is not enforced.

### `#colors`

After the character data, the `#colors` block stores per-cell colour as `col,row,#rrggbb` entries, one per line. Coordinates are 0-indexed from the top-left.

**Only non-black cells are stored.** A cell with no entry in `#colors` is assumed to be `#000000`. This significantly reduces file size for dark frames.

Colour values are lowercase 6-digit hex with a `#` prefix: `#ff3a2d`, `#00ff41`, `#ffffff`.

### Frame separator

Each frame block ends with a line containing exactly `---`.

### Example frame block

```
#frame 1
`.,--iil|/\oosa@W
`.,--iil|/\oosa@W
#colors
0,0,#c43a1b
1,0,#c43a1b
4,0,#888800
7,0,#00ff41
---
```

---

## Complete minimal example

```
#txv v1
#size 4x2
#fps 4
#frames 2
---
#frame 1
`.,W
--@8
#colors
3,0,#ffffff
2,1,#00ff41
3,1,#ffffff
---
#frame 2
.,`W
-@-8
#colors
3,0,#ffffff
1,1,#00ff41
3,1,#ffffff
---
```

---

## Parser rules

1. Lines beginning with `#` inside a frame's character block are **not** metadata — the character block is read by line count (`ROWS` lines), not by scanning for `#` prefixes.
2. Unknown `#key` lines anywhere in the file must be silently ignored.
3. If a `#colors` block is missing for a frame, all cells are assumed black.
4. If a frame's character line is shorter than `COLS`, the remainder of that line is treated as spaces.
5. If `#frames` in the header does not match the actual frame count in the file, the actual count takes precedence.
6. A `---` line inside a `#colors` block terminates the frame regardless of expected entry count.
7. Files must be valid UTF-8. Only printable ASCII characters should appear in the character grid.

---

## Versioning

This document describes **TXV v1**. The version is declared in the first line of every file (`#txv v1`). Future versions may extend the header and frame structure. A v1 parser encountering a higher version number should attempt to parse it as v1 and note the version mismatch.

---

## Reference implementations

| Tool | Description |
|------|-------------|
| `ascii-cam.html` | Live webcam capture → `.txv` recorder |
| `txv-converter.html` | MP4/MOV/WEBM → `.txv` browser converter |
| `txv-player.html` | `.txv` player with playback controls |
| `txv-convert.py` | Command-line video → `.txv` converter (Python) |

---

## License

The TXV format specification is released into the public domain. Anyone may implement, extend, or build on it freely.

---

*TXV was designed in March 2026.*
