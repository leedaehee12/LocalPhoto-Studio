
"""
LocalPhoto Studio: PySide6 GUI.

편집 상태는 EditorController가 관리합니다.
"""

import sys
from pathlib import Path

from PySide6.QtCore import QEvent, Qt, QTimer, Signal
from PySide6.QtGui import (
    QAction,
    QImage,
    QImageReader,
    QKeySequence,
    QPixmap
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
    QWidget
)

from editor_controller import EditorController
from export_worker import ExportThread
from models import AdjustmentSettings
from processing import apply_adjustments
from histogram_widget import HistogramWidget


class EditSlider(QSlider):
    """
    마우스 입력 시작을 QSlider 기본 값 변경보다
    먼저 통보하는 확장 슬라이더입니다.
    """

    # 마우스를 누르는 시점에 전달
    mouse_edit_started = Signal()

    # 마우스를 놓은 뒤 전달
    mouse_edit_finished = Signal()

    def mousePressEvent(self, event) -> None:

        if event.button() == Qt.MouseButton.LeftButton:

            # Qt가 트랙 클릭으로 값을 바꾸기 전에
            # 편집을 시작합니다.
            self.mouse_edit_started.emit()

        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:

        # Qt가 최종 슬라이더 값을 처리합니다.
        super().mouseReleaseEvent(event)

        if event.button() == Qt.MouseButton.LeftButton:
            self.mouse_edit_finished.emit()


class MainWindow(QMainWindow):
    """
    사진과 슬라이더를 보여주고
    입력 의도를 Controller에 전달합니다.
    """

    # 항목명: (최솟값, 최댓값, 화면 표시 제목)
    SLIDER_SPECS = {
        "exposure_ev": (-30, 30, "노출 (EV)"),
        "contrast": (-100, 100, "대비"),
        "saturation": (-100, 100, "채도"),
        "warmth": (-100, 100, "색온도 (간이)"),
    }

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("LocalPhoto Studio")
        self.resize(1200, 800)

        # ===== 편집 상태 =====

        # controller:
        # 편집 중 상태·확정 이력·Undo/Redo 관리자
        self.controller = EditorController(max_steps=100)

        # original_image:
        # 원본 QImage, 처음에는 빈 이미지
        self.original_image = QImage()

        # current_file_path:
        # 현재 사진의 파일 경로 또는 None
        self.current_file_path: Path | None = None

        # preview_source:
        # 화면 크기에 맞춰 축소한 원본 이미지 캐시
        self.preview_source = QImage()

        # preview_size:
        # 캐시 생성 당시의 (너비, 높이) 튜플
        self.preview_size: tuple[int, int] | None = None

        # export_thread:
        # 현재 실행 중인 저장 스레드 또는 None
        self.export_thread: ExportThread | None = None

        # _active_key:
        # 현재 수정 중인 보정 항목의 이름 또는 None
        self._active_key: str | None = None

        # _input_mode:
        # 'mouse': 마우스로 드래그 중
        # 'idle': 키보드/휠 입력 중
        # None: 편집 작업 없음
        self._input_mode: str | None = None

        # ===== 키보드/휠 입력 타이머 =====

        # 마우스 드래그에서는 이 타이머를 사용하지 않습니다.
        self.edit_timer = QTimer(self)

        self.edit_timer.setSingleShot(True)
        self.edit_timer.setInterval(500)

        self.edit_timer.timeout.connect(
            self._finish_idle_edit
        )

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

        self.image_label.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Ignored
        )

        self.image_label.setMinimumSize(1, 1)
        self.image_label.installEventFilter(self)

        # ===== 오른쪽 보정 패널 =====

        panel = QWidget()
        panel.setFixedWidth(280)

        panel_layout = QVBoxLayout(panel)

        panel_layout.setContentsMargins(
            16, 20, 16, 20
        )
        panel_layout.setSpacing(14)

        # RGB 히스토그램: 현재 보정 미리보기의 채널 분포를 표시합니다.
        panel_layout.addWidget(QLabel("RGB 히스토그램"))
        self.histogram_widget = HistogramWidget()
        panel_layout.addWidget(self.histogram_widget)

        panel_layout.addWidget(
            QLabel("기본 보정")
        )

        # sliders:
        # 보정 항목명(str) -> EditSlider 객체
        self.sliders: dict[str, EditSlider] = {}

        # value_labels:
        # 보정 항목명(str) -> QLabel 객체
        self.value_labels: dict[str, QLabel] = {}

        for key, (minimum, maximum, title) in (
            self.SLIDER_SPECS.items()
        ):
            self._add_slider(
                panel_layout,
                key,
                title,
                minimum,
                maximum
            )

        reset_button = QPushButton(
            "모든 보정 초기화"
        )

        reset_button.clicked.connect(
            self.reset_adjustments
        )

        panel_layout.addWidget(reset_button)
        panel_layout.addStretch()

        # ===== 중앙 레이아웃 =====

        central = QWidget()
        main_layout = QHBoxLayout(central)

        main_layout.setContentsMargins(
            0, 0, 0, 0
        )
        main_layout.setSpacing(0)

        main_layout.addWidget(self.image_label, 1)
        main_layout.addWidget(panel)

        self.setCentralWidget(central)

        self._create_menu()
        self._sync_controls()

        self.statusBar().showMessage("준비 완료")

    def _add_slider(
        self,
        layout: QVBoxLayout,
        key: str,
        title: str,
        minimum: int,
        maximum: int,
    ) -> None:
        """
        슬라이더 하나를 만들고 입력 신호를 연결합니다.

        layout: 위젯을 배치할 레이아웃
        key: 보정 항목의 필드명
        title: 화면 표시 제목
        minimum, maximum: 슬라이더 정수 범위
        """

        row = QHBoxLayout()

        row.addWidget(QLabel(title))
        row.addStretch()

        value_label = QLabel("0")
        row.addWidget(value_label)

        layout.addLayout(row)

        slider = EditSlider(
            Qt.Orientation.Horizontal
        )

        slider.setRange(minimum, maximum)
        slider.setValue(0)

        # 편집 시작
        slider.mouse_edit_started.connect(
            lambda field=key: self._start_mouse_edit(field)
        )

        # 값 변경: 미리보기와 임시 설정 갱신
        slider.valueChanged.connect(
            lambda value, field=key:
                self._on_slider_value(field, value)
        )

        # 편집 종료
        slider.mouse_edit_finished.connect(
            lambda field=key: self._finish_mouse_edit(field)
        )

        layout.addWidget(slider)

        self.sliders[key] = slider
        self.value_labels[key] = value_label

    def _create_menu(self) -> None:
        """파일과 편집 메뉴를 생성합니다."""

        file_menu = self.menuBar().addMenu("파일")

        open_action = QAction("열기", self)

        open_action.setShortcut(
            QKeySequence.StandardKey.Open
        )

        open_action.triggered.connect(
            self.open_image
        )

        file_menu.addAction(open_action)

        self.save_action = QAction(
            "다른 이름으로 저장...", self
        )

        self.save_action.setShortcut(
            QKeySequence("Ctrl+Shift+S")
        )

        self.save_action.triggered.connect(
            self.export_image
        )

        file_menu.addAction(self.save_action)
        file_menu.addSeparator()

        exit_action = QAction("종료", self)

        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # ===== 편집 메뉴 =====

        edit_menu = self.menuBar().addMenu("편집")

        self.undo_action = QAction(
            "실행 취소", self
        )

        self.undo_action.setShortcut(
            QKeySequence.StandardKey.Undo
        )

        self.undo_action.triggered.connect(
            self.undo_adjustments
        )

        edit_menu.addAction(self.undo_action)

        self.redo_action = QAction(
            "다시 실행", self
        )

        self.redo_action.setShortcut(
            QKeySequence("Ctrl+Y")
        )

        self.redo_action.triggered.connect(
            self.redo_adjustments
        )

        edit_menu.addAction(self.redo_action)

        self._update_history_actions()

    def _start_mouse_edit(self, field: str) -> None:
        """
        마우스를 누른 시점에 편집을 시작합니다.
        Qt가 슬라이더 값을 변경하기 전입니다.
        """

        if self.original_image.isNull():
            return

        # 다른 입력 작업이 진행 중이면 먼저 확정
        if self._active_key is not None:
            self._finish_active_edit()

        self.controller.begin_edit()

        self._active_key = field
        self._input_mode = "mouse"

        self.edit_timer.stop()

    def _on_slider_value(
        self,
        field: str,
        raw_value: int
    ) -> None:
        """
        슬라이더 값이 변경될 때 호출됩니다.

        여기서는 history.record()를 호출하지 않습니다.
        """

        if self.original_image.isNull():
            return

        # 편집 작업이 없거나 다른 항목으로 전환된 경우
        if self._active_key != field:

            self._finish_active_edit()

            self.controller.begin_edit()
            self._active_key = field
            self._input_mode = "idle"

        # 노출은 정수/10으로 EV 변환
        value = (
            raw_value / 10.0
            if field == "exposure_ev"
            else raw_value
        )

        self.controller.set_value(
            field, value
        )

        # 현재값을 즉시 화면에 적용합니다.
        self._update_labels()
        self._update_preview()
        self._update_history_actions()

        # 키보드/휠 입력일 때만 타이머 시작
        if self._input_mode == "idle":
            self.edit_timer.start()

    def _finish_mouse_edit(self, field: str) -> None:
        """마우스를 놓은 시점에 편집을 확정합니다."""

        if (
            self._active_key == field
            and self._input_mode == "mouse"
        ):
            self._finish_active_edit()

    def _finish_idle_edit(self) -> None:
        """키보드/휠 입력이 500ms 멈춘 경우입니다."""

        if self._input_mode == "idle":
            self._finish_active_edit()

    def _finish_active_edit(self) -> None:
        """
        실제 commit_edit()을 호출하는
        유일한 GUI 경로입니다.
        """

        self.edit_timer.stop()

        if self._active_key is None:
            return

        self.controller.commit_edit()

        self._active_key = None
        self._input_mode = None

        self._update_history_actions()

    def _sync_controls(self) -> None:
        """
        모델의 보정 설정을 GUI 슬라이더에 반영합니다.

        Undo/Redo 및 사진 교체 시 사용합니다.
        """

        settings = self.controller.settings

        for field, slider in self.sliders.items():

            # getattr():
            # settings 객체에서 field 이름의 속성값을 읽습니다.
            value = getattr(settings, field)

            raw = (
                round(value * 10)
                if field == "exposure_ev"
                else int(value)
            )

            # 프로그램이 슬라이더 값을 바꿀 때는
            # valueChanged 신호를 차단합니다.
            previous_blocked = slider.blockSignals(True)

            try:
                slider.setValue(raw)
            finally:
                slider.blockSignals(previous_blocked)

        self._update_labels()
        self._update_preview()
        self._update_history_actions()

    def _update_labels(self) -> None:
        """모델의 현재값으로 숫자 라벨을 표시합니다."""

        s = self.controller.settings

        self.value_labels["exposure_ev"].setText(
            f"{s.exposure_ev:+.1f} EV"
        )

        for field in (
            "contrast",
            "saturation",
            "warmth"
        ):
            self.value_labels[field].setText(
                f"{getattr(s, field):+d}"
            )

    def _update_history_actions(self) -> None:
        """Undo/Redo 메뉴의 활성 상태를 갱신합니다."""

        loaded = not self.original_image.isNull()

        self.undo_action.setEnabled(
            loaded and self.controller.can_undo
        )

        self.redo_action.setEnabled(
            loaded and self.controller.can_redo
        )

    def undo_adjustments(self) -> None:
        """
        미확정 변경이 있으면 우선 취소합니다.
        그렇지 않으면 이전 이력을 복원합니다.
        """

        self.edit_timer.stop()

        self._active_key = None
        self._input_mode = None

        self.controller.undo()
        self._sync_controls()

    def redo_adjustments(self) -> None:
        """확정된 다음 보정 상태를 복원합니다."""

        self.edit_timer.stop()

        self._active_key = None
        self._input_mode = None

        self.controller.redo()
        self._sync_controls()

    def reset_adjustments(self) -> None:
        """초기화를 하나의 편집 작업으로 기록합니다."""

        if self.original_image.isNull():
            return

        self._finish_active_edit()

        self.controller.begin_edit()

        self.controller.set_settings(
            AdjustmentSettings()
        )

        self.controller.commit_edit()
        self._sync_controls()

    def open_image(self) -> None:
        """
        새 사진을 정상적으로 읽은 후
        이전 문서의 보정 상태를 초기화합니다.
        """

        path, _filter = QFileDialog.getOpenFileName(
            self,
            "사진 열기",
            "",
            "이미지 (*.jpg *.jpeg *.png *.bmp *.webp);;"
            "모든 파일 (*)",
        )

        if not path:
            return

        reader = QImageReader(path)

        # EXIF 회전 정보 적용
        reader.setAutoTransform(True)

        image = reader.read()

        if image.isNull():
            QMessageBox.critical(
                self,
                "파일 열기 실패",
                reader.errorString()
            )
            return

        # 읽기에 성공했을 때만 기존 이력 제거
        self.edit_timer.stop()

        self._active_key = None
        self._input_mode = None

        self.controller.clear_document()

        self.original_image = image
        self.current_file_path = Path(path)

        # 기존 미리보기 캐시 제거
        self.preview_source = QImage()
        self.preview_size = None

        self._sync_controls()

        self.setWindowTitle(
            f"{self.current_file_path.name} - LocalPhoto Studio"
        )

        self.statusBar().showMessage(
            f"{self.current_file_path.name} | "
            f"{image.width()} × {image.height()} px"
        )

    def _update_preview(self) -> None:
        """
        화면용 축소 원본에 현재 보정값을 적용합니다.
        """

        if self.original_image.isNull():
            return

        width = self.image_label.width()
        height = self.image_label.height()

        if width < 2 or height < 2:
            return

        target_size = (width, height)

        if (
            self.preview_source.isNull()
            or self.preview_size != target_size
        ):

            self.preview_source = self.original_image.scaled(
                width,
                height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

            self.preview_size = target_size

        # 현재 보정값을 공통 모델에서 가져옵니다.
        adjusted = apply_adjustments(
            self.preview_source,
            **self.controller.settings.as_kwargs()
        )

        self.image_label.setPixmap(
            QPixmap.fromImage(adjusted)
        )

        # 표시된 이미지와 동일한 결과로 히스토그램을 갱신합니다.
        self.histogram_widget.set_image(adjusted)

    def export_image(self) -> None:
        """
        사용자가 선택한 형식으로
        원본 해상도 사진 저장을 시작합니다.
        """

        if (
            self.original_image.isNull()
            or self.current_file_path is None
        ):
            QMessageBox.warning(
                self,
                "저장 불가",
                "먼저 사진을 불러오세요."
            )
            return

        if self.export_thread is not None:
            return

        # 기본 제안 파일명에는 확장자를 붙이지 않습니다.
        suggested = self.current_file_path.with_name(
            self.current_file_path.stem + "_edited"
        )

        filters = (
            "JPEG 이미지 (*.jpg *.jpeg);;"
            "PNG 이미지 (*.png)"
        )

        filename, selected_filter = QFileDialog.getSaveFileName(
            self,
            "보정 사진 저장",
            str(suggested),
            filters
        )

        if not filename:
            return

        output = Path(filename)
        suffix = output.suffix.lower()

        # 사용자가 선택한 파일 형식
        preferred = (
            ".png"
            if selected_filter.startswith("PNG")
            else ".jpg"
        )

        if suffix and suffix not in (
            ".jpg", ".jpeg", ".png"
        ):
            QMessageBox.warning(
                self,
                "형식 오류",
                "JPG 또는 PNG 확장자만 사용합니다."
            )
            return

        # 선택한 필터와 확장자가 다르면 필터 우선
        if (
            not suffix
            or (preferred == ".png" and suffix != ".png")
            or (preferred == ".jpg" and suffix == ".png")
        ):
            output = output.with_suffix(preferred)

        # 원본 덮어쓰기 방지
        if (
            output.resolve()
            == self.current_file_path.resolve()
        ):
            QMessageBox.warning(
                self,
                "원본 보호",
                "원본 파일에 덮어쓸 수 없습니다."
            )
            return

        # 기존 파일 덮어쓰기 확인
        if output.exists():

            answer = QMessageBox.question(
                self,
                "덮어쓰기 확인",
                f"{output.name} 파일을 덮어쓰시겠습니까?",
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if answer != QMessageBox.StandardButton.Yes:
                return

        # snapshot:
        # 저장 버튼을 누른 시점의 불변 보정값
        snapshot = self.controller.settings

        thread = ExportThread(
            self.original_image,
            str(output),
            snapshot,
            self
        )

        self.export_thread = thread

        thread.succeeded.connect(
            self._on_export_success
        )

        thread.failed.connect(
            self._on_export_error
        )

        thread.finished.connect(
            self._on_export_finished
        )

        self.save_action.setEnabled(False)

        self.statusBar().showMessage(
            "원본 해상도로 저장 중..."
        )

        thread.start()

    def _on_export_success(self, path: str) -> None:
        """저장 성공 시 GUI에 결과를 표시합니다."""

        self.statusBar().showMessage(
            f"저장 완료: {path}"
        )

        QMessageBox.information(
            self,
            "저장 완료",
            f"사진을 저장했습니다.\n{path}"
        )

    def _on_export_error(self, message: str) -> None:
        """저장 실패 시 오류 메시지를 표시합니다."""

        self.statusBar().showMessage("저장 실패")

        QMessageBox.critical(
            self,
            "저장 오류",
            message
        )

    def _on_export_finished(self) -> None:
        """작업이 끝나면 스레드를 정리합니다."""

        thread = self.export_thread

        self.export_thread = None
        self.save_action.setEnabled(True)

        if thread is not None:
            thread.deleteLater()

    def closeEvent(self, event) -> None:
        """저장 중 프로그램 종료를 방지합니다."""

        if self.export_thread is not None:

            QMessageBox.information(
                self,
                "저장 진행 중",
                "저장 종료 후 프로그램을 닫으세요."
            )

            event.ignore()
            return

        super().closeEvent(event)

    def eventFilter(self, watched, event) -> bool:
        """사진 표시 영역의 크기 변경을 감지합니다."""

        if (
            watched is self.image_label
            and event.type() == QEvent.Type.Resize
        ):
            self._update_preview()

        return super().eventFilter(watched, event)


if __name__ == "__main__":

    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
