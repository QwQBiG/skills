"""Place transparent handwriting on the measured baselines of a paper photo."""

import argparse
from itertools import groupby
import json
from math import isfinite
from pathlib import Path

from PIL import Image, ImageChops


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def curve(x, xs, ys):
    for i in range(1, len(xs)):
        if x <= xs[i]:
            t = (x - xs[i - 1]) / (xs[i] - xs[i - 1])
            return round(ys[i - 1] + t * (ys[i] - ys[i - 1]))
    return ys[-1]


def read_ink(path, crop):
    with Image.open(path) as source:
        image = source.convert("RGBA")
    if crop is not None:
        left, top, right, bottom = crop
        if not (0 <= left < right <= image.width and 0 <= top < bottom <= image.height):
            raise ValueError(f"Crop outside image: {path}")
        image = image.crop(crop)
    alpha = image.getchannel("A")
    if alpha.getextrema()[0] == 255:
        raise ValueError(f"Expected transparent ink: {path}")
    # Effective darkness discards invisible RGB and retains antialiased edges.
    darkness = ImageChops.multiply(ImageChops.invert(image.convert("L")), alpha)
    bounds = darkness.point(lambda p: 255 if p >= 12 else 0).getbbox()
    if not bounds:
        raise ValueError(f"No visible ink: {path}")
    return darkness.crop(bounds)


def compose(template_path, job_path, output):
    paper = read_json(template_path)
    with Image.open(template_path.parent / paper["photo"]) as source:
        page = source.convert("RGB")
    xs, rows = paper["x_samples"], paper["baselines"]
    if (list(page.size) != paper["size_px"] or len(xs) < 2
            or not 0 <= xs[0] < xs[-1] < page.width
            or any(a >= b for a, b in zip(xs, xs[1:]))
            or any(len(row) != len(xs) for row in rows)):
        raise ValueError("Invalid paper coordinates or photo size")
    entries = read_json(job_path)["lines"]
    if not entries:
        raise ValueError("Expected at least one line")
    used = set()
    for entry in entries:
        row = entry["row"]
        if type(row) is not int or not 1 <= row <= len(rows) or row in used:
            raise ValueError(f"Invalid or repeated row: {row}")
        used.add(row)
        ink = read_ink(job_path.parent / entry["file"], entry.get("crop"))
        height = entry.get("height_px", paper["ink_height_px"])
        indent = entry.get("indent_px", 0)
        if type(height) is not int or height <= 0 or type(indent) is not int or indent < 0:
            raise ValueError(f"Invalid height or indent on row {row}")
        start = xs[0] + indent
        width = max(1, round(ink.width * height / ink.height))
        if start + width - 1 > xs[-1]:
            raise ValueError(f"Line exceeds writing area on row {row}. Rewrap the text.")
        ink = ink.resize((width, height), Image.Resampling.LANCZOS)
        baseline = entry.get("baseline", 0.92)
        if not isfinite(baseline) or not 0 <= baseline <= 1:
            raise ValueError(f"Invalid baseline on row {row}")
        offset = round(height * baseline)
        # Group neighboring columns that need the same vertical shift.
        def top(column):
            return curve(start + column, xs, rows[row - 1]) - offset

        for y, columns in groupby(range(width), key=top):
            group = list(columns)
            first, last = group[0], group[-1]
            if y < 0 or y + height > page.height:
                raise ValueError(f"Line outside photo on row {row}")
            box = (start + first, y, start + last + 1, y + height)
            mask = ink.crop((first, 0, last + 1, height))
            # Local paper brightness also affects the tone at the inked pixels.
            transmission = mask.point(lambda p: 255 - round(0.91 * p)).convert("RGB")
            page.paste(ImageChops.multiply(page.crop(box), transmission), box)
    if output.suffix.lower() != ".png":
        raise ValueError("Expected a PNG output path")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as dest:
        page.save(dest, format="PNG")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("template", "job", "output"):
        parser.add_argument(arg, type=Path)
    args = parser.parse_args()
    try:
        compose(args.template, args.job, args.output)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"{error}\n")
