import unittest

import routing_policy


class FakeCycle:
    def __init__(self):
        self.sent = []
        self._remote_summaries = {}
        self._last_consensus = ""
        self._last_interface = ""
        self.checkpoints = 0

    def send(self, sender, recipient, content, kind="peer"):
        self.sent.append((sender, recipient, kind, content))

    def checkpoint(self):
        self.checkpoints += 1
        return True


class ForwardRoutingTests(unittest.TestCase):
    def setUp(self):
        self.cycle = FakeCycle()
        routing_policy.install(self.cycle)

    def test_ordinary_path_is_forward_only(self):
        self.cycle._route_output("evidence", "e")
        self.cycle._route_output("left_hemisphere", "l")
        self.cycle._route_output("consensus", "c")
        self.cycle._route_output("interface", "i")
        edges = [(s, r, k) for s, r, k, _ in self.cycle.sent]
        self.assertIn(("evidence", "left_hemisphere", "specialist"), edges)
        self.assertIn(("left_hemisphere", "consensus", "hemisphere"), edges)
        self.assertIn(("consensus", "interface", "consensus"), edges)
        self.assertNotIn(("left_hemisphere", "right_hemisphere", "cross_hemisphere"), edges)
        self.assertFalse(any(s == "consensus" and r in {"left_hemisphere", "right_hemisphere"} for s, r, _, _ in self.cycle.sent))
        self.assertFalse(any(s == "interface" and r == "consensus" for s, r, _, _ in self.cycle.sent))

    def test_remote_feedback_reenters_only_through_specialists(self):
        self.cycle.accept_remote_summary(
            "acct-1:phone",
            {"phase": "wake", "consensus": "phone consensus", "interface": "phone interface", "cycles": {"interface": 9}},
        )
        recipients = [r for _, r, _, _ in self.cycle.sent]
        self.assertIn("context", recipients)
        self.assertIn("counterpoint", recipients)
        self.assertNotIn("consensus", recipients)
        self.assertNotIn("interface", recipients)
        self.assertTrue(all("[feedback-only]" in text for _, _, _, text in self.cycle.sent))
        self.assertIn("acct-1:phone", self.cycle._remote_summaries)


if __name__ == "__main__":
    unittest.main()
