import unittest

from cartoon_engine.recovery import FrameState, RecoveryController


class RecoveryTests(unittest.TestCase):
    def test_verified_frame_is_never_retried(self):
        c = RecoveryController([1, 2], max_attempts=3)
        c.claim(1, "w1")
        c.verify(1, True, "f1.png", "abc")
        self.assertEqual(c.frames[1].state, FrameState.VERIFIED)
        self.assertEqual(c.claim(1, "w2").state, FrameState.VERIFIED)

    def test_failed_frame_retries_only_until_bound(self):
        c = RecoveryController([1], max_attempts=2)
        c.claim(1, "w1")
        c.verify(1, False, reason="bad image")
        self.assertEqual(c.frames[1].state, FrameState.RETRY)
        c.claim(1, "w2")
        c.verify(1, False, reason="still bad")
        self.assertEqual(c.frames[1].state, FrameState.DEAD)
        self.assertEqual(c.retry_ids(), [])

    def test_progress_is_fail_closed(self):
        c = RecoveryController([1, 2, 3])
        c.claim(1, "w1")
        c.verify(1, True)
        self.assertEqual(c.progress()["verified"], 1)
        self.assertEqual(c.progress()["percent"], 100 / 3)

    def test_blocked_frame_is_terminal(self):
        c = RecoveryController([1])
        c.block(1, "captcha_detected")
        self.assertEqual(c.frames[1].state, FrameState.BLOCKED)
        with self.assertRaises(RuntimeError):
            c.claim(1, "w1")


if __name__ == "__main__":
    unittest.main()
