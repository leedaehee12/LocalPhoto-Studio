"""
LocalPhoto Studio - 톤 커브 계산 엔진

역할:
1. 제어점으로부터 256개 밝기 변환표(LUT)를 생성
2. NumPy RGB/RGBA 이미지에 변환표 적용
3. 원본 픽셀과 알파 채널 보존

Qt GUI와 독립적으로 동작합니다.
"""

import numpy as np

def build_curve_lut(
    points: tuple[tuple[int, int], ...]
) -> np.ndarray:
    """
    제어점을 이용해 톤 커브 LUT를 생성합니다.

    points:
        (입력값, 출력값) 튜플의 모음

        예:
        ((0, 0), (128, 150), (255, 255))

    반환값:
        shape=(256,), dtype=np.uint8인 NumPy 배열
    """
    
    # 시작점과 끝점이 필요하므로 최소 2개
    if len(points) < 2:
        raise ValueError(
            "제어점은 최소 2개가 필요합니다."
        )
    # 제어점은 0~255의 정수 좌표로 제한합니다.
    for x, y in points:
        if type(x) is not int or type(y) is not int:
            raise TypeError(
                "제어점 좌표는 정수여야 합니다"
            )
            
        if not (0 <= x <= 255 and 0 <= y <= 255):
            raise ValueError(
                "제어점 좌표는 0~255여야 합니다."
            )
     # 입력값(x)을 기준으로 제어점을 정렬합니다.
    sorted_points = sorted(
        points,
        key=lambda point: point[0]
    )
    
    # x_coords, y_coords:
    # 각 제어점의 입력/출력값을 분리한 배열
    x_coords = np.array(
        [p[0] for p in sorted_points],
        dtype=np.float64
    )
    
    y_coords = np.array(
        [p[1] for p in sorted_points],
        dtype=np.float64
    )
    
    # ==========================================
    # 제어점의 시작과 끝 검사
    # ==========================================

    # 정렬된 제어점에서 첫 번째와 마지막 x 좌표
    first_x = sorted_points[0][0]
    last_x = sorted_points[-1][0]

    # 첫 번째 제어점은 x=0이어야 합니다.
    # 마지막 제어점은 x=255여야 합니다.
    if first_x != 0 or last_x != 255:
        raise ValueError(
            "제어점에는 x=0과 x=255가 필요합니다."
        )

    
    # np.diff는 이웃한 x 좌표의 차이를 계산합니다.
    # 차이가 0 이하라면 입력값이 중복된 것입니다.
    if np.any(np.diff(x_coords) <= 0):
        raise ValueError(
            "제어점의 입력값(x)은 중복될 수 없습니다."
        )
    # 모든 가능한 8비트 픽셀값 0~255
    input_values = np.arange(
        256,
        dtype=np.float64
    )
    
    # np.interp:
    # 제어점 사이를 직선으로 보간합니다.
    # 예: (0,0), (255,255)라면 결과는 항등 변환
    interpolated = np.interp(
            input_values,
            x_coords,
            y_coords
        )
    # 픽셀값은 정수여야 하므로 반올림하여 변환
    lut = np.rint(interpolated).astype(np.uint8)
    return lut

def apply_curve_pixels(
    pixels: np.ndarray,
    lut: np.ndarray
) -> np.ndarray:
    """
    RGB 또는 RGBA 픽셀에 톤 커브를 적용합니다.

    pixels:
        shape=(높이, 너비, 3 또는 4)
        dtype=np.uint8

    lut:
        build_curve_lut()의 반환값

    반환값:
        원본과 분리된 새 NumPy 배열
    """

    if not isinstance(pixels, np.ndarray):
        raise TypeError(
            "pixels는 NumPy 배열이어야 합니다."
        )

    if (
        pixels.ndim != 3
        or pixels.shape[2] not in (3, 4)
        or pixels.dtype != np.uint8
    ):
        raise ValueError(
            "uint8 RGB 또는 RGBA 배열이 필요합니다."
        )

    if (
        not isinstance(lut, np.ndarray)
        or lut.shape != (256,)
        or lut.dtype != np.uint8
    ):
        raise ValueError(
            "LUT는 길이 256의 uint8 배열이어야 합니다."
        )

    # 원본 이미지가 변경되지 않도록 독립 사본 생성
    result = pixels.copy()

    # 픽셀값 자체를 LUT의 인덱스로 사용합니다.
    #
    # 예:
    # RGB값이 [64, 128, 192]일 때
    # [lut[64], lut[128], lut[192]]로 변환합니다.
    #
    # [:, :, :3]은 RGB 채널만 선택하므로
    # 네 번째 알파 채널은 변경하지 않습니다.
    result[:, :, :3] = lut[result[:, :, :3]]

    return result


        
        
    
    
       
        
  
    