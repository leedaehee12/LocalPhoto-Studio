"""
LocalPhoto Studio - CPU 이미지 보정 엔진

역할:
1. QImage에서 픽셀 데이터를 읽습니다.
2. NumPy 배열로 변환합니다.
3. 노출, 대비, 채도, 색온도를 계산합니다.
4. 보정된 새 QImage를 반환합니다.

주의:
입력받은 원본 이미지는 수정하지 않습니다.
"""

import numpy as np
from PySide6.QtGui import QImage

def apply_adjustments(
    image : QImage,
    exposure_ev : float = 0.0,
    contrast : int = 0,
    saturation: int = 0,
    warmth: int = 0,  
)  -> QImage :


# 이미지가 비어 있으면 빈 QImage를 반환합니다.
    if image.isNull():
        return QImage()

    
 # 보정값이 모두 0이면 계산 없이 원본의 복사본 반환
    if(
        exposure_ev == 0.0
        and contrast == 0
        and saturation == 0
        and warmth == 0
    ):
        return image.copy()

    # 이미지의 픽셀 형식을 RGBA8888로 통일합니다.
    # 각 채널은 0~255의 8비트 정수입니다.
    source = image.convertToFormat(
        QImage.Format.Format_RGBA8888
    )

    # 이미지 가로/세로 크기를 픽셀 단위로 가져옵니다.
    width = source.width()
    height = source.height()

    # 이미지의 한 행에 저장된 바이트 수입니다.
    # 메모리 정렬에 따른 여유 공간을 고려하기 위해 사용합니다.
    row_bytes = source.bytesPerLine()

    # QImage 메모리의 바이트를 NumPy로 읽습니다.
    # dtype=np.uint8: 0~255의 부호 없는 8비트 정수
    raw_bytes = np.frombuffer(
        source.constBits(),
        dtype=np.uint8
    )

    # 높이 × 행 바이트 수로 배열 모양을 변경합니다.
    rows = raw_bytes.reshape(height, row_bytes)

     # 각 픽셀을 [R, G, B, A] 형태로 구성합니다.
    # 결과 배열 크기: (height, width, 4)
    # copy()는 원본 버퍼를 보호하기 위한 독립 사본입니다.
    pixels = rows[:, :width * 4].reshape(
        height, width, 4
    ).copy()

    # RGB 채널만 추출합니다.
    # float32로 변환하고 255로 나누어
    # 픽셀값을 0.0~1.0 범위로 정규화합니다.
    rgb = (
        pixels[:, :, :3].astype(np.float32) / 255.0
    )

    # ===== 1. sRGB → 선형 RGB =====

    # 일반적인 sRGB 데이터는 감마 인코딩되어 있으므로
    # 광량 계산 전에 선형 RGB로 변환합니다.
    linear = np.where(
        rgb <= 0.04045,
        rgb / 12.92,
        ((rgb + 0.055) / 1.055) ** 2.4
    )

    # ===== 2. 노출 보정 =====

    # EV를 광량 배율로 변환합니다.
    # EV +1 = 2배, EV -1 = 0.5배
    exposure_factor = 2.0 ** exposure_ev

    # 전체 RGB 채널에 노출 배율을 적용합니다.
    linear *= exposure_factor

    # ===== 3. 간이 색온도 보정 =====

    # warmth를 -1.0~+1.0 범위로 변환합니다.
    warmth_ratio = warmth / 100.0

    # 따뜻하게: 빨강 증가, 파랑 감소
    # 차갑게: 빨강 감소, 파랑 증가
    red_gain = 1.0 + 0.20 * warmth_ratio
    blue_gain = 1.0 - 0.20 * warmth_ratio

    # [:, :, 0] = 빨강 채널
    # [:, :, 2] = 파랑 채널
    linear[:, :, 0] *= red_gain
    linear[:, :, 2] *= blue_gain

    # ===== 4. 대비 보정 =====

    # -100 => 0.0배
    #    0 => 1.0배
    # +100 => 2.0배
    contrast_factor = 1.0 + contrast / 100.0

    # 0.18은 선형 RGB에서 사용하는 중간 회색 기준값입니다.
    # 기준보다 밝은 값은 더 밝게, 어두운 값은 더 어둡게
    # 만드는 방식입니다.
    linear = (
        (linear - 0.18) * contrast_factor + 0.18
    )

    # ===== 5. 채도 보정 =====

    # 채도 -100 => 0배(흑백)
    # 채도    0 => 1배(변화 없음)
    # 채도 +100 => 2배
    saturation_factor = 1.0 + saturation / 100.0

    # RGB 채널에서 밝기 성분을 계산합니다.
    # 0.2126, 0.7152, 0.0722는
    # 선형 sRGB의 휘도 계산에 사용하는 가중치입니다.
    luminance = (
        linear[:, :, 0:1] * 0.2126
        + linear[:, :, 1:2] * 0.7152
        + linear[:, :, 2:3] * 0.0722
    )

    # 각 색상과 밝기 성분의 차이를 조절합니다.
    # saturation_factor가 0이면 세 채널이
    # 모두 luminance 값으로 바뀝니다.
    linear = (
        luminance
        + (linear - luminance) * saturation_factor
    )

    # ===== 6. 색상 범위 제한 =====

    # 표시 가능한 선형 RGB 범위는 0.0~1.0입니다.
    # 이를 초과한 값은 잘라냅니다.
    linear = np.clip(linear, 0.0, 1.0)

    # ===== 7. 선형 RGB → sRGB =====

    # 디스플레이에 표시하도록 sRGB로 재인코딩합니다.
    srgb = np.where(
        linear <= 0.0031308,
        linear * 12.92,
        1.055 * (linear ** (1.0 / 2.4)) - 0.055
    )

    # 0.0~1.0 실수를 0~255 정수로 변환합니다.
    rgb_uint8 = np.rint(
        srgb * 255.0
    ).clip(0, 255).astype(np.uint8)

    # RGB 채널만 변경합니다.
    # 네 번째 알파(투명도) 채널은 그대로 보존합니다.
    pixels[:, :, :3] = rgb_uint8

    # ===== 8. QImage 생성 =====

    # NumPy 배열을 QImage로 변환합니다.
    result = QImage(
        pixels.data,
        width,
        height,
        width * 4,
        QImage.Format.Format_RGBA8888
    )

    # pixels.data는 NumPy의 메모리를 참조하므로
    # copy()를 이용해 Qt가 소유하는 독립된 이미지를 만듭니다.
    return result.copy()
    