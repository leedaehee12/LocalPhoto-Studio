import sys
from pathlib import Path


from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QAction, QPixmap, QImageReader, QKeySequence
from PySide6.QtWidgets import(
    QApplication,
    QMainWindow,
    QLabel,
    QFileDialog,
    QMessageBox,
    QSizePolicy,

)



class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 1. 기본 창 설정

        self.setWindowTitle("LocalPhoto Studio")
        self.resize(1200, 800)
       
        # 2. 원본 이미지 저장 변수
        self.original_pixmap = QPixmap()

        # 3. 사진 표시 영역 생성
        self.image_label = QLabel(
            "파일 -> 열기 (Ctrl + o) 사진을 불러오세요."
        )

        self.image_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.image_label.setStyleSheet(
            """
            QLabel {
                background-color: #252525;
                color: #CCCCCC;
                font-size: 16px;
            }
        """
        )

        # 사진 크기로 창 강제 증가 방지
        self.image_label.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Ignored
        )

        self.image_label.setMinimumSize(1, 1)

        # 이미지 표시 영역의 크기 변경 감지
        self.image_label.installEventFilter(self)

        self.setCentralWidget(self.image_label)

        # 메뉴바 구성
        self.create_menu()

        # 상태바 구성
        self.statusBar().showMessage("준비 완료")

    def create_menu(self):
        
        """프로그램 메뉴 생성"""

        file_menu = self.menuBar().addMenu("파일")

        # 사진열기
        open_action = QAction("열기", self)

        open_action.setShortcut(
            QKeySequence.StandardKey.Open
        )

        open_action.triggered.connect(self.open_image)

        file_menu.addAction(open_action)

        # 종료
        exit_action = QAction("종료", self)
        exit_action.triggered.connect(self.close)

        file_menu.addSeparator()
        file_menu.addAction(exit_action)

    def open_image(self):
        """이미지 파일 선택 및 로딩"""

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "사진 열기",
            "",
            "이미지 파일 (*.jpg *.jpeg *.png *.bmp *.webp);;"
            "모든 파일 (*)"
        )

        # 이미지 파일명 추출
        filename = Path(file_path).name

        # 취소를 누른경우
        if not file_path:
            return

        # EXIF 회전을 적용하여 이미지 로딩
        reader = QImageReader(file_path)
        reader.setAutoTransform(True)

        image = reader.read()

        # 불러오기 실패
        if image.isNull():
            QMessageBox.critical(
                    self,
                "오류",
                f"이미지를 불러올 수 없습니다.\n"
                f"{reader.errorString()}"
            )
            return

        # 원본 이미지 저장
        self.original_pixmap = QPixmap.fromImage(image)

        # 창 제목 변경
        file_path = Path(file_path).name
        self.setWindowTitle(
            f"{filename} - LocalPhoto Studio"
        )

        # 사진 출력
        self.update_preview()

        # 해상도 상태 표시
        width = image.width()
        height = image.height()

        self.statusBar().showMessage(
            f"{filename} | {width} * {height} px"
        )

    def update_preview(self):
        """화면 크기에 맞춰 이미지 출력"""

        if self.original_pixmap.isNull():
            return

        # 현재 이미지 표시 영역 크기
        target_size = self.image_label.size()

        if target_size.isEmpty():
            return

        # 원본을 기준으로 비율 유지 축소
        scaled_pixmap = self.original_pixmap.scaled(
            target_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        self.image_label.setPixmap(scaled_pixmap)

    def eventFilter(self, watched, event):
        """이미지 표시 영역 크기 변경 감지"""

        if(
            watched is self.image_label
            and event.type() == QEvent.Type.Resize
        ):
            self.update_preview()

        return super().eventFilter(watched, event)


        
        


        self.label = QLabel("LocalPhoto Studio")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.setCentralWidget(self.label)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())