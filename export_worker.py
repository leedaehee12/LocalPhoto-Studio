
"""
원본 해상도 JPEG/PNG 내보내기.

GUI/이력 객체를 직접 제어하지 않습니다.
"""

from pathlib import Path
from typing import Mapping

from PySide6.QtCore import (
    QIODevice,
    QSaveFile,
    QThread,
    Signal,
    Qt
)

from PySide6.QtGui import (
    QImage,
    QImageWriter,
    QPainter
)

from models import AdjustmentSettings
from processing import apply_adjustments


def normalize_settings(
    settings: AdjustmentSettings | Mapping[str, float | int],
) -> AdjustmentSettings:
    """
    기존 dict 호출 방식도 지원합니다.

    내부에서는 AdjustmentSettings 모델만 사용합니다.
    """

    if isinstance(settings, AdjustmentSettings):
        return settings

    return AdjustmentSettings(**dict(settings))


def save_adjusted_image(
    source: QImage,
    output_path: str,
    settings: AdjustmentSettings | Mapping[str, float | int],
) -> None:
    """
    원본 해상도의 보정 사진을 안전하게 저장합니다.
    오류 발생 시 예외를 발생시킵니다.
    """

    # path:
    # 확장자 검사와 저장 위치 관리용 Path 객체
    path = Path(output_path)

    # suffix:
    # 파일 확장자를 소문자로 변환
    # 예: '.JPG' → '.jpg'
    suffix = path.suffix.lower()

    # 파일 확장자와 Qt 인코더 형식 대응표
    formats = {
        ".jpg": b"JPEG",
        ".jpeg": b"JPEG",
        ".png": b"PNG"
    }

    if suffix not in formats:
        raise ValueError(
            "지원하는 저장 형식은 JPG, JPEG, PNG입니다."
        )

    if source.isNull():
        raise ValueError(
            "저장할 원본 이미지가 없습니다."
        )

    # ===== 1. 보정 설정 정규화 =====

    # snapshot:
    # 저장 시작 시점의 불변 보정 설정입니다.
    snapshot = normalize_settings(settings)

    # ===== 2. 원본 해상도 보정 =====

    # result:
    # 화면 미리보기가 아닌 원본 전체를 보정한 QImage
    result = apply_adjustments(
        source,
        **snapshot.as_kwargs()
    )

    if result.isNull():
        raise RuntimeError(
            "보정 결과가 비어 있습니다."
        )

    # ===== 3. JPEG 투명도 처리 =====

    if suffix in (".jpg", ".jpeg"):

        # JPEG는 투명도를 지원하지 않습니다.
        # 불투명한 RGB 이미지 생성
        opaque = QImage(
            result.size(),
            QImage.Format.Format_RGB888
        )

        if opaque.isNull():
            raise MemoryError(
                "JPEG용 이미지 메모리를 확보하지 못했습니다."
            )

        # 배경을 흰색으로 채웁니다.
        opaque.fill(Qt.GlobalColor.white)

        # 투명 영역을 흰 배경에 합성합니다.
        painter = QPainter(opaque)

        try:
            painter.drawImage(0, 0, result)
        finally:
            painter.end()

        result = opaque

    # ===== 4. 임시 파일 생성 =====

    # QSaveFile:
    # 임시 파일에 기록한 뒤 성공 시 최종 저장합니다.
    target = QSaveFile(str(path))

    if not target.open(
        QIODevice.OpenModeFlag.WriteOnly
    ):
        raise OSError(
            f"파일 열기 실패: {target.errorString()}"
        )

    # ===== 5. 인코더 생성 =====

    # writer:
    # JPEG 또는 PNG 바이트로 변환하는 QImageWriter 객체
    writer = QImageWriter(
        target,
        formats[suffix]
    )

    if suffix in (".jpg", ".jpeg"):
        # JPEG 저장 품질
        writer.setQuality(95)

    # 실제 이미지 기록
    if not writer.write(result):

        message = writer.errorString()

        # 저장이 실패했으므로 임시 파일 쓰기 취소
        target.cancelWriting()

        raise OSError(
            f"이미지 인코딩 실패: {message}"
        )

    # ===== 6. 저장 확정 =====

    if not target.commit():
        raise OSError(
            f"최종 저장 실패: {target.errorString()}"
        )


class ExportThread(QThread):
    """
    백그라운드에서 사진을 저장합니다.
    QWidget을 직접 조작하지 않습니다.
    """

    # 성공한 파일 경로(str)를 GUI에 전달
    succeeded = Signal(str)

    # 오류 메시지(str)를 GUI에 전달
    failed = Signal(str)

    def __init__(
        self,
        source: QImage,
        output_path: str,
        settings: AdjustmentSettings | Mapping[str, float | int],
        parent=None,
    ) -> None:

        super().__init__(parent)

        # source:
        # 원본 이미지의 독립 사본
        # 저장 중 다른 사진을 열어도 작업 데이터가 유지됩니다.
        self.source = source.copy()

        # output_path:
        # 사용자가 선택한 저장 대상 전체 경로
        self.output_path = output_path

        # settings:
        # 저장 시작 시점의 불변 보정 설정
        self.settings = normalize_settings(settings)

    def run(self) -> None:
        """
        QThread.start()로 실행되는 작업 함수입니다.
        """

        try:
            save_adjusted_image(
                self.source,
                self.output_path,
                self.settings
            )

        except Exception as exc:

            self.failed.emit(
                f"{type(exc).__name__}: {exc}"
            )

        else:
            self.succeeded.emit(self.output_path)
