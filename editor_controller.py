
"""
슬라이더 입력 한 번을 편집 '한 건'으로 묶는 상태 제어기.
Qt에 의존하지 않습니다.
"""

from dataclasses import replace

from history import AdjustmentHistory
from models import AdjustmentSettings


class EditorController:
    """
    현재 임시 보정값과 확정된 Undo/Redo 이력의 소유자입니다.
    """

    def __init__(self, max_steps: int = 100) -> None:

        # history:
        # 확정된 보정값만 저장하는 AdjustmentHistory 객체
        self.history = AdjustmentHistory(
            max_steps=max_steps
        )

        # _draft:
        # 편집 도중 화면에 표시할 현재 보정값(불변 객체)
        self._draft = self.history.current

        # _editing:
        # 하나의 편집 작업이 진행 중인지 여부(bool)
        self._editing = False

    @property
    def settings(self) -> AdjustmentSettings:
        """
        현재 미리보기/저장에 반영할 보정값을 반환합니다.
        """
        return self._draft

    @property
    def editing(self) -> bool:
        return self._editing

    @property
    def dirty(self) -> bool:
        """
        임시 상태가 최근 확정 상태와 다르면 True입니다.
        """
        return self._draft != self.history.current

    @property
    def can_undo(self) -> bool:
        return self.dirty or self.history.can_undo

    @property
    def can_redo(self) -> bool:
        return (
            not self.dirty
            and self.history.can_redo
        )

    def begin_edit(self) -> None:
        """
        입력 묶음의 시작입니다.
        연속 호출은 새 이력을 만들지 않습니다.
        """
        self._editing = True

    def set_value(
        self,
        field: str,
        value: float | int
    ) -> None:
        """
        한 보정 항목을 변경합니다.

        field:
            보정 항목 이름(str)
            예: "exposure_ev"

        value:
            적용할 숫자(float 또는 int)
        """

        if not self._editing:
            raise RuntimeError(
                "값을 변경하기 전에 begin_edit()을 호출해야 합니다."
            )

        if field not in AdjustmentSettings.__dataclass_fields__:
            raise ValueError(
                f"지원하지 않는 보정 항목: {field}"
            )

        # replace():
        # 기존 _draft를 수정하지 않고
        # 필드 하나만 바꾼 새 객체를 생성합니다.
        self._draft = replace(
            self._draft,
            **{field: value}
        )

    def set_settings(
        self,
        settings: AdjustmentSettings
    ) -> None:
        """
        초기화처럼 모든 보정값을 한 번에 변경합니다.
        """

        if not self._editing:
            raise RuntimeError(
                "설정 변경 전에 begin_edit()을 호출해야 합니다."
            )

        self._draft = settings

    def commit_edit(self) -> bool:
        """
        편집 종료 시 실행합니다.

        시작부터 종료까지의 중간 변경값을
        하나의 이력으로 확정합니다.
        """

        if not self._editing:
            return False

        self._editing = False

        # 같은 값이면 record()가 False를 반환합니다.
        return self.history.record(self._draft)

    def cancel_edit(self) -> None:
        """
        진행 중인 편집을 버리고
        마지막 확정 상태로 되돌립니다.
        """
        self._editing = False
        self._draft = self.history.current

    def undo(self) -> AdjustmentSettings:
        """
        미확정 편집이 있으면 먼저 취소합니다.
        없으면 과거 확정 상태로 이동합니다.
        """

        if self.dirty:
            self.cancel_edit()
            return self._draft

        self._editing = False
        self._draft = self.history.undo()

        return self._draft

    def redo(self) -> AdjustmentSettings:
        """
        미확정 편집은 취소합니다.
        그렇지 않으면 다음 확정 상태로 이동합니다.
        """

        if self.dirty:
            self.cancel_edit()
            return self._draft

        self._editing = False
        self._draft = self.history.redo()

        return self._draft

    def clear_document(self) -> None:
        """
        다른 사진으로 전환할 때
        이전 상태와 이력을 완전히 초기화합니다.
        """

        self.history.clear()
        self._draft = self.history.current
        self._editing = False
