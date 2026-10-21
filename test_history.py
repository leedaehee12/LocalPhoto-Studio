
"""
LocalPhoto Studio - Undo/Redo 단위 테스트

Qt GUI 없이 순수 Python 코드만으로
보정 이력 관리가 정상인지 검증합니다.
"""

import unittest

from history import (
    AdjustmentHistory,
    AdjustmentSettings
)


class TestHistory(unittest.TestCase):

    def test_undo_redo(self):
        """기록 후 이전/다음 상태로 이동하는지 검사"""

        # history: 새로운 이력 관리 객체
        history = AdjustmentHistory()

        # brighter: 노출을 +1.0 EV로 설정한 상태
        brighter = AdjustmentSettings(exposure_ev=1.0)

        history.record(brighter)

        # Undo 후에는 원래 설정이어야 합니다.
        self.assertEqual(
            history.undo(),
            AdjustmentSettings()
        )

        # Redo 후에는 +1.0 EV로 복원되어야 합니다.
        self.assertEqual(
            history.redo(),
            brighter
        )

    def test_duplicate(self):
        """동일한 설정을 중복 기록하지 않는지 검사"""

        history = AdjustmentHistory()

        self.assertFalse(
            history.record(AdjustmentSettings())
        )

        self.assertFalse(history.can_undo)

    def test_redo_removed(self):
        """Undo 이후 새로운 편집을 하면 Redo 기록 삭제"""

        history = AdjustmentHistory()

        history.record(AdjustmentSettings(contrast=10))
        history.record(AdjustmentSettings(contrast=20))

        history.undo()

        history.record(
            AdjustmentSettings(saturation=30)
        )

        self.assertFalse(history.can_redo)

    def test_history_limit(self):
        """최대 이력 수가 적용되는지 검사"""

        # 최대 2단계까지만 되돌릴 수 있습니다.
        history = AdjustmentHistory(max_steps=2)

        for value in (10, 20, 30):
            history.record(
                AdjustmentSettings(contrast=value)
            )

        self.assertEqual(history.undo().contrast, 20)
        self.assertEqual(history.undo().contrast, 10)
        self.assertFalse(history.can_undo)

    def test_clear(self):
        """새 사진을 열 때 기존 이력을 제거하는지 검사"""

        history = AdjustmentHistory()

        history.record(
            AdjustmentSettings(exposure_ev=1.5)
        )

        history.clear()

        self.assertEqual(
            history.current,
            AdjustmentSettings()
        )

        self.assertFalse(history.can_undo)


if __name__ == "__main__":
    unittest.main()
