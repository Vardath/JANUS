import unittest

from src.fano_core import FanoJanusUnit, fano_completion


class FanoSemanticTests(unittest.TestCase):
    def test_fano_line_completion_uses_binary_geometry(self):
        self.assertEqual(fano_completion(1, 2), 3)
        self.assertEqual(fano_completion(4, 7), 3)
        self.assertEqual(fano_completion(2, 5), 7)
        self.assertEqual(fano_completion(3, 3), 0)
        self.assertEqual(fano_completion(0, 6), 0)

    def test_direction_changes_which_input_receives_attention(self):
        texts = [
            "A speculative analogy might connect these two ideas.",
            "Measured data and verified source evidence support the recorded value.",
            "An alternative explanation could make the current interpretation fail.",
        ]
        u = FanoJanusUnit()
        u.active_direction = 1
        self.assertIn("Measured data", u.choose_focus(texts))
        u.active_direction = 4
        self.assertIn("alternative explanation", u.choose_focus(texts))
        u.active_direction = 6
        self.assertIn("speculative analogy", u.choose_focus(texts))

    def test_projection_changes_processing_pressure(self):
        u = FanoJanusUnit(weights=[100, 1, 1, 1, 1, 1, 1, 1])
        self.assertEqual(u.processing_pressure()["dominant"], "conservative")
        u.weights = [1, 30, 30, 30, 1, 1, 1, 1]
        self.assertEqual(u.processing_pressure()["dominant"], "coherent")
        u.weights = [1, 1, 1, 1, 30, 30, 30, 30]
        self.assertEqual(u.processing_pressure()["dominant"], "exploratory")

    def test_integration_completion_can_bias_persistent_state(self):
        u = FanoJanusUnit(weights=[8, 20, 18, 1, 1, 1, 1, 1], active_direction=1)
        completion = u.integration_completion(["evidence: Fano d1", "logic: Fano d2"])
        self.assertEqual(completion, 3)
        before = u.weights[3]
        u.bias(completion, 2)
        self.assertEqual(u.weights[3], before + 2)

    def test_summary_exposes_meaning_not_just_number(self):
        u = FanoJanusUnit(weights=[8, 1, 1, 1, 1, 1, 20, 1], active_direction=6)
        s = u.summary()
        self.assertEqual(s["orientation"], "novelty")
        self.assertIn("testable", s["directive"])
        self.assertIn("processing_pressure", s)


if __name__ == "__main__":
    unittest.main()
