
"""
LocalPhoto Studio - 톤 커브 통합 테스트

검증 대상:
1. 톤 커브가 processing.py에 전달되는지
2. 기본 보정 상태에서 기존 픽셀이 유지되는지
3. 알파 채널과 원본이 보존되는지
4. 파일 내보내기에 톤 커브가 반영되는지
5. Undo/Redo가 커브 제어점을 복원하는지
"""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from PySide6.QtGui import QColor, QImage

from models import (
    AdjustmentSettings,
    IDENTITY_CURVE
)
from processing import apply_adjustments
from export_worker import save_adjusted_image
from editor_controller import EditorController


# 중간 회색(128)을 180으로 변환하는 밝기 커브
BRIGHT_CURVE = (
    (0, 0),
    (128, 180),
    (255, 255)
)


class CurvePipelineTests(unittest.TestCase):

    def make_image(self) -> QImage:
        """
        한 픽셀짜리 RGBA 테스트 이미지를 생성합니다.

        R=128, G=128, B=128, A=77
        """

        image = QImage(
            1,
            1,
            QImage.Format.Format_RGBA8888
        )

        image.setPixelColor(
            0, 0,
            QColor(128, 128, 128, 77)
        )

        return image

    def test_identity_curve(self):
        """기본 커브라면 RGB 값이 그대로 유지됩니다."""

        source = self.make_image()

        settings = AdjustmentSettings()

        result = apply_adjustments(
            source,
            **settings.as_kwargs()
        )

        self.assertEqual(
            result.pixelColor(0, 0).getRgb(),
            source.pixelColor(0, 0).getRgb()
        )

    def test_bright_curve(self):
        """중간 밝기 128이 180으로 변환되어야 합니다."""

        source = self.make_image()

        settings = AdjustmentSettings(
            curve_points=BRIGHT_CURVE
        )

        result = apply_adjustments(
            source,
            **settings.as_kwargs()
        )

        pixel = result.pixelColor(0, 0)

        self.assertEqual(pixel.red(), 180)
        self.assertEqual(pixel.green(), 180)
        self.assertEqual(pixel.blue(), 180)

    def test_alpha_and_original(self):
        """커브 적용 후에도 알파와 원본을 보존합니다."""

        source = self.make_image()

        before = source.pixelColor(
            0, 0
        ).getRgb()

        result = apply_adjustments(
            source,
            curve_points=BRIGHT_CURVE
        )

        # 투명도는 변경하지 않습니다.
        self.assertEqual(
            result.pixelColor(0, 0).alpha(),
            77
        )

        # 원본 QImage는 변경되지 않아야 합니다.
        self.assertEqual(
            source.pixelColor(0, 0).getRgb(),
            before
        )

    def test_export_matches_preview(self):
        """
        같은 설정으로 보정한 미리보기와
        PNG 저장 결과가 일치하는지 검사합니다.

        여기서는 1x1 동일 해상도를 사용합니다.
        """

        source = self.make_image()

        settings = AdjustmentSettings(
            curve_points=BRIGHT_CURVE
        )

        # 화면 미리보기에서 사용하는 계산 경로
        preview = apply_adjustments(
            source,
            **settings.as_kwargs()
        )

        # 임시 폴더는 테스트 종료 시 자동 삭제
        with TemporaryDirectory() as folder:

            path = Path(folder) / "curve_test.png"

            # 기존 원본 해상도 저장 엔진 호출
            save_adjusted_image(
                source,
                str(path),
                settings
            )

            self.assertTrue(path.exists())

            saved = QImage(str(path))

            self.assertFalse(saved.isNull())

            # PNG는 무손실이므로 픽셀값 일치
            self.assertEqual(
                saved.pixelColor(0, 0).getRgb(),
                preview.pixelColor(0, 0).getRgb()
            )

    def test_undo_redo_curve(self):
        """Undo/Redo가 커브 제어점을 정확히 복원합니다."""

        controller = EditorController()

        settings = AdjustmentSettings(
            curve_points=BRIGHT_CURVE
        )

        # 톤 커브를 하나의 편집 작업으로 기록
        controller.begin_edit()

        controller.set_settings(settings)

        controller.commit_edit()

        # Undo 이전에는 변경된 커브가 적용됨
        self.assertEqual(
            controller.settings.curve_points,
            BRIGHT_CURVE
        )

        # Undo: 기본 직선으로 복원
        controller.undo()

        self.assertEqual(
            controller.settings.curve_points,
            IDENTITY_CURVE
        )

        # Redo: 밝기 커브로 복원
        controller.redo()

        self.assertEqual(
            controller.settings.curve_points,
            BRIGHT_CURVE
        )

    def test_invalid_curve(self):
        """입력 좌표가 중복된 제어점을 거부합니다."""

        source = self.make_image()

        with self.assertRaises(ValueError):
            apply_adjustments(
                source,
                curve_points=(
                    (0, 0),
                    (128, 80),
                    (128, 180),
                    (255, 255)
                )
            )


if __name__ == "__main__":
    unittest.main()
