
import tempfile
import unittest

from pathlib import Path

from PySide6.QtGui import QImage, QColor

from export_worker import save_adjusted_image


class ExportTests(unittest.TestCase):

    def setUp(self):
        """
        테스트용 3×2 픽셀 이미지를 생성합니다.
        각 픽셀은 반투명한 붉은색입니다.
        """

        self.source = QImage(
            3, 2,
            QImage.Format.Format_RGBA8888
        )

        self.source.fill(
            QColor(200, 100, 60, 128)
        )

        # 기본 보정 파라미터
        self.settings = {
            "exposure_ev": 0.0,
            "contrast": 0,
            "saturation": 0,
            "warmth": 0,
        }

    def test_png_resolution_and_alpha(self):
        """PNG 저장 시 해상도와 투명도를 보존합니다."""

        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder) / "test.png")

            save_adjusted_image(
                self.source,
                path,
                self.settings
            )

            image = QImage(path)

            self.assertFalse(image.isNull())
            self.assertEqual(image.width(), 3)
            self.assertEqual(image.height(), 2)

            self.assertEqual(
                image.pixelColor(0, 0).alpha(),
                128
            )

    def test_jpeg_resolution(self):
        """JPEG 저장 시 원본 해상도를 유지합니다."""

        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder) / "test.jpg")

            save_adjusted_image(
                self.source,
                path,
                self.settings
            )

            image = QImage(path)

            self.assertFalse(image.isNull())
            self.assertEqual(image.width(), 3)
            self.assertEqual(image.height(), 2)

            # JPEG는 투명도를 보존하지 않습니다.
            self.assertEqual(
                image.pixelColor(0, 0).alpha(),
                255
            )

    def test_source_unchanged(self):
        """저장 후에도 원본 QImage는 변경되지 않아야 합니다."""

        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder) / "test.png")

            settings = self.settings.copy()
            settings["exposure_ev"] = 1.0

            save_adjusted_image(
                self.source,
                path,
                settings
            )

            self.assertEqual(
                self.source.pixelColor(0, 0),
                QColor(200, 100, 60, 128)
            )

    def test_invalid_extension(self):
        """지원하지 않는 파일 형식은 오류를 발생시킵니다."""

        with self.assertRaises(ValueError):
            save_adjusted_image(
                self.source,
                "test.xyz",
                self.settings
            )


if __name__ == "__main__":
    unittest.main()
