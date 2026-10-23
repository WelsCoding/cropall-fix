"""Output filename helpers for numbered (multi-crop) outputs.

These helpers are deliberately independent of Tk and ImageMagick, in the
same way as :mod:`crop_geometry`, so the numbering rules can be tested
without a GUI.

In multi-crop mode every crop of ``photo.jpg`` is written next to the
other crops as ``photo_1.jpg``, ``photo_2.jpg`` and so on. The number is
derived from the files already present in the output folder (rather than
from an in-memory counter), so numbering continues where a previous
session -- or an earlier visit to the same file -- left off, and an
existing crop is never overwritten.
"""

import re
from pathlib import Path


def numbered_output_path(output_folder, filename, number):
    """Return the output path for crop ``number`` of ``filename``.

    Only the base name of ``filename`` is used, e.g. crop 2 of
    ``holiday/photo.tar.jpg`` becomes ``<output_folder>/photo.tar_2.jpg``.
    """
    number = int(number)
    if number < 1:
        raise ValueError("Crop number must be a positive integer")
    source = Path(Path(filename).name)
    return Path(output_folder) / f"{source.stem}_{number}{source.suffix}"


def next_numbered_output_path(output_folder, filename):
    """Return the first unused numbered output path for ``filename``.

    The returned path never points at an existing file, so saving to it
    cannot overwrite an earlier crop (including a plain, un-numbered crop
    made with multi-crop disabled).
    """
    number = 1
    while True:
        candidate = numbered_output_path(output_folder, filename, number)
        if not candidate.exists():
            return candidate
        number += 1


def has_numbered_output(output_folder, filename):
    """Return True if the output folder already holds a numbered crop.

    A numbered crop is any file named ``<stem>_<number><suffix>`` for the
    given source ``filename``; the plain ``<stem><suffix>`` output does not
    count.
    """
    folder = Path(output_folder)
    if not folder.is_dir():
        return False
    source = Path(Path(filename).name)
    pattern = re.compile(
        rf"{re.escape(source.stem)}_\d+{re.escape(source.suffix)}",
        re.IGNORECASE,
    )
    return any(
        entry.is_file() and pattern.fullmatch(entry.name) for entry in folder.iterdir()
    )
