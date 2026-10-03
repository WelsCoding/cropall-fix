# cropall: a tiny batch image processing app to crop pictures in less clicks
#
# Copyright (C) 2015-2024 Pyarelal Knowles
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
import os
import shutil
from pathlib import Path

import wand.image
from tkinter import messagebox

import video_support
from crop_geometry import resize_dimensions, validate_crop_coords

logger = logging.getLogger("cropall")

DEFAULT_VIDEO_EXTENSIONS = (
    ".mp4 .mov .mkv .avi .webm .m4v .mpeg .mpg .wmv .3gp "
    ".ts .m2ts .flv .vob"
)


class Cropper:
    def __init__(self, config):
        self.config = config
        extensions = config.get(
            "cropall", "video_extensions", fallback=DEFAULT_VIDEO_EXTENSIONS
        )
        self.video_extensions = {
            extension.lower() for extension in extensions.split()
        }

    def is_video_file(self, filename):
        return Path(filename).suffix.lower() in self.video_extensions

    def _divisor(self):
        value = self.config.get("selection", "divisible_by", fallback="").strip()
        if not value:
            return 1
        try:
            divisor = int(value)
        except ValueError:
            raise ValueError("Divisible by must be a positive integer") from None
        if divisor < 1:
            raise ValueError("Divisible by must be a positive integer")
        return divisor

    def _resize_limits(self):
        try:
            width = max(1, self.config.getint("cropper", "resize_width"))
            height = max(1, self.config.getint("cropper", "resize_height"))
        except (ValueError, KeyError):
            return 1920, 1080
        return width, height

    def _show_video_error(self, error):
        logger.exception("Video processing failed: %s", error)
        messagebox.showerror(
            "Video processing failed",
            f"Could not process the video.\n\n{error}",
        )

    def can_replace(self, dst_file):
        ask = self.config.getboolean("cropper", "confirm_overwrite")
        exists = os.path.exists(dst_file)
        if ask and exists:
            return messagebox.askokcancel(
                "File exists. Overwrite?",
                f"{dst_file} already exists. Are you sure you want to overwrite it? "
                "(disable asking in options)",
            )
        return True

    def resize(self, src_file, dst_file):
        if not self.can_replace(dst_file):
            return False
        if self.is_video_file(src_file):
            try:
                source_size = video_support.probe_video_size(src_file)
                width, height = resize_dimensions(
                    source_size,
                    self._resize_limits(),
                    divisor=self._divisor(),
                    alignment=2,
                )
                if (width, height) == source_size:
                    shutil.copy(src_file, dst_file)
                else:
                    video_support.transcode_video(
                        src_file, dst_file, f"scale={width}:{height}"
                    )
            except (video_support.VideoError, ValueError) as error:
                self._show_video_error(error)
                return False
            return True

        try:
            with wand.image.Image(filename=src_file) as img:
                width, height = resize_dimensions(
                    (img.width, img.height),
                    self._resize_limits(),
                    divisor=self._divisor(),
                )
                if (width, height) != (img.width, img.height):
                    img.transform(resize=f"{width}x{height}!")
                img.save(filename=dst_file)
        except ValueError as error:
            messagebox.showerror("Invalid resize settings", str(error))
            return False
        return True

    def crop(self, src_file, dst_file, box, source_size=None):
        if not self.can_replace(dst_file):
            return False
        if self.is_video_file(src_file):
            try:
                self._crop_video(src_file, dst_file, box, source_size)
            except (video_support.VideoError, ValueError) as error:
                self._show_video_error(error)
                return False
            return True

        try:
            with wand.image.Image(filename=src_file) as img:
                divisor = self._divisor()
                coords = validate_crop_coords(
                    box, (img.width, img.height), divisor=divisor
                )
                x1, y1, x2, y2 = coords
                crop = f"{x2 - x1}x{y2 - y1}+{x1}+{y1}"
                img.transform(crop=crop)

                resize = "no resize"
                if self.config.getboolean("cropper", "resize"):
                    width, height = resize_dimensions(
                        (img.width, img.height),
                        self._resize_limits(),
                        divisor=divisor,
                    )
                    if (width, height) != (img.width, img.height):
                        img.transform(resize=f"{width}x{height}!")
                    resize = f"{width}x{height}"
                logger.info("Writing %s, crop %s %s", dst_file, crop, resize)
                img.save(filename=dst_file)
        except ValueError as error:
            messagebox.showerror("Invalid crop settings", str(error))
            return False
        return True

    def _crop_video(self, src_file, dst_file, box, source_size=None):
        divisor = self._divisor()
        if source_size is None:
            source_size = video_support.probe_video_size(src_file)
        coords = validate_crop_coords(
            box, source_size, divisor=divisor, alignment=2
        )
        x1, y1, x2, y2 = coords
        crop_width = x2 - x1
        crop_height = y2 - y1
        filters = [f"crop={crop_width}:{crop_height}:{x1}:{y1}:exact=1"]

        if self.config.getboolean("cropper", "resize"):
            width, height = resize_dimensions(
                (crop_width, crop_height),
                self._resize_limits(),
                divisor=divisor,
                alignment=2,
            )
            if (width, height) != (crop_width, crop_height):
                filters.append(f"scale={width}:{height}:flags=lanczos")

        logger.info(
            "Writing %s, video crop %sx%s+%s+%s, filters %s",
            dst_file,
            crop_width,
            crop_height,
            x1,
            y1,
            ",".join(filters),
        )
        video_support.transcode_video(src_file, dst_file, ",".join(filters))

    def copy(self, src_file, dst_file):
        if not self.can_replace(dst_file):
            return False
        shutil.copy(src_file, dst_file)
        return True
