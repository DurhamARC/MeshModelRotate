#!/usr/bin/env python
"""Losslessly optimise a thumbnail with oxipng and mark the model's JSON record complete.

    optimise_png.py <name.png> <name.json>
"""

import json
import os
import sys
from importlib.metadata import version
from pathlib import Path

import oxipng


def main():
    png, record_path = Path(sys.argv[1]), Path(sys.argv[2])
    before = png.stat().st_size
    oxipng.optimize(png, level=4, strip=oxipng.StripChunks.safe())
    after = png.stat().st_size

    record = json.loads(record_path.read_text())
    record["thumbnail"] = {"png": png.name, "size_rendered": before, "size": after}
    record["versions"]["pyoxipng"] = version("pyoxipng")
    record["status"] = "complete"
    tmp = record_path.with_name(f".{record_path.name}.partial")
    tmp.write_text(json.dumps(record, indent=2))
    os.replace(tmp, record_path)
    print(f"OK: {png} {before // 1024}KB -> {after // 1024}KB")


if __name__ == "__main__":
    main()
