"""FFmpeg helpers for displaying and cropping video files."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import uuid


class VideoError(RuntimeError):
    """Raised when FFmpeg cannot read or process a video."""


class VideoFrameUnavailable(VideoError):
    """Raised when a requested frame number is past the end of a video."""


def ffmpeg_available():
    return shutil.which("ffmpeg") is not None


def extract_frame(video_path, frame_number=0):
    """Return one video frame as PNG bytes (frame numbers are zero-based)."""
    frame_number = int(frame_number)
    if frame_number < 0:
        raise ValueError("Frame number cannot be negative")

    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(video_path),
        "-map",
        "0:v:0",
    ]
    if frame_number:
        command += ["-vf", f"select=eq(n\,{frame_number})", "-vsync", "0"]
    command += [
        "-frames:v",
        "1",
        "-f",
        "image2pipe",
        "-vcodec",
        "png",
        "pipe:1",
    ]

    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError:
        raise VideoError(
            "ffmpeg was not found. Install FFmpeg to preview and crop videos."
        ) from None
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        if frame_number and any(
            marker in detail.lower()
            for marker in (
                "output file is empty",
                "nothing was encoded",
                "nothing was written",
            )
        ):
            raise VideoFrameUnavailable("There are no more frames in this video")
        raise VideoError(detail or "ffmpeg could not read this video")
    if not result.stdout:
        raise VideoFrameUnavailable("There are no more frames in this video")
    return result.stdout


def probe_video_size(video_path):
    """Return display-oriented ``(width, height)`` for the first video stream."""
    command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height:stream_tags=rotate:stream_side_data=rotation",
        "-of",
        "json",
        str(video_path),
    ]
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError:
        raise VideoError(
            "ffprobe was not found. Install FFmpeg to crop or resize videos."
        ) from None
    if result.returncode:
        raise VideoError(result.stderr.strip() or "ffprobe could not read this video")
    try:
        stream = json.loads(result.stdout)["streams"][0]
        width = int(stream["width"])
        height = int(stream["height"])
        rotation = float(stream.get("tags", {}).get("rotate", 0))
        for side_data in stream.get("side_data_list", []):
            if "rotation" in side_data:
                rotation = float(side_data["rotation"])
                break
    except (IndexError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        raise VideoError("Could not determine the video dimensions") from None
    if width < 1 or height < 1:
        raise VideoError("The video has invalid dimensions")
    if round(abs(rotation)) % 180 == 90:
        return height, width
    return width, height


def _encoder_arguments(output_path):
    suffix = Path(output_path).suffix.lower()
    if suffix == ".webm":
        return [
            "-c:v",
            "libvpx-vp9",
            "-crf",
            "30",
            "-b:v",
            "0",
            "-c:a",
            "libopus",
        ]
    if suffix in (".mpg", ".mpeg", ".vob"):
        return ["-c:v", "mpeg2video", "-q:v", "3", "-c:a", "mp2"]
    if suffix == ".avi":
        return [
            "-c:v",
            "mpeg4",
            "-q:v",
            "3",
            "-c:a",
            "libmp3lame",
            "-q:a",
            "3",
        ]
    if suffix == ".wmv":
        return ["-c:v", "wmv2", "-q:v", "3", "-c:a", "wmav2"]

    arguments = [
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
    ]
    if suffix in (".mp4", ".m4v", ".mov"):
        arguments += ["-movflags", "+faststart"]
    return arguments


def _run_transcode(command):
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError:
        raise VideoError(
            "ffmpeg was not found. Install FFmpeg to crop or resize videos."
        ) from None
    if result.returncode:
        detail = result.stderr.strip()
        if len(detail) > 1600:
            detail = detail[-1600:]
        raise VideoError(detail or "ffmpeg could not process this video")


def transcode_video(input_path, output_path, video_filter):
    """Apply a video filter and atomically replace the destination on success."""
    input_path = Path(input_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_suffix = output_path.suffix.lower()
    temporary_path = output_path.with_name(
        f".{output_path.stem}.cropall-{uuid.uuid4().hex}{temporary_suffix}"
    )
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(input_path),
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-map_metadata",
        "0",
        "-vf",
        video_filter,
    ]
    command += _encoder_arguments(temporary_path)
    command.append(str(temporary_path))

    try:
        _run_transcode(command)
        if not temporary_path.exists() or temporary_path.stat().st_size == 0:
            raise VideoError("ffmpeg did not produce an output video")
        try:
            os.replace(temporary_path, output_path)
        except OSError as error:
            raise VideoError(f"Could not save the cropped video: {error}") from error
    finally:
        try:
            temporary_path.unlink()
        except FileNotFoundError:
            pass
