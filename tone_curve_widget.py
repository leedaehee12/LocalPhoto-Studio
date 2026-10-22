
"""
LocalPhoto Studio - 톤 커브 편집 위젯

담당 기능:
1. 톤 커브와 제어점 그리기
2. 마우스로 제어점 추가 및 이동
3. 우클릭으로 중간 제어점 삭제
4. 편집 시작/변경/종료 Qt 신호 발생

이미지 픽셀을 직접 보정하지 않습니다.
"""

from PySide6.QtCore import QPointF, Qt, Signal

from PySide6.QtGui import (
    QColor,
    QPainter,
    QPainterPath,
    QPen
)

from PySide6.QtWidgets import QWidget

from models import CurvePoints, IDENTITY_CURVE
from tone_curve import build_curve_lut


class ToneCurveWidget(QWidget):
    """
    0~255 밝기 범위를 편집하는 그래프 위젯입니다.

    왼쪽 아래: 입력 0, 출력 0
    오른쪽 위: 입력 255, 출력 255
    """

    # 마우스 입력의 시작과 종료를 알리는 신호입니다.
    editStarted = Signal()
    editFinished = Signal()

    # 불변 튜플 형태의 제어점 목록을 전달합니다.
    pointsChanged = Signal(object)

    # 그래프 바깥 여백과 클릭 판정 반경(px)
    MARGIN = 16
    HIT_RADIUS = 9

    def __init__(self, parent=None):
        super().__init__(parent)

        # 현재 제어점들의 불변 튜플
        self._points: CurvePoints = IDENTITY_CURVE

        # 마우스로 이동 중인 제어점 인덱스
        # 드래그 중이 아니라면 None
        self._drag_index: int | None = None

        self.setMinimumSize(190, 190)

        self.setToolTip(
            "좌클릭: 제어점 추가 / "
            "드래그: 이동 / "
            "우클릭: 중간점 삭제"
        )

    def set_points(self, points: CurvePoints):
        """
        외부 모델의 제어점을 위젯에 반영합니다.

        Undo/Redo 또는 초기화할 때 사용합니다.

        중요:
        여기서는 pointsChanged를 발생시키지 않습니다.
        그렇지 않으면 프로그램이 적용한 값을
        새로운 사용자 편집으로 오인할 수 있습니다.
        """

        # 잘못된 제어점이 넘어오면 예외 발생
        build_curve_lut(points)

        self._points = points
        self._drag_index = None
        self.update()

    def _graph_rect(self):
        """실제 곡선이 그려지는 사각형을 반환합니다."""

        return self.rect().adjusted(
            self.MARGIN,
            self.MARGIN,
            -self.MARGIN,
            -self.MARGIN
        )

    def _to_screen(
        self,
        point: tuple[int, int]
    ) -> QPointF:
        """
        톤 커브 좌표(0~255)를
        QWidget 화면 좌표(px)로 변환합니다.
        """

        area = self._graph_rect()
        x, y = point

        # 입력 x는 왼쪽에서 오른쪽으로 증가
        screen_x = (
            area.left()
            + x * area.width() / 255.0
        )

        # 출력 y는 아래에서 위로 증가
        # 화면의 y 좌표와 방향이 반대입니다.
        screen_y = (
            area.bottom()
            - y * area.height() / 255.0
        )

        return QPointF(screen_x, screen_y)

    def _from_screen(
        self,
        position: QPointF
    ) -> tuple[int, int]:
        """
        마우스 위치(px)를
        톤 커브 좌표(0~255)로 변환합니다.
        """

        area = self._graph_rect()

        x = round(
            255
            * (position.x() - area.left())
            / max(1, area.width())
        )

        y = round(
            255
            * (area.bottom() - position.y())
            / max(1, area.height())
        )

        # 마우스가 영역을 벗어나도
        # 유효한 밝기 범위를 유지합니다.
        x = max(0, min(255, x))
        y = max(0, min(255, y))

        return x, y

    def _hit_test(
        self,
        position: QPointF
    ) -> int | None:
        """
        클릭 위치 근처에 제어점이 있는지 확인합니다.

        반환:
            제어점 인덱스(int) 또는 None
        """

        for index, point in enumerate(self._points):

            center = self._to_screen(point)

            # 마우스와 제어점 사이의 거리 제곱
            distance_sq = (
                (position.x() - center.x()) ** 2
                + (position.y() - center.y()) ** 2
            )

            if distance_sq <= self.HIT_RADIUS ** 2:
                return index

        return None

    def mousePressEvent(self, event):
        """
        마우스 버튼을 누를 때 실행됩니다.
        """

        # ===== 우클릭: 중간 제어점 삭제 =====

        if event.button() == Qt.MouseButton.RightButton:

            index = self._hit_test(event.position())

            # 양 끝 제어점은 삭제할 수 없습니다.
            if (
                index is not None
                and 0 < index < len(self._points) - 1
            ):
                self.editStarted.emit()

                self._points = (
                    self._points[:index]
                    + self._points[index + 1:]
                )

                self.pointsChanged.emit(self._points)
                self.editFinished.emit()

                self.update()

            event.accept()
            return

        # ===== 좌클릭: 제어점 선택 또는 추가 =====

        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return

        index = self._hit_test(event.position())

        # 값 변경 전에 편집 시작을 알립니다.
        self.editStarted.emit()

        if index is None:

            x, y = self._from_screen(event.position())

            # 제어점의 x 좌표는 중복될 수 없습니다.
            existing_x = {
                point[0] for point in self._points
            }

            if x in existing_x or x in (0, 255):
                self.editFinished.emit()
                event.accept()
                return

            # 새 제어점을 입력 밝기 순으로 정렬
            points = sorted(
                (*self._points, (x, y))
            )

            self._points = tuple(points)

            # 새로 추가한 점의 인덱스
            index = self._points.index((x, y))

            self.pointsChanged.emit(self._points)

        # 선택한 점을 드래그 대상으로 지정
        self._drag_index = index

        self.update()
        event.accept()

    def mouseMoveEvent(self, event):
        """드래그 중인 제어점의 위치를 변경합니다."""

        if self._drag_index is None:
            super().mouseMoveEvent(event)
            return

        index = self._drag_index

        x, y = self._from_screen(event.position())

        if index == 0:
            # 첫 번째 제어점의 입력값은 항상 0
            x = 0

        elif index == len(self._points) - 1:
            # 마지막 제어점의 입력값은 항상 255
            x = 255

        else:
            # 중간 제어점은 양옆의 점을
            # 가로질러 이동하지 못하게 합니다.
            x = max(
                self._points[index - 1][0] + 1,
                x
            )

            x = min(
                self._points[index + 1][0] - 1,
                x
            )

        new_point = (x, y)

        if self._points[index] != new_point:

            # 불변 튜플을 직접 수정하지 않고
            # 리스트로 복사한 뒤 새 튜플 생성
            updated = list(self._points)

            updated[index] = new_point

            self._points = tuple(updated)

            # 현재 편집값을 GUI에 전달
            self.pointsChanged.emit(self._points)

            self.update()

        event.accept()

    def mouseReleaseEvent(self, event):
        """마우스를 놓으면 한 번의 편집을 종료합니다."""

        if (
            event.button() == Qt.MouseButton.LeftButton
            and self._drag_index is not None
        ):

            self._drag_index = None

            # GUI가 commit_edit()을 호출할 수 있게 알림
            self.editFinished.emit()

            self.update()
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        """Qt 화면에 배경, 그리드, 곡선, 제어점을 그립니다."""

        painter = QPainter(self)

        try:
            painter.setRenderHint(
                QPainter.RenderHint.Antialiasing,
                True
            )

            painter.fillRect(
                self.rect(),
                QColor("#22262d")
            )

            area = self._graph_rect()

            if area.width() < 2 or area.height() < 2:
                return

            # ===== 1. 격자선 =====

            painter.setPen(
                QPen(QColor(255, 255, 255, 40), 1)
            )

            for fraction in (0, 0.25, 0.5, 0.75, 1):

                x = round(
                    area.left()
                    + fraction * area.width()
                )

                y = round(
                    area.top()
                    + fraction * area.height()
                )

                painter.drawLine(
                    x, area.top(),
                    x, area.bottom()
                )

                painter.drawLine(
                    area.left(), y,
                    area.right(), y
                )

            # ===== 2. 기본 항등 커브 =====

            painter.setPen(
                QPen(
                    QColor(190, 190, 190, 100),
                    1,
                    Qt.PenStyle.DashLine
                )
            )

            painter.drawLine(
                self._to_screen((0, 0)),
                self._to_screen((255, 255))
            )

            # ===== 3. 현재 커브 =====

            # 실제 보정 엔진과 동일한 LUT 사용
            lut = build_curve_lut(self._points)

            path = QPainterPath()

            for x, output in enumerate(lut):

                position = self._to_screen(
                    (x, int(output))
                )

                if x == 0:
                    path.moveTo(position)
                else:
                    path.lineTo(position)

            painter.setPen(
                QPen(QColor("#54c6ee"), 2.5)
            )

            painter.drawPath(path)

            # ===== 4. 제어점 표시 =====

            painter.setPen(
                QPen(QColor("#ffffff"), 1.5)
            )

            painter.setBrush(
                QColor("#54c6ee")
            )

            for point in self._points:
                painter.drawEllipse(
                    self._to_screen(point),
                    5,
                    5
                )

        finally:
            painter.end()
