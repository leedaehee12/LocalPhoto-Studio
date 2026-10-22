
"""톤 커브 계산 기능 단위 테스트"""

import unittest
import numpy as np

from tone_curve import (
    build_curve_lut,
    apply_curve_pixels
)


class TestToneCurve(unittest.TestCase):

    def test_identity(self):
        """기본 직선 커브는 모든 픽셀값을 유지합니다."""

        lut = build_curve_lut(
            ((0, 0), (255, 255))
        )

        expected = np.arange(
            256, dtype=np.uint8
        )

        np.testing.assert_array_equal(lut, expected)

    def test_brighten(self):
        """중간 밝기를 올리면 더 밝게 변환됩니다."""

        lut = build_curve_lut(
            ((0, 0), (128, 180), (255, 255))
        )

        self.assertEqual(int(lut[128]), 180)

        # 양 끝의 픽셀값은 그대로 유지
        self.assertEqual(int(lut[0]), 0)
        self.assertEqual(int(lut[255]), 255)

    def test_s_curve(self):
        """S 커브는 그림자를 낮추고 하이라이트를 높입니다."""

        lut = build_curve_lut(
            (
                (0, 0),
                (64, 48),
                (128, 128),
                (192, 214),
                (255, 255),
            )
        )

        self.assertLess(int(lut[64]), 64)
        self.assertEqual(int(lut[128]), 128)
        self.assertGreater(int(lut[192]), 192)

    def test_preserve_alpha_and_source(self):
        """알파 채널과 원본 픽셀값이 유지됩니다."""

        source = np.array(
            [[[64, 128, 192, 77]]],
            dtype=np.uint8
        )

        original = source.copy()

        lut = build_curve_lut(
            ((0, 0), (128, 180), (255, 255))
        )

        result = apply_curve_pixels(source, lut)

        self.assertEqual(int(result[0, 0, 1]), 180)
        self.assertEqual(int(result[0, 0, 3]), 77)

        np.testing.assert_array_equal(
            source, original
        )

    def test_duplicate_input(self):
        """같은 x 좌표의 제어점은 허용하지 않습니다."""

        with self.assertRaises(ValueError):
            build_curve_lut(
                (
                    (0, 0),
                    (128, 100),
                    (128, 180),
                    (255, 255)
                )
            )

    def test_invalid_range(self):
        """0~255 범위를 벗어난 제어점을 거부합니다."""

        with self.assertRaises(ValueError):
            build_curve_lut(
                ((0, 0), (300, 255))
            )


if __name__ == "__main__":
    unittest.main()
