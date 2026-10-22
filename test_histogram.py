"""Qt 없이 실행 가능한 RGB 히스토그램 계산 단위 테스트."""

import unittest
import numpy as np

from histogram import calculate_rgb_histogram


class HistogramTests(unittest.TestCase):
    def test_rgb_channels(self):
        """R, G, B의 밝기별 픽셀 개수가 정확해야 합니다."""
        pixels = np.array([[[0, 10, 20], [255, 10, 20]]], dtype=np.uint8)
        hist = calculate_rgb_histogram(pixels)
        self.assertEqual(hist.shape, (3, 256))
        self.assertEqual(hist[0, 0], 1)
        self.assertEqual(hist[0, 255], 1)
        self.assertEqual(hist[1, 10], 2)
        self.assertEqual(hist[2, 20], 2)
        self.assertEqual(hist.sum(), 6)

    def test_transparent_pixels_excluded(self):
        """완전 투명한 RGBA 픽셀은 세지 않습니다."""
        pixels = np.array([[[10, 20, 30, 255], [250, 240, 230, 0]]], dtype=np.uint8)
        hist = calculate_rgb_histogram(pixels)
        self.assertEqual(hist.sum(), 3)
        self.assertEqual(hist[0, 250], 0)
        self.assertEqual(hist[0, 10], 1)

    def test_empty_image(self):
        hist = calculate_rgb_histogram(np.empty((0, 0, 3), dtype=np.uint8))
        self.assertEqual(hist.shape, (3, 256))
        self.assertEqual(hist.sum(), 0)

    def test_invalid_dimensions(self):
        with self.assertRaises(ValueError):
            calculate_rgb_histogram(np.zeros((10, 10), dtype=np.uint8))

    def test_invalid_dtype(self):
        with self.assertRaises(TypeError):
            calculate_rgb_histogram(np.zeros((2, 2, 3), dtype=np.float32))


if __name__ == "__main__":
    unittest.main()
