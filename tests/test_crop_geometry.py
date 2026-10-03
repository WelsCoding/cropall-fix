import unittest

from crop_geometry import normalize_crop_coords, resize_dimensions


class CropGeometryTests(unittest.TestCase):
    def dimensions(self, coords):
        return coords[2] - coords[0], coords[3] - coords[1]

    def test_square_ratio_constrains_selection(self):
        coords = normalize_crop_coords(
            (20, 30, 320, 230), (400, 300), aspect=(1, 1)
        )
        self.assertEqual(self.dimensions(coords)[0], self.dimensions(coords)[1])

    def test_free_selection_keeps_non_square_shape(self):
        coords = normalize_crop_coords((20, 30, 320, 230), (400, 300))
        self.assertNotEqual(self.dimensions(coords)[0], self.dimensions(coords)[1])

    def test_crop_dimensions_obey_divisor_and_preserve_common_ratio(self):
        coords = normalize_crop_coords(
            (10, 20, 310, 220),
            (400, 300),
            divisor=8,
            aspect=(3, 2),
        )
        width, height = self.dimensions(coords)
        self.assertEqual(width % 8, 0)
        self.assertEqual(height % 8, 0)
        self.assertEqual(width * 2, height * 3)

    def test_video_alignment_applies_to_size_and_offset(self):
        coords = normalize_crop_coords(
            (3, 5, 119, 91), (128, 96), divisor=3, aspect=None, alignment=2
        )
        left, top, right, bottom = coords
        self.assertEqual(left % 2, 0)
        self.assertEqual(top % 2, 0)
        self.assertEqual((right - left) % 6, 0)
        self.assertEqual((bottom - top) % 6, 0)
        self.assertGreaterEqual(left, 0)
        self.assertGreaterEqual(top, 0)
        self.assertLessEqual(right, 128)
        self.assertLessEqual(bottom, 96)

    def test_resize_dimensions_do_not_upscale_and_obey_divisor(self):
        width, height = resize_dimensions((1600, 900), (1920, 1080), divisor=7)
        self.assertLessEqual(width, 1600)
        self.assertLessEqual(height, 900)
        self.assertEqual(width % 7, 0)
        self.assertEqual(height % 7, 0)
        self.assertAlmostEqual(width / height, 16 / 9, places=2)

    def test_impossible_divisor_is_reported(self):
        with self.assertRaises(ValueError):
            normalize_crop_coords((0, 0, 8, 8), (8, 8), divisor=9)


if __name__ == "__main__":
    unittest.main()
