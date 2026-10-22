
"""
LocalPhoto Studio - 공통 보정 설정 모델

GUI, Undo/Redo, CPU 보정 엔진, 저장 엔진이
동일한 보정 설정을 사용합니다.
"""

from dataclasses import dataclass


# CurvePoints:
# 톤 커브 제어점의 자료형입니다.
#
# 각 제어점: (입력 밝기, 출력 밝기)
# 전체 형태: ((x1, y1), (x2, y2), ...)
CurvePoints = tuple[tuple[int, int], ...]


# 기본 톤 커브는 입력과 출력이 같은 직선입니다.
# 예: 128 → 128
IDENTITY_CURVE: CurvePoints = (
    (0, 0),
    (255, 255)
)


@dataclass(frozen=True, slots=True)
class AdjustmentSettings:
    """
    특정 시점의 보정값을 보관합니다.

    frozen=True:
        객체 생성 후 값을 직접 변경하지 못합니다.
        과거 Undo 이력을 보호하기 위한 설정입니다.

    slots=True:
        객체가 사용하는 속성을 명확하게 제한합니다.
    """

    # 노출(EV)
    exposure_ev: float = 0.0

    # 대비(-100 ~ 100)
    contrast: int = 0

    # 채도(-100 ~ 100)
    saturation: int = 0

    # 간이 색온도(-100 ~ 100)
    warmth: int = 0

    # 톤 커브 제어점
    #
    # tuple은 불변 자료형이므로
    # 과거 이력의 제어점이 실수로 바뀌지 않습니다.
    curve_points: CurvePoints = IDENTITY_CURVE

    def as_kwargs(
        self
    ) -> dict[str, float | int | CurvePoints]:
        """
        보정 엔진에 전달할 키워드 인수를 반환합니다.

        반환값:
            dict

        예:
            {
                "exposure_ev": 1.0,
                "contrast": 20,
                ...
                "curve_points": ((0, 0), (255, 255))
            }
        """

        return {
            "exposure_ev": self.exposure_ev,
            "contrast": self.contrast,
            "saturation": self.saturation,
            "warmth": self.warmth,
            "curve_points": self.curve_points
        }
