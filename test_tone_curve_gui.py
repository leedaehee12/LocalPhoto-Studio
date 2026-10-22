
"""톤 커브 GUI와 EditorController의 연동 테스트"""

import unittest

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QImage
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from main import MainWindow
from models import IDENTITY_CURVE


class ToneCurveGuiTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # 기존 QApplication이 있으면 재사용합니다.
        cls.app = (
            QApplication.instance()
            or QApplication([])
        )

    def test_curve_click_undo_redo(self):
        """
        제어점 추가가 이력 한 단계로 기록되고
        Undo/Redo로 복구되는지 확인합니다.
        """

        window = MainWindow()

        try:
            window.show()
            self.app.processEvents()

            # 파일 대화상자 없이 작은 테스트 이미지 준비
            image = QImage(
                32, 32,
                QImage.Format.Format_RGBA8888
            )
            image.fill(QColor(128, 128, 128))

            window.original_image = image
            window._sync_controls()

            widget = window.curve_widget
            area = widget._graph_rect()

            # 그래프의 가운데보다 위쪽을 클릭합니다.
            # 대략 입력 128, 출력 191에 해당합니다.
            position = QPoint(
                round(area.left() + area.width() / 2),
                round(area.bottom() - area.height() * 0.75)
            )

            QTest.mouseClick(
                widget,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
                position
            )

            # 새로운 중간 제어점이 생성되어야 합니다.
            points = window.controller.settings.curve_points

            self.assertEqual(len(points), 3)

            # 이력은 초기 상태 + 편집 결과 = 2개
            self.assertEqual(
                window.controller.history.length,
                2
            )

            # Undo 실행 시 기본 직선으로 복원
            window.undo_adjustments()

            self.assertEqual(
                window.controller.settings.curve_points,
                IDENTITY_CURVE
            )

            # Redo 실행 시 편집된 제어점 복원
            window.redo_adjustments()

            self.assertEqual(
                window.controller.settings.curve_points,
                points
            )

        finally:
            window.close()


if __name__ == "__main__":
    unittest.main()
