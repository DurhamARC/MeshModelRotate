#!/usr/bin/env python3
"""Build contact sheets from rendered thumbnails, for eyeballing a batch quickly.

Two ways to choose what goes on the sheets:

    contact_sheet.py --dir /mnt/srs/HoBScan/Processed/Ashmolean -o sheets/
    contact_sheet.py --csv review_orientation.csv --root /mnt/srs/HoBScan/Processed -o sheets/

The CSV form is for reviewing flagged models: it takes `collection` and `model` columns and, if an
`extent_margin_mm` column is present, orders by it ascending so the least decisive cases come first
-- those are where an orientation rule is most likely to have got it wrong, so a reviewer who stops
early has still seen the ones that matter.

Thumbnails are RGBA with a transparent background; they are composited onto a mid grey, since pale
flint on white is hard to read.
"""
import argparse
import csv
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

BG = (208, 208, 208)
SHEET_BG = (245, 245, 245)
LABEL_H = 22
PAD = 8


def load_font(size):
    for path in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                 "/usr/share/fonts/dejavu/DejaVuSans.ttf"):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def entries_from_csv(path, root):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    if rows and "extent_margin_mm" in rows[0]:
        rows.sort(key=lambda r: float(r["extent_margin_mm"] or 0))
    out = []
    for r in rows:
        png = os.path.join(root, r["collection"], r["model"] + ".png")
        label = r["model"]
        if "extent_margin_mm" in r:
            label += "  ({}mm)".format(r["extent_margin_mm"])
        out.append((png, label, r["collection"]))
    return out


def entries_from_dir(d):
    return [(os.path.join(d, f), os.path.splitext(f)[0], os.path.basename(d.rstrip("/")))
            for f in sorted(os.listdir(d)) if f.lower().endswith(".png")]


def fit(draw, text, font, width):
    """Shorten from the left until the label fits its cell: these names differ in the tail, and a
    label wider than its cell overlaps the next one and makes both unreadable."""
    if draw.textlength(text, font=font) <= width:
        return text
    for i in range(1, len(text)):
        cut = "…" + text[i:]
        if draw.textlength(cut, font=font) <= width:
            return cut
    return ""


def build(entries, out_dir, cell, cols, per_sheet, title):
    os.makedirs(out_dir, exist_ok=True)
    font = load_font(11)
    head = load_font(15)
    rows = math.ceil(per_sheet / cols)
    cw, ch = cell + PAD, cell + LABEL_H + PAD
    sheets, missing = [], []

    for n in range(0, len(entries), per_sheet):
        chunk = entries[n:n + per_sheet]
        head_h = 30
        sheet = Image.new("RGB", (cols * cw + PAD, rows * ch + PAD + head_h), SHEET_BG)
        draw = ImageDraw.Draw(sheet)
        idx = n // per_sheet + 1
        total = math.ceil(len(entries) / per_sheet)
        draw.text((PAD, 8), "{} — sheet {} of {} — items {}-{} of {}".format(
            title, idx, total, n + 1, n + len(chunk), len(entries)), fill=(40, 40, 40), font=head)

        for i, (png, label, _) in enumerate(chunk):
            x = PAD + (i % cols) * cw
            y = PAD + head_h + (i // cols) * ch
            box = Image.new("RGB", (cell, cell), BG)
            if os.path.exists(png):
                try:
                    im = Image.open(png).convert("RGBA")
                    im.thumbnail((cell, cell), Image.LANCZOS)
                    box.paste(im, ((cell - im.width) // 2, (cell - im.height) // 2), im)
                except Exception as e:                       # a corrupt PNG must not kill the sheet
                    missing.append("{}: {}".format(png, e))
                    draw.text((x + 4, y + 4), "unreadable", fill=(180, 0, 0), font=font)
            else:
                missing.append(png)
                draw.text((x + 4, y + 4), "missing", fill=(180, 0, 0), font=font)
            sheet.paste(box, (x, y))
            draw.text((x + 2, y + cell + 4), fit(draw, label, font, cell - 4),
                      fill=(30, 30, 30), font=font)

        path = os.path.join(out_dir, "sheet_{:03d}.png".format(idx))
        sheet.save(path, optimize=True)
        sheets.append(path)
        print("{}  ({} items)".format(path, len(chunk)))

    return sheets, missing


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--csv", help="CSV with 'collection' and 'model' columns")
    src.add_argument("--dir", help="directory of PNG thumbnails")
    ap.add_argument("--root", default="/mnt/srs/HoBScan/Processed",
                    help="where <collection>/<model>.png live (with --csv)")
    ap.add_argument("-o", "--out", required=True, help="output directory for the sheets")
    ap.add_argument("--cell", type=int, default=180, help="thumbnail size in px (default 180)")
    ap.add_argument("--cols", type=int, default=10, help="columns per sheet (default 10)")
    ap.add_argument("--per-sheet", type=int, default=60, help="items per sheet (default 60)")
    ap.add_argument("--title", default=None)
    a = ap.parse_args()

    entries = entries_from_csv(a.csv, a.root) if a.csv else entries_from_dir(a.dir)
    if not entries:
        sys.exit("nothing to render")
    title = a.title or (os.path.basename(a.csv) if a.csv else os.path.basename(a.dir.rstrip("/")))

    sheets, missing = build(entries, a.out, a.cell, a.cols, a.per_sheet, title)
    print("\n{} sheets, {} thumbnails, in {}".format(len(sheets), len(entries), a.out))
    if missing:
        print("WARNING: {} could not be read:".format(len(missing)), file=sys.stderr)
        for m in missing[:10]:
            print("  " + m, file=sys.stderr)


if __name__ == "__main__":
    main()
