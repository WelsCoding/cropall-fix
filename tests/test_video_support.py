import json
import subprocess
import unittest
from unittest.mock import patch

import video_support


class VideoSupportTests(unittest.TestCase):
    @patch("video_support.subprocess.run")
    def test_extract_frame_selects_requested_zero_based_frame(self, run):
        run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=b"png", stderr=b""
        )
        self.assertEqual(video_support.extract_frame("clip.mp4", 10), b"png")
        command = run.call_args.args[0]
        self.assertIn(r"select=eq(n\,10)", command)
        self.assertIn("-vsync", command)

    @patch("video_support.subprocess.run")
    def test_extract_frame_reports_end_of_video(self, run):
        run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=b"", stderr=b""
        )
        with self.assertRaises(video_support.VideoFrameUnavailable):
            video_support.extract_frame("clip.mp4", 30)

    @patch("video_support.subprocess.run")
    def test_probe_video_size_accounts_for_rotation_metadata(self, run):
        run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps(
                {
                    "streams": [
                        {
                            "width": 1920,
                            "height": 1080,
                            "tags": {"rotate": "90"},
                        }
                    ]
                }
            ),
            stderr="",
        )
        self.assertEqual(video_support.probe_video_size("rotated.mov"), (1080, 1920))


if __name__ == "__main__":
    unittest.main()
