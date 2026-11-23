"""Nominal calibration levels must not depend on concentration unit scale."""
import json
import math
from pathlib import Path
import subprocess
import sys
import unittest

SKILL_ROOT = Path(__file__).resolve().parents[2] / 'skills' / 'analytical-method-validation'
sys.path.insert(0, str(SKILL_ROOT / 'scripts'))
import _common as common


def observations(scale, curved=False):
    return [{'level': level * scale,
             'response': (level ** 2 if curved else 2 * level) + error * (-1 if level % 2 else 1)}
            for level in range(1, 6) for error in (-.02, .02)]


def report(rows, weight='none'):
    completed = subprocess.run([sys.executable, '-B', str(SKILL_ROOT / 'scripts' / 'check_response.py'),
                                '-i', '-', '--format', 'json', '--weight', weight,
                                '--max-back-calc-error', '1'], input=json.dumps(rows),
                               capture_output=True, text=True)
    if completed.returncode not in (0, 1):
        raise AssertionError(completed.stderr)
    return completed.returncode, json.loads(completed.stdout)[0]


class LevelIdentityTests(unittest.TestCase):
    def test_linear_cli_preserves_levels_and_findings_across_unit_scales(self):
        baseline_code, baseline = report(observations(1))
        self.assertEqual(baseline_code, 0)
        for weight in ('none', '1/x', '1/x2'):
            for scale in (1e-13, 1e-6, 1e6):
                with self.subTest(weight=weight, scale=scale):
                    code, actual = report(observations(scale), weight)
                    self.assertEqual(code, 0, actual['findings'])
                    self.assertEqual(actual['summary']['distinct levels'], 5)
                    self.assertEqual([r['n'] for r in actual['levels']], [2] * 5)
                    self.assertEqual([r['level'] for r in actual['levels']],
                                     [i * scale for i in range(1, 6)])
                    self.assertAlmostEqual(actual['summary']['lack-of-fit p'], 1, places=8)
                    for row in actual['levels']:
                        self.assertAlmostEqual(row['relative_error_pct'], 0, places=8)

    def test_curvature_lack_of_fit_is_scale_invariant(self):
        for weight in ('none', '1/x', '1/x2'):
            baseline = None
            for scale in (1, 1e-13, 1e6):
                rows = observations(scale, curved=True)
                xs = [row['level'] for row in rows]
                ys = [row['response'] for row in rows]
                weights = None if weight == 'none' else [1/x**(1 if weight == '1/x' else 2) for x in xs]
                actual = common.lack_of_fit(xs, ys, common.fit_linear(xs, ys, weights))
                with self.subTest(weight=weight, scale=scale):
                    self.assertTrue(actual['applicable'])
                    self.assertEqual(actual['levels'], 5)
                    self.assertEqual(actual['df_lack_of_fit'], 3)
                    self.assertEqual(actual['df_pure_error'], 5)
                    self.assertLess(actual['p_value'], .001)
                    if baseline is not None:
                        self.assertTrue(math.isclose(actual['f_statistic'], baseline['f_statistic'], rel_tol=1e-9))
                        self.assertTrue(math.isclose(actual['p_value'], baseline['p_value'], rel_tol=1e-9))
                    baseline = actual

    def test_nominal_levels_are_not_rounded_before_back_calculation(self):
        rows = [{'level': (i + .1) * 1e-12, 'response': 2 * (i + .1) + error}
                for i in range(1, 6) for error in (-.02, .02)]
        _, actual = report(rows)
        self.assertEqual([row['level'] for row in actual['levels']],
                         [(i + .1) * 1e-12 for i in range(1, 6)])
        for row in actual['levels']:
            self.assertAlmostEqual(row['relative_error_pct'], 0, places=8)

    def test_numeric_spellings_share_a_nominal_level(self):
        rows = [{'level': text, 'response': response}
                for i in range(1, 6)
                for text, response in [(f'{i}e-13', 2*i-.02), (format(i*1e-13, '.13f'), 2*i+.02)]]
        _, actual = report(rows)
        self.assertEqual([row['n'] for row in actual['levels']], [2] * 5)

    def test_close_but_distinct_nominals_do_not_manufacture_replicates(self):
        xs = [1e-13, 1.1e-13, 2e-13, 2.1e-13, 3e-13, 3.1e-13]
        ys = [1., 1.1, 2., 2.1, 3., 3.1]
        result = common.lack_of_fit(xs, ys, common.fit_linear(xs, ys))
        self.assertFalse(result['applicable'])
        self.assertEqual(result['levels'], 6)
        self.assertEqual(result['replicated_levels'], 0)


if __name__ == '__main__':
    unittest.main()
