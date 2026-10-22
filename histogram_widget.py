"""미리보기 이미지의 RGB 히스토그램을 그리는 PySide6 전용 위젯.

히스토그램 계산 알고리즘은 histogram.py가 담당합니다.
이 위젯은 QImage를 NumPy 배열로 연결하고, 계산 결과를 그리기만 합니다.
"""

import numpy as np
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from histogram import calculate_rgb_histogram


class HistogramWidget(QWidget):
    """보정된 미리보기 이미지의 RGB 밝기 분포를 시각화합니다."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        # 각 행은 R/G/B 채널, 256개 열은 밝기별 픽셀 개수입니다.
        self._counts = np.zeros((3, 256), dtype=np.int64)
        self.setFixedHeight(160)
        self.setToolTip(
            "현재 보정 미리보기의 RGB 분포입니다. "
            "왼쪽은 그림자(0), 오른쪽은 밝은 영역(255)입니다."
        )

    def set_image(self, image: QImage) -> None:
        """QImage를 RGBA 픽셀로 변환하여 히스토그램을 갱신합니다.

        image: 화면에 표시된 보정 결과 QImage.
        처리 부하를 낮추기 위해 원본 대신 미리보기를 사용합니다.
        """
        if image.isNull():
            self._counts.fill(0)
            self.update()
            return

        # bytesPerLine을 사용하여 메모리 행 패딩을 안전하게 제외합니다.
        rgba = image.convertToFormat(QImage.Format.Format_RGBA8888)
        height, width = rgba.height(), rgba.width()
        bytes_per_line = rgba.bytesPerLine()

        pixels = np.frombuffer(rgba.constBits(), dtype=np.uint8)
        pixels = pixels.reshape(height, bytes_per_line)
        pixels = pixels[:, :width * 4].reshape(height, width, 4)

        self._counts = calculate_rgb_histogram(pixels)
        self.update()  # Qt 페인트 이벤트 예약

    def paintEvent(self, event) -> None:
        """세 개의 반투명 선 그래프로 R/G/B 분포를 표시합니다."""
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.fillRect(self.rect(), QColor("#22262d"))

            graph = self.rect().adjusted(10, 12, -10, -12)
            if graph.width() < 2 or graph.height() < 2:
                return

            # 밝기 기준선 0%, 25%, 50%, 75%, 100%
            painter.setPen(QPen(QColor(255, 255, 255, 35), 1))
            for step in range(5):
                x = graph.left() + graph.width() * step / 4
                painter.drawLine(round(x), graph.top(), round(x), graph.bottom())

            maximum = int(self._counts.max())
            if maximum == 0:
                return

            # 로그 스케일로 작은 빈도도 눈에 보이게 합니다.
            log_max = np.log1p(maximum)
            colors = (
                QColor(255, 90, 90, 185),
                QColor(90, 230, 110, 185),
                QColor(90, 155, 255, 185),
            )
            for channel, color in enumerate(colors):
                heights = np.log1p(self._counts[channel]) / log_max
                path = QPainterPath()
                for bucket in range(256):
                    x = graph.left() + graph.width() * bucket / 255.0
                    y = graph.bottom() - graph.height() * float(heights[bucket])
                    if bucket == 0:
                        path.moveTo(x, y)
                    else:
                        path.lineTo(x, y)
                painter.setPen(QPen(color, 1.35))
                painter.drawPath(path)
        finally:
            painter.end()
