
"""
LocalPhoto Studio - 이미지 내보내기 모듈

담당 기능:
1. 원본 해상도로 이미지 보정
2. JPG / PNG 인코딩
3. 임시 파일을 이용한 안전한 저장
4. 별도 스레드에서 처리
"""

from pathlib import Path

from PySide6.QtCore import (
    QIODevice,
    QSaveFile,
    QThread,
    Signal,
    Qt,
)

from PySide6.QtGui import (
    QImage,
    QImageWriter,
    QPainter,
)

# 기존 사진 보정 함수를 재사용합니다.
from processing import apply_adjustments


def save_adjusted_image(
    source: QImage,
    output_path: str,
    settings: dict,
) -> None:
    """
    원본 해상도의 보정 사진을 파일에 저장합니다.

    source:
        불러온 원본 QImage 객체

    output_path:
        저장할 파일의 전체 경로(str)

    settings:
        보정값을 담은 딕셔너리(dict)

    반환값:
        없음(None)
        저장에 실패하면 예외를 발생시킵니다.
    """

    # suffix: 파일 확장자를 소문자로 가져옵니다.
    # 예: "photo.JPG" -> ".jpg"
    suffix = Path(output_path).suffix.lower()

    # 확장자와 Qt 이미지 형식의 대응표입니다.
    # bytes 형식으로 전달합니다.
    formats = {
        ".jpg": b"JPEG",
        ".jpeg": b"JPEG",
        ".png": b"PNG",
    }

    if suffix not in formats:
        raise ValueError(
            "지원하는 형식은 JPG, JPEG, PNG입니다."
        )

    # ===== 1. 원본 이미지 보정 =====

    # **settings는 딕셔너리 언패킹 문법입니다.
    #
    # 예:
    # {"exposure_ev": 1.0, "contrast": 20}
    # ->
    # exposure_ev=1.0, contrast=20
    #
    # 입력 이미지는 화면용 축소본이 아닙니다.
    result = apply_adjustments(
        source,
        **settings
    )

    if result.isNull():
        raise RuntimeError(
            "보정 결과 이미지가 비어 있습니다."
        )

    # ===== 2. JPEG의 투명도 처리 =====

    if suffix in (".jpg", ".jpeg"):

        # JPEG는 투명도를 지원하지 않습니다.
        # RGB888 형식의 새 이미지를 만듭니다.
        opaque = QImage(
            result.size(),
            QImage.Format.Format_RGB888
        )

        # 전체 배경을 흰색으로 채웁니다.
        opaque.fill(Qt.GlobalColor.white)

        # QPainter를 이용하여 기존 사진을
        # 흰 배경 위에 합성합니다.
        painter = QPainter(opaque)
        painter.drawImage(0, 0, result)
        painter.end()

        result = opaque
    # ===== 3. 안전한 저장 파일 생성 =====

    # QSaveFile은 우선 임시 파일에 데이터를 씁니다.
    # 쓰기가 끝나면 commit()으로 최종 저장합니다.
    target_file = QSaveFile(output_path)
    if not target_file.open(
        QIODevice.OpenModeFlag.WriteOnly
    ) : 
        raise OSError(
            f"파일열기 실패 : {target_file.errorString()}"
        )
    # ===== 4. 이미지 인코더 생성 =====

    # writer:
    # 이미지를 JPEG/PNG 바이트로 변환하는 객체
    writer = QImageWriter(
        target_file,
        formats[suffix]
    )
    
    if suffix in (".jpg", ".jpeg"):
        # JPEG 품질 95 (손실 압축)
         writer.setQuality(95)
         
    if not writer.write(result):
        
       # 실패 원인을 문자열로 가져옵니다.
        error_message = writer.errorString()
       
       # 임시 저장을 취소합니다.
        target_file.cancelWriting() 
        
        raise OSError(
            f"이미지기록실패 : {error_message}"
        )
        
     # ===== 5. 저장 확정 =====

     # 쓰기가 성공한 경우에만 최종 경로로 반영합니다.
     
    if not target_file.commit():
        raise OSError(
            f"파일 저장 실패: {target_file.errorString()}"  
         )
        
class ExportThread(QThread):
    """
    이미지 저장 작업용 스레드입니다.

    GUI 스레드와 분리하여 대용량 이미지 처리 중
    프로그램 창의 반응성을 유지합니다.
    """

    # 성공 시 저장 경로(str)를 전달하는 신호
    succeeded = Signal(str)
    # 실패 시 오류 메시지(str)를 전달하는 신호
    failed = Signal(str)
    
    def __init__(
        self,
        source : QImage,
        output_path: str,
        settings: dict,
        parent=None
    ):
        super().__init__(parent)
        
        # 원본 이미지를 복사해 저장합니다.
        self.source = source.copy()
        
        # 저장할 파일 경로
        self.output_path = output_path
        
        # 작업 시작 시점의 보정값 사본
        self.settings = settings.copy()
    
    def run(self):
        
        """
        start()를 호출하면 별도 스레드에서 실행됩니다.

        이 함수 안에서는 GUI 위젯을 직접 조작하지 않습니다.
        """
        try:
            save_adjusted_image(
                self.source,
                self.output_path,
                self.settings
            )

            # 작업 성공을 GUI에 알립니다.
            self.succeeded.emit(
                self.output_path
            )

        except Exception as exc:

            # 오류의 클래스 이름과 내용을 함께 전달합니다.
            self.failed.emit(
                f"{type(exc).__name__}: {exc}"
            )
        
      
         
    
   