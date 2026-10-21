
"""사진 보정값의 공통 자료형: GUI, 이력, 저장 엔진이 동일하게 사용합니다."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AdjustmentSettings:
    """
    한 시점의 보정값입니다.
    불변 객체이므로 과거 이력이 변하지 않습니다.
    """

    # 노출 보정(실수, 보통 -3.0 ~ +3.0)
    exposure_ev: float = 0.0

    # 대비(정수, -100 ~ +100)
    contrast: int = 0

    # 채도(정수, -100 ~ +100)
    saturation: int = 0

    # 간이 색온도(정수, -100 ~ +100)
    warmth: int = 0

    def as_kwargs(self) -> dict[str, float | int]:
        """
        processing.apply_adjustments()에 전달할
        키워드 인수를 만듭니다.
        """
        return {
            "exposure_ev": self.exposure_ev,
            "contrast": self.contrast,
            "saturation": self.saturation,
            "warmth": self.warmth,
        }
