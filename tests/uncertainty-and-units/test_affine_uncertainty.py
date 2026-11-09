"""Uncertainty conversions must not depend on a temperature scale's origin."""
import json
import math
from pathlib import Path
import subprocess
import sys
import unittest

SKILL_ROOT = Path(__file__).resolve().parents[2] / 'skills' / 'uncertainty-and-units'
sys.path.insert(0, str(SKILL_ROOT / 'scripts'))
import convert_units

try:
    import pint
except ImportError:
    pint = None


@unittest.skipIf(pint is None, 'pint is required')
class AffineUncertaintyTests(unittest.TestCase):
    def setUp(self):
        self.registry = convert_units.build_registry()

    def test_temperature_uncertainties_are_independent_of_origin(self):
        cases = [('degC', 'K', 1), ('K', 'degC', 1),
                 ('degC', 'degF', 1.8), ('degF', 'degC', 1/1.8),
                 ('K', 'degF', 1.8), ('degF', 'K', 1/1.8)]
        for source, target, scale in cases:
            for value in [-40.0, -1e-12, 0.0, 1e-12, 20.0, 1e12]:
                with self.subTest(source=source, target=target, value=value):
                    result = convert_units.propagate(self.registry, value, 0.1,
                                                     source, target, [], {})
                    self.assertTrue(math.isclose(result, 0.1 * scale, rel_tol=1e-12))

    def test_multiplicative_uncertainty_does_not_need_resolvable_value_step(self):
        for value in [-1e-320, 0.0, 1e-320, 1e300]:
            for source, target, expected in [('nm', 'm', 1e-10), ('m', 'nm', 1e8)]:
                with self.subTest(value=value, source=source, target=target):
                    result = convert_units.propagate(self.registry, value, 0.1,
                                                     source, target, [], {})
                    self.assertTrue(math.isclose(result, expected, rel_tol=1e-12))

    def test_zero_uncertainty_stays_zero(self):
        self.assertEqual(convert_units.propagate(self.registry, 1e-12, 0,
                                                'degC', 'K', [], {}), 0)

    def test_cli_preserves_nonzero_uncertainty_near_celsius_zero(self):
        completed = subprocess.run([sys.executable, '-B', str(SKILL_ROOT / 'scripts' / 'convert_units.py'),
                                    '--value', '1e-12', '--unit', 'degC', '--to', 'kelvin',
                                    '--uncertainty', '0.1'], capture_output=True, text=True, check=True)
        report = json.loads(completed.stdout)
        self.assertEqual(report['uncertainty'], 0.1)
        self.assertEqual(report['uncertainty_unit'], 'kelvin')
        self.assertAlmostEqual(report['value'], 273.150000000001)

    def test_reciprocal_context_retains_scale_invariance(self):
        first = convert_units.propagate(self.registry, 532., .5, 'nm', 'eV', ['spectroscopy'], {})
        second = convert_units.propagate(self.registry, 5.32e-7, 5e-10, 'm', 'eV', ['spectroscopy'], {})
        energy = convert_units.convert(self.registry, 532., 'nm', 'eV', ['spectroscopy'], {}).magnitude
        self.assertTrue(math.isclose(first, energy * .5 / 532, rel_tol=1e-8))
        self.assertTrue(math.isclose(second, first, rel_tol=1e-8))

    def test_logarithmic_conversion_retains_local_derivative(self):
        result = convert_units.propagate(self.registry, 10., .1, 'mW', 'dBm', [], {})
        self.assertTrue(math.isclose(result, 10/math.log(10)*.1/10, rel_tol=1e-8))


if __name__ == '__main__':
    unittest.main()
