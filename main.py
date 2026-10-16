
"""
LocalPhoto Studio - 메인 GUI

담당 기능:
- 프로그램 창 구성
- 사진 파일 불러오기
- 보정 슬라이더 값 읽기
- processing.py에 보정 요청
- 결과 이미지를 화면에 표시
"""

import sys
from pathlib import Path

from PySide6.QtCore import Qt, QEvent

from PySide6.QtGui import (
    QAction,
    QImage,
    QImageReader,
    QKeySequence,
    QPixmap,
)

from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

# 같은 폴더의 processing.py에서 보정 함수를 가져옵니다.
from processing import apply_adjustments


class MainWindow(QMainWindow):
    """프로그램의 메인 창입니다."""

    def __init__(self):
        # 부모 클래스인 QMainWindow의 초기화 수행
        super().__init__()

        self.setWindowTitle("LocalPhoto Studio")
        self.resize(1200, 800)

        # original_image:
        # 파일에서 불러온 원본 QImage 객체
        self.original_image = QImage()

        # preview_source:
        # 화면 크기에 맞춰 축소한 원본 이미지 캐시
        self.preview_source = QImage()

        # preview_size:
        # 캐시 생성 당시의 (가로, 세로) 크기
        # 아직 생성 전이므로 None
        self.preview_size = None

        # ===== 사진 표시 영역 =====

        self.image_label = QLabel(
            "파일 → 열기 (Ctrl+O)로 사진을 불러오세요."
        )

        self.image_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.image_label.setStyleSheet(
            "background-color: #252525;"
            "color: #dddddd;"
            "font-size: 16px;"
        )

        # 이미지 크기에 의해 창이 강제로 커지는 것을 방지
        self.image_label.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Ignored
        )

        self.image_label.setMinimumSize(1, 1)

        # 이미지 표시 영역 크기 변경 이벤트 감지
        self.image_label.installEventFilter(self)

        # ===== 오른쪽 보정 패널 =====

        panel = QWidget()
        panel.setFixedWidth(280)

        # 패널 내부 위젯을 위에서 아래로 배치합니다.
        panel_layout = QVBoxLayout(panel)

        # 왼쪽, 위, 오른쪽, 아래 여백
        panel_layout.setContentsMargins(16, 20, 16, 20)

        # 위젯 사이 간격
        panel_layout.setSpacing(14)

        panel_layout.addWidget(QLabel("기본 보정"))

        # add_slider()는 두 객체를 반환합니다.
        # 첫 번째: QSlider 객체
        # 두 번째: 현재 수치를 표시하는 QLabel 객체

        self.exposure_slider, self.exposure_label = (
            self.add_slider(
                panel_layout, "노출", -30, 30
            )
        )

        self.contrast_slider, self.contrast_label = (
            self.add_slider(
                panel_layout, "대비", -100, 100
            )
        )

        self.saturation_slider, self.saturation_label = (
            self.add_slider(
                panel_layout, "채도", -100, 100
            )
        )

        self.warmth_slider, self.warmth_label = (
            self.add_slider(
                panel_layout, "색온도 (간이)", -100, 100
            )
        )

        # ===== 초기화 버튼 =====

        reset_button = QPushButton("모든 보정 초기화")

        # 버튼 클릭 시 reset_adjustments() 실행
        reset_button.clicked.connect(
            self.reset_adjustments
        )

        panel_layout.addWidget(reset_button)

        # 남는 공간을 아래쪽에 배치합니다.
        panel_layout.addStretch()

        # ===== 중앙 레이아웃 =====

        central = QWidget()

        # 사진과 패널을 좌우로 배치
        main_layout = QHBoxLayout(central)

        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 사진 영역은 남는 가로 공간을 사용합니다.
        main_layout.addWidget(self.image_label, 1)

        # 보정 패널은 오른쪽에 배치합니다.
        main_layout.addWidget(panel)

        self.setCentralWidget(central)

        # 메뉴, 수치 표시, 상태바 초기화
        self.create_menu()
        self.update_value_labels()
        self.statusBar().showMessage("준비 완료")

    def add_slider(
        self,
        layout: QVBoxLayout,
        title: str,
        low: int,
        high: int
    ):
        """
        보정 슬라이더 하나를 생성합니다.

        layout:
            슬라이더가 추가될 Qt 레이아웃

        title:
            화면에 표시할 항목 이름(str)

        low:
            슬라이더 최솟값(int)

        high:
            슬라이더 최댓값(int)

        반환값:
            (QSlider 객체, QLabel 객체)
        """

        # 항목 이름과 값을 가로로 배치합니다.
        label_row = QHBoxLayout()

        title_label = QLabel(title)
        value_label = QLabel("0")

        label_row.addWidget(title_label)
        label_row.addStretch()
        label_row.addWidget(value_label)

        layout.addLayout(label_row)

        # 가로 방향으로 움직이는 슬라이더 생성
        slider = QSlider(Qt.Orientation.Horizontal)

        slider.setRange(low, high)
        slider.setValue(0)

        # 값이 바뀌면 보정 갱신 함수를 호출합니다.
        slider.valueChanged.connect(
            self.on_adjustments_changed
        )

        layout.addWidget(slider)

        # 생성한 두 객체를 호출한 함수에 돌려줍니다.
        return slider, value_label

    def create_menu(self):
        """파일 메뉴를 생성합니다."""

        file_menu = self.menuBar().addMenu("파일")

        open_action = QAction("열기", self)

        open_action.setShortcut(
            QKeySequence.StandardKey.Open
        )

        open_action.triggered.connect(
            self.open_image
        )

        file_menu.addAction(open_action)

        exit_action = QAction("종료", self)

        exit_action.triggered.connect(
            self.close
        )

        file_menu.addSeparator()
        file_menu.addAction(exit_action)

    def open_image(self):
        """사진 파일을 읽고 원본 이미지로 저장합니다."""

        # file_path:
        # 사용자가 선택한 파일의 전체 경로(str)
        # 취소하면 빈 문자열을 반환합니다.
        #
        # _selected_filter:
        # 선택된 파일 형식 필터 문자열
        # 현재 사용하지 않으므로 앞에 _를 붙입니다.
        file_path, _selected_filter = (
            QFileDialog.getOpenFileName(
                self,
                "사진 열기",
                "",
                "이미지 (*.jpg *.jpeg *.png *.bmp *.webp);;"
                "모든 파일 (*)"
            )
        )

        if not file_path:
            return

        # 파일을 읽는 Qt 객체 생성
        reader = QImageReader(file_path)

        # EXIF 방향 정보를 적용합니다.
        reader.setAutoTransform(True)

        # loaded_image는 QImage 객체입니다.
        # 불러오기에 실패하면 빈 QImage가 반환됩니다.
        loaded_image = reader.read()

        if loaded_image.isNull():
            QMessageBox.critical(
                self,
                "오류",
                "이미지를 불러올 수 없습니다.\n"
                f"{reader.errorString()}"
            )
            return

        # 새 사진을 원본으로 저장합니다.
        self.original_image = loaded_image

        # 이전 사진의 축소 이미지 캐시를 제거합니다.
        self.preview_source = QImage()
        self.preview_size = None

        # 이전 사진에 적용한 보정을 초기화합니다.
        self.reset_adjustments()

        # 전체 경로에서 파일명만 추출합니다.
        filename = Path(file_path).name

        self.setWindowTitle(
            f"{filename} - LocalPhoto Studio"
        )

        self.statusBar().showMessage(
            f"{filename} | "
            f"{loaded_image.width()} × "
            f"{loaded_image.height()} px"
        )

    def update_value_labels(self):
        """현재 슬라이더의 값을 화면에 표시합니다."""

        # QSlider.value()는 int를 반환합니다.
        # EV는 10으로 나누어 float로 변환합니다.
        exposure_ev = (
            self.exposure_slider.value() / 10.0
        )

        self.exposure_label.setText(
            f"{exposure_ev:+.1f} EV"
        )

        self.contrast_label.setText(
            f"{self.contrast_slider.value():+d}"
        )

        self.saturation_label.setText(
            f"{self.saturation_slider.value():+d}"
        )

        self.warmth_label.setText(
            f"{self.warmth_slider.value():+d}"
        )

    def on_adjustments_changed(self, _value: int):
        """
        슬라이더 값이 변경되면 Qt가 호출합니다.

        _value:
            방금 움직인 슬라이더의 정수 값입니다.

        이번에는 네 슬라이더의 현재값을 모두 다시
        읽으므로 이 인수를 직접 사용하지 않습니다.
        """

        # 슬라이더 옆 숫자를 갱신합니다.
        self.update_value_labels()

        # 보정된 미리보기를 다시 계산합니다.
        self.update_preview()

    def reset_adjustments(self):
        """모든 보정 슬라이더를 0으로 초기화합니다."""

        # sliders:
        # 초기화할 QSlider 객체들을 모은 튜플입니다.
        sliders = (
            self.exposure_slider,
            self.contrast_slider,
            self.saturation_slider,
            self.warmth_slider,
        )

        for slider in sliders:
            # blockSignals(True)는 Qt 신호를 일시 차단합니다.
            # 이전 차단 상태를 돌려받아 보관합니다.
            previous_blocked = slider.blockSignals(True)

            slider.setValue(0)

            # 기존 신호 차단 상태로 복구합니다.
            slider.blockSignals(previous_blocked)

        # 네 번 다시 계산하지 않고 한 번만 갱신합니다.
        self.update_value_labels()
        self.update_preview()

    def update_preview(self):
        """현재 보정값을 적용한 사진을 표시합니다."""

        if self.original_image.isNull():
            return

        # 사진 표시 영역의 현재 크기(int)를 읽습니다.
        target_width = self.image_label.width()
        target_height = self.image_label.height()

        if target_width < 2 or target_height < 2:
            return

        # 현재 사진 표시 영역의 크기를 튜플로 저장합니다.
        target_size = (target_width, target_height)

        # 창 크기가 바뀌었다면 캐시를 다시 만듭니다.
        if (
            self.preview_source.isNull()
            or self.preview_size != target_size
        ):
            self.preview_source = (
                self.original_image.scaled(
                    target_width,
                    target_height,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            )

            self.preview_size = target_size

        # ===== 보정 파라미터 읽기 =====

        # exposure_ev는 float입니다.
        exposure_ev = (
            self.exposure_slider.value() / 10.0
        )

        # 나머지는 int입니다.
        contrast = self.contrast_slider.value()
        saturation = self.saturation_slider.value()
        warmth = self.warmth_slider.value()

        # ===== 이미지 엔진 호출 =====

        # adjusted:
        # processing.py가 반환하는 보정된 QImage입니다.
        #
        # image=self.preview_source:
        # 화면용 축소 원본을 함수에 전달합니다.
        adjusted = apply_adjustments(
            image=self.preview_source,
            exposure_ev=exposure_ev,
            contrast=contrast,
            saturation=saturation,
            warmth=warmth
        )

        # QImage를 화면 표시용 QPixmap으로 변환합니다.
        self.image_label.setPixmap(
            QPixmap.fromImage(adjusted)
        )

    def eventFilter(self, watched, event):
        """
        Qt 이벤트를 감지합니다.

        watched:
            이벤트가 발생한 객체입니다.

        event:
            발생한 이벤트의 종류와 정보를 담습니다.
        """

        # 사진 표시 영역의 크기가 변경되었는지 검사
        if (
            watched is self.image_label
            and event.type() == QEvent.Type.Resize
        ):
            self.update_preview()

        # 부모 클래스에도 이벤트를 전달합니다.
        return super().eventFilter(watched, event)


if __name__ == "__main__":

    # QApplication:
    # 사용자 입력, 창 이벤트 등을 관리하는 객체
    app = QApplication(sys.argv)

    # MainWindow 클래스의 인스턴스 생성
    window = MainWindow()

    # 창을 화면에 표시합니다.
    window.show()

    # Qt 이벤트 루프 실행
    # 프로그램 종료 시 종료 코드를 반환합니다.
    sys.exit(app.exec())
