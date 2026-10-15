import numpy as np
from PySide6.QtGui import QImage

def apply_exposure(image: QImage, ev:float) -> QImage:
    """sRGB 이미지에 노출 보정을 적용합니다."""

    if image.isNull():
        return QImage()

    # 0 EV에서는 원본 데이터를 그대로 복사
    if ev == 0.0:
        return image.copy()
    
    # 이미지 데이터를 RGBA 8비트 형식으로 변환
    source = image.convertToFormat(
        QImage.Format.Format_RGBA8888
    )

    width = source.width()
    height = source.height()

    # QImage의 픽셀을 NumPy 배열로 복사
    pixels = np.frombuffer(
        source.constBits(),
        dtype=np.uint8
    ).reshape(height, width, 4).copy()

    # 0~255 범위의 색상 변환표 생성
    values = np.arange(256, dtype=np.float32) /255.0

    # sRGB 감마를 제거하여 선형 광량으로 변환
    linear = np.where(
        values <= 0.04045,
        values / 12.92,
        ((values + 0.055) / 1.055) ** 2.4
    )

    # 노출 보정: +1 EV = 광량 2배
    linear = np.clip(
        linear * (2.0 ** ev),
        0.0,
        1.0
    )

    # 선형 광량을 sRGB로 다시 변환
    srgb = np.where(
        linear <= 0.0031308,
        linear * 12.92,
        1.055 * (linear ** (1 / 2.4)) - 0.055
    )

    table = np.rint(
        np.clip(srgb * 255.0, 0, 255)
    ).astype(np.uint8)

    # RGB 채널만 수정 (알파 채널 보존)
    pixels[:, :, :3] = table[pixels[:, :, :3]]

    # NumPy 배열을 QImage로 변환
    output = QImage(
        pixels.data,
        width,
        height,
        width * 4,
        QImage.Format.Format_RGBA8888
    )

    # 메모리 소유권을 분리하여 반환
    return output.copy()