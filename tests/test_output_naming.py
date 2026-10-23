import tempfile
import unittest
from pathlib import Path

from output_naming import (
    has_numbered_output,
    next_numbered_output_path,
    numbered_output_path,
)


class OutputNamingTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.output_folder = Path(self.temporary_directory.name)

    def touch(self, name):
        (self.output_folder / name).touch()

    def test_numbered_output_path_inserts_number_before_extension(self):
        self.assertEqual(
            numbered_output_path(self.output_folder, "photo.jpg", 3),
            self.output_folder / "photo_3.jpg",
        )

    def test_numbered_output_path_rejects_non_positive_numbers(self):
        with self.assertRaises(ValueError):
            numbered_output_path(self.output_folder, "photo.jpg", 0)

    def test_first_crop_is_number_one(self):
        self.assertEqual(
            next_numbered_output_path(self.output_folder, "photo.jpg"),
            self.output_folder / "photo_1.jpg",
        )

    def test_plain_output_does_not_block_first_numbered_crop(self):
        # A crop made earlier with multi-crop disabled must not be
        # overwritten by, or change the numbering of, numbered crops.
        self.touch("photo.jpg")
        self.assertEqual(
            next_numbered_output_path(self.output_folder, "photo.jpg"),
            self.output_folder / "photo_1.jpg",
        )

    def test_number_increments_past_existing_crops(self):
        self.touch("photo_1.jpg")
        self.touch("photo_2.jpg")
        self.assertEqual(
            next_numbered_output_path(self.output_folder, "photo.jpg"),
            self.output_folder / "photo_3.jpg",
        )

    def test_first_free_number_is_used(self):
        self.touch("photo_1.jpg")
        self.touch("photo_3.jpg")
        self.assertEqual(
            next_numbered_output_path(self.output_folder, "photo.jpg"),
            self.output_folder / "photo_2.jpg",
        )

    def test_unrelated_files_do_not_affect_numbering(self):
        self.touch("other_1.jpg")
        self.touch("photo_1.png")
        self.assertEqual(
            next_numbered_output_path(self.output_folder, "photo.jpg"),
            self.output_folder / "photo_1.jpg",
        )

    def test_stems_with_dots_and_spaces_are_kept(self):
        self.touch("my photo.tar_1.jpg")
        self.assertEqual(
            next_numbered_output_path(self.output_folder, "my photo.tar.jpg"),
            self.output_folder / "my photo.tar_2.jpg",
        )

    def test_video_extensions_are_numbered_the_same_way(self):
        self.touch("clip_1.mp4")
        self.assertEqual(
            next_numbered_output_path(self.output_folder, "clip.mp4"),
            self.output_folder / "clip_2.mp4",
        )

    def test_has_numbered_output(self):
        self.assertFalse(has_numbered_output(self.output_folder, "photo.jpg"))
        self.touch("photo.jpg")
        self.touch("photo_abc.jpg")
        self.touch("photo_1a.jpg")
        self.assertFalse(has_numbered_output(self.output_folder, "photo.jpg"))
        self.touch("photo_12.jpg")
        self.assertTrue(has_numbered_output(self.output_folder, "photo.jpg"))

    def test_has_numbered_output_with_missing_folder(self):
        missing = self.output_folder / "does-not-exist"
        self.assertFalse(has_numbered_output(missing, "photo.jpg"))


if __name__ == "__main__":
    unittest.main()
