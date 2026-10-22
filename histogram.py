"""RGB 히스토그램의 순수 NumPy 계산 모듈.

Qt 위젯이나 이미지 저장과 독립적입니다. 입력은 RGB/RGBA 픽셀 배열,
출력은 각 채널의 0~255 밝기별 픽셀 개수입니다.
"""

import numpy as np


def calculate_rgb_histogram(pixels: np.ndarray) -> np.ndarray:
    """8비트 RGB 또는 RGBA 배열에서 (3, 256) 히스토그램을 계산합니다.

    pixels:
        np.ndarray, shape=(높이, 너비, 3 또는 4), dtype=np.uint8
        마지막 채널이 알파(A)라면 완전 투명한 픽셀은 제외합니다.

    반환값:
        np.ndarray, shape=(3, 256), dtype=np.int64
        행 0/1/2는 각각 R/G/B 채널, 열 0~255는 채널 값입니다.
    """
    if not isinstance(pixels, np.ndarray):
        raise TypeError("pixels는 NumPy 배열이어야 합니다.")

    if pixels.ndim != 3 or pixels.shape[2] not in (3, 4):
        raise ValueError("pixels의 크기는 (높이, 너비, 3 또는 4)여야 합니다.")

    if pixels.dtype != np.uint8:
        raise TypeError("8비트 채널을 가진 uint8 배열만 지원합니다.")

    # RGB 3채널만 추출합니다. RGBA면 완전 투명한 픽셀은 제외합니다.
    if pixels.shape[2] == 4:
        valid_pixels = pixels[:, :, :3][pixels[:, :, 3] > 0]
    else:
        valid_pixels = pixels.reshape(-1, 3)

    # 채널 3개 각각 256개 빈의 픽셀 수를 셉니다.
    counts = np.zeros((3, 256), dtype=np.int64)
    for channel in range(3):
        counts[channel] = np.bincount(
            valid_pixels[:, channel], minlength=256
        )
    return counts
