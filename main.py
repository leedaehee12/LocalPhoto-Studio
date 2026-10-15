
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

from processing import apply_exposure


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("LocalPhoto Studio")
        self.resize(1200, 800)

        # 원본 이미지와 미리보기 캐시
        self.original_image = QImage()
        self.preview_source = QImage()
        self.preview_target_size = None

        # ===== 이미지 표시 영역 =====
        self.image_label = QLabel(
            "파일 → 열기 (Ctrl+O)로 사진을 불러오세요."
        )

        self.image_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.image_label.setStyleSheet(
            "background: #252525; color: #ddd; font-size: 16px;"
        )

        self.image_label.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Ignored
        )

        self.image_label.setMinimumSize(1, 1)
        self.image_label.installEventFilter(self)

        # ===== 오른쪽 보정 패널 =====
        panel = QWidget()
        panel.setFixedWidth(260)

        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(16, 20, 16, 20)
        panel_layout.setSpacing(12)

        panel_layout.addWidget(QLabel("기본 보정"))
        panel_layout.addWidget(QLabel("노출 (Exposure)"))

        # 현재 노출 수치
        self.exposure_value_label = QLabel("+0.0 EV")
        panel_layout.addWidget(self.exposure_value_label)

        # 노출 조절 슬라이더
        self.exposure_slider = QSlider(
            Qt.Orientation.Horizontal
        )

        self.exposure_slider.setRange(-30, 30)
        self.exposure_slider.setValue(0)

        self.exposure_slider.valueChanged.connect(
            self.on_exposure_changed
        )

        panel_layout.addWidget(self.exposure_slider)

        # 초기화 버튼
        reset_button = QPushButton("노출 초기화")
        reset_button.clicked.connect(
            lambda: self.exposure_slider.setValue(0)
        )

        panel_layout.addWidget(reset_button)
        panel_layout.addStretch()

        # ===== 메인 레이아웃 =====
        central = QWidget()
        layout = QHBoxLayout(central)

        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self.image_label, 1)
        layout.addWidget(panel)

        self.setCentralWidget(central)

        # 메뉴 및 상태바
        self.create_menu()
        self.statusBar().showMessage("준비 완료")

    def create_menu(self):
        file_menu = self.menuBar().addMenu("파일")

        open_action = QAction("열기", self)
        open_action.setShortcut(
            QKeySequence.StandardKey.Open
        )
        open_action.triggered.connect(self.open_image)

        file_menu.addAction(open_action)

        exit_action = QAction("종료", self)
        exit_action.triggered.connect(self.close)

        file_menu.addSeparator()
        file_menu.addAction(exit_action)

    def open_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "사진 열기",
            "",
            "이미지 (*.jpg *.jpeg *.png *.bmp *.webp);;"
            "모든 파일 (*)"
        )

        if not file_path:
            return

        reader = QImageReader(file_path)
        reader.setAutoTransform(True)

        image = reader.read()

        if image.isNull():
            QMessageBox.critical(
                self,
                "오류",
                f"이미지를 불러올 수 없습니다.\n"
                f"{reader.errorString()}"
            )
            return

        # 새 원본 저장 및 미리보기 캐시 초기화
        self.original_image = image
        self.preview_source = QImage()
        self.preview_target_size = None

        # 새 사진을 열면 노출값 초기화
        self.exposure_slider.setValue(0)

        filename = Path(file_path).name

        self.setWindowTitle(
            f"{filename} - LocalPhoto Studio"
        )

        self.update_preview()

        self.statusBar().showMessage(
            f"{filename} | "
            f"{image.width()} × {image.height()} px"
        )

    def on_exposure_changed(self, slider_value):
        """슬라이더 값 변경 시 실행"""

        ev = slider_value / 10.0

        self.exposure_value_label.setText(
            f"{ev:+.1f} EV"
        )

        self.update_preview()

    def update_preview(self):
        """미리보기 이미지를 갱신"""

        if self.original_image.isNull():
            return

        target_size = self.image_label.size()

        if (
            target_size.width() < 2
            or target_size.height() < 2
        ):
            return

        # 창 크기가 바뀐 경우에만 원본 다시 축소
        if (
            self.preview_source.isNull()
            or self.preview_target_size != target_size
        ):
            self.preview_source = self.original_image.scaled(
                target_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

            self.preview_target_size = target_size

        # 현재 노출 설정을 미리보기에 적용
        ev = self.exposure_slider.value() / 10.0

        preview = apply_exposure(
            self.preview_source,
            ev
        )

        self.image_label.setPixmap(
            QPixmap.fromImage(preview)
        )

    def eventFilter(self, watched, event):
        if (
            watched is self.image_label
            and event.type() == QEvent.Type.Resize
        ):
            self.update_preview()

        return super().eventFilter(watched, event)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
