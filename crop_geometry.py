"""Pixel-safe crop and resize geometry helpers.

These functions are deliberately independent of Tk and ImageMagick so crop
constraints can be previewed in the GUI and checked by the file processors.
"""

from fractions import Fraction
import math


def _positive_int(value, name):
    try:
        value = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a positive integer") from None
    if value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _aspect_values(aspect):
    if aspect is None:
        return None
    try:
        width, height = aspect
        width = _positive_int(width, "Aspect width")
        height = _positive_int(height, "Aspect height")
    except (TypeError, ValueError):
        raise ValueError("Aspect ratio must contain two positive integers") from None
    ratio = width / height
    return ratio, Fraction(width, height)


def _clamp(value, lower, upper):
    return min(max(value, lower), upper)


def _round_half_up(value):
    return int(math.floor(value + 0.5))


def _nearest_units(target, maximum):
    """Small set of nearby positive integer sizes, measured in grid units."""
    if maximum < 1:
        return set()
    base = math.floor(target)
    candidates = {1, maximum}
    for value in (base - 1, base, base + 1, base + 2):
        candidates.add(int(_clamp(value, 1, maximum)))
    return candidates


def _divisible_dimensions(
    target_width,
    target_height,
    max_width,
    max_height,
    divisor,
    alignment,
    aspect=None,
):
    """Choose dimensions on the requested pixel grid, close to the target."""
    divisor = _positive_int(divisor, "Divisibility")
    alignment = _positive_int(alignment, "Pixel alignment")
    step = math.lcm(divisor, alignment)
    max_width = int(max_width)
    max_height = int(max_height)
    max_width_units = max_width // step
    max_height_units = max_height // step
    if max_width_units < 1 or max_height_units < 1:
        raise ValueError(
            f"The image is too small to produce sides divisible by {divisor}"
        )

    target_width = max(float(target_width), float(step))
    target_height = max(float(target_height), float(step))
    target_width_units = target_width / step
    target_height_units = target_height / step

    aspect_values = _aspect_values(aspect)
    if aspect_values is None:
        width_units = int(math.floor(target_width_units))
        height_units = int(math.floor(target_height_units))
        width_units = int(_clamp(width_units, 1, max_width_units))
        height_units = int(_clamp(height_units, 1, max_height_units))
        return width_units * step, height_units * step

    ratio, ratio_fraction = aspect_values
    width_candidates = _nearest_units(target_width_units, max_width_units)
    height_candidates = _nearest_units(target_height_units, max_height_units)
    candidates = set()

    # Consider nearby sizes that follow the selected ratio, from either side.
    for width_units in width_candidates:
        for height_units in {
            _clamp(_round_half_up(width_units / ratio), 1, max_height_units),
            _clamp(math.floor(width_units / ratio), 1, max_height_units),
            _clamp(math.ceil(width_units / ratio), 1, max_height_units),
        }:
            candidates.add((int(width_units), int(height_units)))
    for height_units in height_candidates:
        for width_units in {
            _clamp(_round_half_up(height_units * ratio), 1, max_width_units),
            _clamp(math.floor(height_units * ratio), 1, max_width_units),
            _clamp(math.ceil(height_units * ratio), 1, max_width_units),
        }:
            candidates.add((int(width_units), int(height_units)))

    # Include exact integer multiples of the ratio when they fit close to the
    # requested crop. This keeps common ratios exact without shrinking crops
    # dramatically just to find an exact integer pair.
    numerator = ratio_fraction.numerator
    denominator = ratio_fraction.denominator
    max_exact_scale = min(
        max_width_units // numerator, max_height_units // denominator
    )
    target_exact_scale = min(
        target_width_units / numerator, target_height_units / denominator
    )
    exact_scale = min(math.floor(target_exact_scale), max_exact_scale)
    if exact_scale >= 1:
        exact_width_units = numerator * exact_scale
        exact_height_units = denominator * exact_scale
        width_coverage = exact_width_units / target_width_units
        height_coverage = exact_height_units / target_height_units
        if min(width_coverage, height_coverage) >= 0.90:
            return exact_width_units * step, exact_height_units * step

    for scale in {
        int(_clamp(math.floor(target_exact_scale), 1, max_exact_scale))
        if max_exact_scale
        else 0,
        int(_clamp(math.ceil(target_exact_scale), 1, max_exact_scale))
        if max_exact_scale
        else 0,
        max_exact_scale,
    }:
        if scale:
            candidates.add((numerator * scale, denominator * scale))

    # Small ratio errors are normal when pixel dimensions are rounded. The
    # score balances that error with how much of the user's requested region is
    # retained, preferring a slightly larger near-match over a much smaller
    # exact ratio when the pixel grid makes an exact match impractical.
    def score(size):
        width_units, height_units = size
        actual_ratio = width_units / height_units
        ratio_error = abs(math.log(actual_ratio / ratio))
        width_error = abs(width_units - target_width_units) / max(
            target_width_units, 1.0
        )
        height_error = abs(height_units - target_height_units) / max(
            target_height_units, 1.0
        )
        return (
            ratio_error + 0.25 * (width_error + height_error),
            -(width_units * height_units),
        )

    width_units, height_units = min(candidates, key=score)
    return width_units * step, height_units * step


def normalize_crop_coords(
    coords,
    image_size,
    divisor=1,
    aspect=None,
    alignment=1,
):
    """Return a clamped crop rectangle satisfying the requested pixel rules.

    ``coords`` is ``(left, top, right, bottom)`` and may use either drag
    direction. ``aspect`` is either ``None`` (free selection) or a
    ``(width, height)`` ratio. ``alignment`` additionally aligns both the
    output dimensions and their top-left offsets; videos use 2 for common
    4:2:0 chroma formats.
    """
    if len(coords) != 4 or len(image_size) != 2:
        raise ValueError("Crop coordinates and image size are invalid")
    image_width = _positive_int(image_size[0], "Image width")
    image_height = _positive_int(image_size[1], "Image height")
    alignment = _positive_int(alignment, "Pixel alignment")

    try:
        x1, y1, x2, y2 = (float(value) for value in coords)
    except (TypeError, ValueError):
        raise ValueError("Crop coordinates must be numeric") from None
    if not all(math.isfinite(value) for value in (x1, y1, x2, y2)):
        raise ValueError("Crop coordinates must be finite")

    left = _clamp(min(x1, x2), 0.0, float(image_width))
    right = _clamp(max(x1, x2), 0.0, float(image_width))
    top = _clamp(min(y1, y2), 0.0, float(image_height))
    bottom = _clamp(max(y1, y2), 0.0, float(image_height))
    requested_width = max(right - left, 0.0)
    requested_height = max(bottom - top, 0.0)

    aspect_values = _aspect_values(aspect)
    ratio = aspect_values[0] if aspect_values else None
    if ratio is not None and requested_width > 0 and requested_height > 0:
        if requested_width / requested_height > ratio:
            target_height = requested_height
            target_width = target_height * ratio
        else:
            target_width = requested_width
            target_height = target_width / ratio
    else:
        target_width = requested_width
        target_height = requested_height

    width, height = _divisible_dimensions(
        target_width,
        target_height,
        image_width,
        image_height,
        divisor,
        alignment,
        aspect=aspect,
    )

    center_x = (left + right) / 2.0
    center_y = (top + bottom) / 2.0
    max_left = ((image_width - width) // alignment) * alignment
    max_top = ((image_height - height) // alignment) * alignment
    left_px = int(
        _clamp(
            _round_half_up((center_x - width / 2.0) / alignment) * alignment,
            0,
            max_left,
        )
    )
    top_px = int(
        _clamp(
            _round_half_up((center_y - height / 2.0) / alignment) * alignment,
            0,
            max_top,
        )
    )
    return [left_px, top_px, left_px + width, top_px + height]


def validate_crop_coords(coords, image_size, divisor=1, alignment=1):
    """Validate a final crop rectangle without changing its displayed size."""
    if len(coords) != 4 or len(image_size) != 2:
        raise ValueError("Crop coordinates and image size are invalid")
    image_width = _positive_int(image_size[0], "Image width")
    image_height = _positive_int(image_size[1], "Image height")
    divisor = _positive_int(divisor, "Divisibility")
    alignment = _positive_int(alignment, "Pixel alignment")
    try:
        values = [int(value) for value in coords]
    except (TypeError, ValueError):
        raise ValueError("Crop coordinates must be integers") from None
    if any(float(value) != int(value) for value in coords):
        raise ValueError("Crop coordinates must be integers")

    left, top, right, bottom = values
    width = right - left
    height = bottom - top
    if (
        left < 0
        or top < 0
        or right > image_width
        or bottom > image_height
        or width < 1
        or height < 1
    ):
        raise ValueError("Crop selection falls outside the image")
    if width % divisor or height % divisor:
        raise ValueError(
            f"Crop width and height must both be divisible by {divisor}"
        )
    if alignment > 1 and (
        width % alignment
        or height % alignment
        or left % alignment
        or top % alignment
    ):
        raise ValueError("Crop selection is not aligned for video encoding")
    return values


def resize_dimensions(
    source_size,
    max_size,
    divisor=1,
    alignment=1,
):
    """Fit ``source_size`` within ``max_size`` without upscaling.

    The returned dimensions are divisible by ``divisor`` and aligned for the
    target pixel format, while retaining the source aspect ratio as closely as
    integer pixel dimensions allow.
    """
    if len(source_size) != 2 or len(max_size) != 2:
        raise ValueError("Source and maximum sizes must have two dimensions")
    source_width = _positive_int(source_size[0], "Source width")
    source_height = _positive_int(source_size[1], "Source height")
    max_width = _positive_int(max_size[0], "Maximum width")
    max_height = _positive_int(max_size[1], "Maximum height")
    width_limit = min(source_width, max_width)
    height_limit = min(source_height, max_height)
    scale = min(1.0, width_limit / source_width, height_limit / source_height)
    target_width = source_width * scale
    target_height = source_height * scale
    return _divisible_dimensions(
        target_width,
        target_height,
        width_limit,
        height_limit,
        divisor,
        alignment,
        aspect=(source_width, source_height),
    )
