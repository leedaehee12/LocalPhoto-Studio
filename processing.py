
"""
CPU 이미지 보정 엔진.

GUI·Undo·파일 저장을 알 필요가 없는
순수 연산 모듈입니다.
"""

import numpy as np
from PySide6.QtGui import QImage


def apply_adjustments(
    image: QImage,
    exposure_ev: float = 0.0,
    contrast: int = 0,
    saturation: int = 0,
    warmth: int = 0,
) -> QImage:
    """
    QImage를 보정해 독립적인 새 QImage를 반환합니다.
    입력받은 원본 이미지는 수정하지 않습니다.
    """

    # 비어 있는 이미지인지 확인
    if image.isNull():
        return QImage()

    # 모든 보정값이 0이면 계산할 필요가 없습니다.
    if (
        exposure_ev == 0
        and contrast == 0
        and saturation == 0
        and warmth == 0
    ):
        return image.copy()

    # ===== 1. QImage → NumPy =====

    # source:
    # RGBA8888으로 변환한 QImage 객체
    # 한 픽셀은 R,G,B,A 네 채널로 구성됩니다.
    source = image.convertToFormat(
        QImage.Format.Format_RGBA8888
    )

    # width, height: 원본 이미지의 가로·세로 픽셀 수
    width, height = source.width(), source.height()

    # row_bytes:
    # 한 행의 실제 메모리 크기(패딩 포함)
    row_bytes = source.bytesPerLine()

    # pixels:
    # (세로, 가로, 4) 형태의 uint8 NumPy 배열
    # .copy()로 원본 이미지 메모리와 분리합니다.
    pixels = np.frombuffer(
        source.constBits(),
        dtype=np.uint8
    )

    pixels = pixels.reshape(
        height, row_bytes
    )[:, :width * 4]

    pixels = pixels.reshape(
        height, width, 4
    ).copy()

    # rgb:
    # RGB 채널만 float32로 변환
    # 0~255를 0.0~1.0으로 정규화합니다.
    rgb = (
        pixels[:, :, :3].astype(np.float32)
        / 255.0
    )

    # ===== 2. sRGB → 선형 RGB =====

    # sRGB 감마를 해제합니다.
    # 이후 밝기 계산이 실제 광량에 비례하게 됩니다.
    linear = np.where(
        rgb <= 0.04045,
        rgb / 12.92,
        ((rgb + 0.055) / 1.055) ** 2.4,
    )

    # ===== 3. 노출 보정 =====

    # +1 EV: 광량 2배
    # -1 EV: 광량 0.5배
    linear *= 2.0 ** exposure_ev

    # ===== 4. 간이 색온도 =====

    # warmth_ratio:
    # -1.0부터 +1.0까지의 실수
    warmth_ratio = warmth / 100.0

    # 빨강과 파랑 채널의 상대적 이득을 변경합니다.
    linear[:, :, 0] *= (
        1.0 + 0.20 * warmth_ratio
    )

    linear[:, :, 2] *= (
        1.0 - 0.20 * warmth_ratio
    )

    # ===== 5. 대비 보정 =====

    # contrast_factor:
    # 대비 -100: 0배
    # 대비    0: 1배
    # 대비 +100: 2배
    contrast_factor = 1.0 + contrast / 100.0

    # 선형 RGB의 0.18을 기준으로
    # 밝기 차이를 확대하거나 축소합니다.
    linear = (
        (linear - 0.18) * contrast_factor
        + 0.18
    )

    # ===== 6. 채도 보정 =====

    # luminance:
    # 선형 RGB의 휘도 성분
    # 각 채널에 휘도 가중치를 적용합니다.
    luminance = (
        linear[:, :, 0:1] * 0.2126
        + linear[:, :, 1:2] * 0.7152
        + linear[:, :, 2:3] * 0.0722
    )

    # saturation_factor:
    # -100: 흑백
    #    0: 원래 채도
    # +100: 채도 차이 2배
    saturation_factor = (
        1.0 + saturation / 100.0
    )

    linear = (
        luminance
        + (linear - luminance) * saturation_factor
    )

    # ===== 7. sRGB 재인코딩 =====

    # 출력 가능한 광량 범위로 제한합니다.
    linear = np.clip(linear, 0.0, 1.0)

    # 선형 RGB → sRGB
    srgb = np.where(
        linear <= 0.0031308,
        linear * 12.92,
        1.055 * (linear ** (1.0 / 2.4)) - 0.055,
    )

    # 0~255 uint8 RGB 배열로 변환합니다.
    pixels[:, :, :3] = (
        np.rint(srgb * 255)
        .clip(0, 255)
        .astype(np.uint8)
    )

    # ===== 8. QImage 반환 =====

    # NumPy 배열의 메모리를 참조하는 QImage 생성
    result = QImage(
        pixels.data,
        width,
        height,
        width * 4,
        QImage.Format.Format_RGBA8888
    )

    # 메모리 소유권을 분리한 이미지 반환
    return result.copy()
