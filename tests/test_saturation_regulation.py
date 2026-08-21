import unittest

import saturation_regulation as sr


class _Fano:
    def __init__(self, exploratory):
        self._x = exploratory
    def processing_pressure(self):
        return {"exploratory": self._x}


class _Core:
    def __init__(self, exploratory):
        self.fano = _Fano(exploratory)


class _Cycle:
    def __init__(self, vals):
        names=("counterpoint","left_hemisphere","right_hemisphere","consensus","interface")
        self.cores={n:_Core(v) for n,v in zip(names,vals)}


class SaturationRegulationTests(unittest.TestCase):
    def test_exploratory_pressure_is_mean_of_integration_layer(self):
        c=_Cycle([0.50,0.40,0.60,0.45,0.55])
        self.assertAlmostEqual(sr._exploratory_pressure(c),0.50,places=6)

    def test_missing_or_invalid_runtime_does_not_invent_pressure(self):
        class Broken: cores={}
        self.assertEqual(sr._exploratory_pressure(Broken()),0.0)

    def test_thresholds_are_nontrivial(self):
        self.assertGreaterEqual(sr.SATURATION_IMBALANCE,1.0)
        self.assertGreater(sr.SATURATION_EXPLORATORY,0.0)
        self.assertLess(sr.SATURATION_EXPLORATORY,1.0)
        self.assertGreaterEqual(sr.SATURATION_COOLDOWN,300)


if __name__ == "__main__":
    unittest.main()
