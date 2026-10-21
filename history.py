
"""
확정된 보정값의 Undo/Redo 이력만 관리합니다.
Qt에 의존하지 않습니다.
"""

from models import AdjustmentSettings


class AdjustmentHistory:
    """
    보정 설정 스냅샷 목록과 현재 인덱스를 관리합니다.
    """

    def __init__(
        self,
        initial: AdjustmentSettings | None = None,
        max_steps: int = 100,
    ) -> None:

        # max_steps:
        # 취소 가능한 과거 단계 수(int)
        if max_steps < 1:
            raise ValueError(
                "max_steps는 1 이상이어야 합니다."
            )

        self._max_steps = max_steps
        self.clear(initial)

    @property
    def current(self) -> AdjustmentSettings:
        """
        _position이 가리키는 현재 확정 설정을 반환합니다.
        """
        return self._states[self._position]

    @property
    def can_undo(self) -> bool:
        """
        현재 위치보다 앞에 기록이 있으면 True입니다.
        """
        return self._position > 0

    @property
    def can_redo(self) -> bool:
        """
        현재 위치 뒤에 기록이 있으면 True입니다.
        """
        return self._position < len(self._states) - 1

    @property
    def length(self) -> int:
        """
        저장된 확정 상태의 개수를 반환합니다.
        테스트 및 상태 표시용입니다.
        """
        return len(self._states)

    def record(
        self,
        settings: AdjustmentSettings
    ) -> bool:
        """
        새 확정 상태를 기록합니다.
        동일하면 False를 반환합니다.
        """

        if settings == self.current:
            return False

        # Undo 이후 새 편집을 하면
        # 사용하지 않는 Redo 분기를 버립니다.
        del self._states[self._position + 1:]

        self._states.append(settings)

        # 현재 상태 1개와 최대 max_steps개 과거 상태 유지
        excess = (
            len(self._states) - (self._max_steps + 1)
        )

        if excess > 0:
            del self._states[:excess]

        # 마지막 요소가 현재 상태가 됩니다.
        self._position = len(self._states) - 1

        return True

    def undo(self) -> AdjustmentSettings:
        """
        기록 하나를 이전으로 이동하고 설정을 반환합니다.
        """
        if self.can_undo:
            self._position -= 1

        return self.current

    def redo(self) -> AdjustmentSettings:
        """
        기록 하나를 다음으로 이동하고 설정을 반환합니다.
        """
        if self.can_redo:
            self._position += 1

        return self.current

    def clear(
        self,
        initial: AdjustmentSettings | None = None
    ) -> None:
        """
        새 문서를 열 때 이력을 초기 상태 하나로 교체합니다.
        """
        self._states = [
            initial if initial is not None
            else AdjustmentSettings()
        ]

        self._position = 0
