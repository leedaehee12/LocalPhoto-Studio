
"""
LocalPhoto Studio 이미지 처리 단위 테스트

한 픽셀짜리 가상 이미지를 생성해서
보정 수식이 정상적으로 작동하는지 검사합니다.
"""

import unittest

from PySide6.QtGui import QColor, QImage
from processing import apply_adjustments


class ProcessingTests(unittest.TestCase):

    def make_image(
        self,
        red: int,
        green: int,
        blue: int,
        alpha: int = 255
    ):
        """지정한 RGBA 색상의 1×1 이미지를 만듭니다."""

        image = QImage(
            1, 1,
            QImage.Format.Format_RGBA8888
        )

        image.setPixelColor(
            0, 0,
            QColor(red, green, blue, alpha)
        )

        return image

    def test_zero_returns_original(self):
        """모든 보정값이 0이면 색상이 같아야 합니다."""

        source = self.make_image(100, 80, 60, 128)
        result = apply_adjustments(source)

        self.assertEqual(
            result.pixelColor(0, 0),
            source.pixelColor(0, 0)
        )

    def test_exposure_lightens(self):
        """노출 +1 EV는 사진을 밝게 해야 합니다."""

        source = self.make_image(90, 90, 90)

        result = apply_adjustments(
            source, exposure_ev=1.0
        )

        self.assertGreater(
            result.pixelColor(0, 0).red(),
            90
        )

    def test_saturation_minus100_grayscale(self):
        """채도 -100은 무채색을 만들어야 합니다."""

        source = self.make_image(190, 100, 40)

        result = apply_adjustments(
            source, saturation=-100
        )

        pixel = result.pixelColor(0, 0)

        self.assertEqual(pixel.red(), pixel.green())
        self.assertEqual(pixel.green(), pixel.blue())

    def test_warmth_red_vs_blue(self):
        """색온도를 높이면 빨강이 파랑보다 강해져야 합니다."""

        source = self.make_image(128, 128, 128)

        result = apply_adjustments(
            source, warmth=60
        )

        pixel = result.pixelColor(0, 0)

        self.assertGreater(
            pixel.red(),
            pixel.blue()
        )

    def test_preserve_source_and_alpha(self):
        """원본과 투명도 값이 유지되어야 합니다."""

        source = self.make_image(
            100, 80, 60, 105
        )

        result = apply_adjustments(
            source,
            contrast=40,
            exposure_ev=1.0,
            saturation=80
        )

        self.assertEqual(
            source.pixelColor(0, 0),
            QColor(100, 80, 60, 105)
        )

        self.assertEqual(
            result.pixelColor(0, 0).alpha(),
            105
        )


if __name__ == "__main__":
    unittest.main()
