#!/usr/bin/env python3
"""
txv-convert.py — Convert a video file to the TXV format (Text Vision v1)

Requirements:
    pip install opencv-python numpy

Usage:
    python3 txv-convert.py input.mp4
    python3 txv-convert.py input.mp4 -o output.txv
    python3 txv-convert.py input.mp4 --cols 90 --fps 12 --duration 10
    python3 txv-convert.py input.mp4 --mode edge --contrast 1.5
    python3 txv-convert.py input.mp4 --mode bw --cols 120 --fps 24

See TXV_SPEC.md for the full format specification.
"""

import cv2
import numpy as np
import argparse
import sys
import os
import math
import time
from datetime import datetime, timezone

# ── Character set (light → dark, matching reference implementation) ──────────
CHARS = list(
    '`.,_-~^:;!|/\\()<>[]{}il1rtcvz+=*nux?eaosyfh%kpdqb$gw#@WM&8'
)

EDGE_CHARS = {
    'horizontal': '-',
    'diag_fwd':   '/',
    'vertical':   '|',
    'diag_back':  '\\',
}

EDGE_THRESHOLD = 0.18


# ── Colour modes ─────────────────────────────────────────────────────────────

def hsv_to_rgb(h, s, v):
    """h in 0-360, s and v in 0-1. Returns (r, g, b) in 0-255."""
    i = int(h / 60) % 6
    f = h / 60 - math.floor(h / 60)
    p, q, t = v*(1-s), v*(1-f*s), v*(1-(1-f)*s)
    cases = [(v,t,p),(q,v,p),(p,v,t),(p,q,v),(t,p,v),(v,p,q)]
    r, g, b = cases[i]
    return int(r*255), int(g*255), int(b*255)


def sobel_char(gray, col, row):
    """
    Run a 3×3 Sobel kernel on the grayscale image at (col, row).
    Returns (magnitude, directional_char).
    gray is a 2D numpy array of floats 0–1, shape (rows, cols).
    """
    rows, cols = gray.shape
    r0, r1, r2 = max(0,row-1), row, min(rows-1, row+1)
    c0, c1, c2 = max(0,col-1), col, min(cols-1, col+1)

    tl,tc,tr = gray[r0,c0], gray[r0,c1], gray[r0,c2]
    ml,       mr = gray[r1,c0],             gray[r1,c2]
    bl,bc,br = gray[r2,c0], gray[r2,c1], gray[r2,c2]

    gx = (-tl + tr) + 2*(-ml + mr) + (-bl + br)
    gy = (-tl - 2*tc - tr) + (bl + 2*bc + br)

    mag   = math.sqrt(gx*gx + gy*gy)
    angle = math.degrees(math.atan2(gy, gx)) % 180

    if   angle < 22.5  or angle >= 157.5: ch = '-'
    elif angle < 67.5:                    ch = '/'
    elif angle < 112.5:                   ch = '|'
    else:                                 ch = '\\'

    return mag, ch


def sample_frame(bgr_frame, cols, rows, contrast, mode, rainbow_hue=0):
    """
    Convert a BGR OpenCV frame (already resized to cols×rows) into
    a list of character rows and a colour map dict.

    Returns:
        char_rows  : list of strings, one per row
        color_map  : dict {(col, row): '#rrggbb'} — only non-black cells
        rainbow_hue: updated hue value for next call
    """
    # Convert to float RGB 0–1
    rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    gray = 0.299*rgb[:,:,0] + 0.587*rgb[:,:,1] + 0.114*rgb[:,:,2]

    # Apply contrast: (bright - 0.5) * contrast + 0.5, clamped to 0–1
    cb = np.clip((gray - 0.5) * contrast + 0.5, 0.0, 1.0)

    char_rows = []
    color_map = {}
    rainbow_hue = (rainbow_hue + 0.5) % 360

    for row in range(rows):
        row_str = ''
        for col in range(cols):
            bright = gray[row, col]
            c      = cb[row, col]
            r, g, b = rgb[row, col]

            if mode == 'edge':
                mag, edge_ch = sobel_char(gray, col, row)
                if mag > EDGE_THRESHOLD:
                    ch = edge_ch
                    intensity = min(1.0, mag / 0.6)
                    v = int(180 + intensity * 75)
                    cr, cg, cbl = v, v, v
                else:
                    idx = int(c * 0.4 * (len(CHARS)-1)) if c > 0.15 else 0
                    ch  = CHARS[idx]
                    v   = int(c * 55)
                    cr, cg, cbl = v, v, v

            elif mode == 'bw':
                ch  = CHARS[round(c * (len(CHARS)-1))]
                v   = int(c * 255)
                cr, cg, cbl = v, v, v

            elif mode == 'rainbow':
                ch  = CHARS[round(c * (len(CHARS)-1))]
                hue = (rainbow_hue + col * (360 / cols) + row * 1.5) % 360
                cr, cg, cbl = hsv_to_rgb(hue, 0.8, 0.35 + c * 0.65)

            else:  # color (default)
                ch  = CHARS[round(c * (len(CHARS)-1))]
                cr, cg, cbl = int(r*255), int(g*255), int(b*255)

            row_str += ch

            # Only store non-black cells
            if cr > 4 or cg > 4 or cbl > 4:
                color_map[(col, row)] = f'#{cr:02x}{cg:02x}{cbl:02x}'

        char_rows.append(row_str)

    return char_rows, color_map, rainbow_hue


# ── Main conversion ───────────────────────────────────────────────────────────

def convert(
    input_path,
    output_path=None,
    cols=80,
    fps=12,
    duration=None,
    contrast=1.2,
    mode='color',
    author=None,
    note=None,
    quiet=False,
):
    if not os.path.exists(input_path):
        print(f'Error: file not found: {input_path}', file=sys.stderr)
        sys.exit(1)

    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        print(f'Error: could not open video: {input_path}', file=sys.stderr)
        sys.exit(1)

    # Video metadata
    source_fps    = cap.get(cv2.CAP_PROP_FPS) or 30
    total_src_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    video_duration   = total_src_frames / source_fps
    vid_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    vid_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    aspect = vid_w / vid_h if vid_h > 0 else 16/9

    # Cap duration
    if duration is None:
        duration = video_duration
    else:
        duration = min(duration, video_duration)

    # Calculate target rows using real Courier New char proportions
    # Standard Courier New bold: charW ≈ 0.6 × charH  (measured empirically)
    CHAR_ASPECT = 0.601
    rows = max(1, round(cols * CHAR_ASPECT / aspect))

    total_frames = max(1, round(duration * fps))
    frame_step   = duration / total_frames  # seconds between samples

    # Output path
    if output_path is None:
        base = os.path.splitext(input_path)[0]
        output_path = base + '.txv'

    if not quiet:
        print(f'  Input   : {os.path.basename(input_path)}')
        print(f'  Video   : {vid_w}×{vid_h} @ {source_fps:.1f}fps  ({video_duration:.1f}s)')
        print(f'  Grid    : {cols}×{rows} chars')
        print(f'  Capture : {fps}fps for {duration:.1f}s = {total_frames} frames')
        print(f'  Mode    : {mode}   Contrast: {contrast}')
        print(f'  Output  : {output_path}')
        print()

    lines = []

    # ── Header ──
    lines.append('#txv v1')
    lines.append(f'#size {cols}x{rows}')
    lines.append(f'#fps {fps}')
    lines.append(f'#frames {total_frames}')
    lines.append(f'#mode {mode}')
    lines.append(f'#source {os.path.basename(input_path)}')
    lines.append(f'#created {datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}')
    if author:
        lines.append(f'#author {author}')
    if note:
        lines.append(f'#note {note}')
    lines.append('---')

    rainbow_hue = 0
    start_time  = time.time()

    for f in range(total_frames):
        target_time = f * frame_step
        target_src_frame = int(target_time * source_fps)
        target_src_frame = min(target_src_frame, total_src_frames - 1)

        # Seek and read
        cap.set(cv2.CAP_PROP_POS_FRAMES, target_src_frame)
        ret, bgr = cap.read()
        if not ret:
            # Try to read next available frame
            ret, bgr = cap.read()
            if not ret:
                if not quiet:
                    print(f'  Warning: could not read frame {f+1}, skipping.')
                continue

        # Resize to target grid
        small = cv2.resize(bgr, (cols, rows), interpolation=cv2.INTER_AREA)

        # Sample
        char_rows, color_map, rainbow_hue = sample_frame(
            small, cols, rows, contrast, mode, rainbow_hue
        )

        # Write frame
        lines.append(f'#frame {f+1}')
        lines.extend(char_rows)
        lines.append('#colors')
        for (c, r), hex_col in color_map.items():
            lines.append(f'{c},{r},{hex_col}')
        lines.append('---')

        # Progress
        if not quiet:
            pct     = (f+1) / total_frames * 100
            elapsed = time.time() - start_time
            eta     = (elapsed / (f+1)) * (total_frames - f - 1) if f > 0 else 0
            bar_len = 30
            filled  = int(bar_len * (f+1) / total_frames)
            bar     = '█' * filled + '░' * (bar_len - filled)
            print(
                f'\r  [{bar}] {pct:5.1f}%  frame {f+1}/{total_frames}'
                f'  ETA {eta:.0f}s   ',
                end='', flush=True
            )

    cap.release()

    if not quiet:
        print(f'\n\n  Done in {time.time()-start_time:.1f}s')

    # Write file
    content = '\n'.join(lines)
    with open(output_path, 'w', encoding='utf-8') as fh:
        fh.write(content)

    size_kb = len(content.encode('utf-8')) / 1024
    if not quiet:
        print(f'  Wrote {size_kb:.0f} KB → {output_path}')

    return output_path


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Convert a video file to TXV (Text Vision) format.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  python3 txv-convert.py clip.mp4
  python3 txv-convert.py clip.mp4 -o out.txv --cols 90 --fps 24
  python3 txv-convert.py clip.mp4 --mode edge --contrast 1.8 --duration 5
  python3 txv-convert.py clip.mov --mode bw --cols 120
  python3 txv-convert.py clip.mp4 --author ben --note "first txv"

modes:
  color    Full RGB colour (default)
  bw       Greyscale
  rainbow  Animated HSV hue sweep
  edge     Sobel edge detection with directional chars (/ \\ | -)
        """
    )

    parser.add_argument('input',
        help='Input video file (MP4, MOV, WEBM, AVI, etc.)')
    parser.add_argument('-o', '--output',
        help='Output .txv file path (default: same name as input)')
    parser.add_argument('--cols', type=int, default=80,
        help='Character grid width in columns (default: 80)')
    parser.add_argument('--fps', type=int, default=12,
        help='Frames per second to capture (default: 12)')
    parser.add_argument('--duration', type=float, default=None,
        help='Max seconds to convert (default: full video)')
    parser.add_argument('--contrast', type=float, default=1.2,
        help='Contrast multiplier 0.3–2.5 (default: 1.2)')
    parser.add_argument('--mode', default='color',
        choices=['color','bw','rainbow','edge'],
        help='Colour mode (default: color)')
    parser.add_argument('--author',
        help='Author name to embed in the file header')
    parser.add_argument('--note',
        help='Short description to embed in the file header')
    parser.add_argument('-q', '--quiet', action='store_true',
        help='Suppress progress output')

    args = parser.parse_args()

    print()
    print('  TXV CONVERTER  v1.0')
    print('  ─────────────────────────────')

    convert(
        input_path  = args.input,
        output_path = args.output,
        cols        = args.cols,
        fps         = args.fps,
        duration    = args.duration,
        contrast    = args.contrast,
        mode        = args.mode,
        author      = args.author,
        note        = args.note,
        quiet       = args.quiet,
    )


if __name__ == '__main__':
    main()
