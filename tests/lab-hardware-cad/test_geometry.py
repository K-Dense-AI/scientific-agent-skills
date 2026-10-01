"""Native OCCT regressions; run with the per-skill isolated environment."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

bd = pytest.importorskip('build123d')
SKILL_ROOT = Path(__file__).resolve().parents[2] / 'skills' / 'lab-hardware-cad'
SCRIPTS = SKILL_ROOT / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import _common


def cli(script, *args):
    return subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)],
                          text=True, capture_output=True, timeout=120,
                          env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})


def test_boolean_interference_touching_and_separation():
    a = bd.Box(10, 10, 10)
    assert _common.intersection_volume(a, bd.Pos(5, 0, 0) * a) == pytest.approx(500)
    assert _common.intersection_volume(a, bd.Pos(10, 0, 0) * a) == pytest.approx(0)
    b = bd.Pos(10.3, 0, 0) * a
    assert _common.intersection_volume(a, b) == pytest.approx(0)
    assert a.distance_to(b) == pytest.approx(0.3)


def test_oblique_cylinder_census_uses_axial_not_world_bbox_span():
    part = bd.Pos(7, 2, 4) * bd.Rot(30, 45, 0) * bd.Cylinder(3, 10)
    rows = _common.cylinder_census(part)
    assert len(rows) == 1
    assert rows[0]['diameter_mm'] == pytest.approx(6)
    assert rows[0]['extent_mm'] == pytest.approx(10, abs=1e-4)
    assert rows[0]['sweep_deg'] == pytest.approx(360)


def test_gauges_measure_holes_and_preserve_small_failure():
    part = bd.Box(10, 10, 4) - bd.Cylinder(2, 6)
    checks = _common.normalise_checks([
        {'clear': {'cylinder': 3.9}},
        {'material': {'box': (1, 1, 1), 'at': [(3, 3, 0)]}, 'min_mm3': 0.9},
        {'clear': {'cylinder': 5}},
    ])
    assert [r['pass'] for r in _common.evaluate_checks(part, checks)] == [True, True, False]
    # Before this fix, four-decimal rounding made 0.01001 <= 0.01 pass.
    tiny = bd.Box(1, 1, 0.01001)
    entry = _common.normalise_checks([{'clear': {'box': (2, 2, 2)}, 'tol_mm3': 0.01}])
    assert not _common.evaluate_checks(tiny, entry)[0]['pass']


def test_documented_carrier_exports_mm_step_cut_dxf_and_snapshot(tmp_path):
    import re
    import ezdxf
    from PIL import Image
    code = re.findall(r'```python\n(.*?)```', (SKILL_ROOT / 'SKILL.md').read_text(), re.S)[0]
    model = tmp_path / 'carrier_model.py'
    model.write_text(code)
    run = cli('gen.py', model, '--outdir', tmp_path, '--dxf', '--json')
    assert run.returncode == 0, run.stderr
    manifest = json.loads(run.stdout)
    assert manifest['geometry']['solid_count'] == 1
    assert manifest['geometry_checks']['pass']
    assert manifest['interfaces'][0]['value'] == pytest.approx(129.06)
    part = bd.import_step(tmp_path / 'carrier.step')
    # Independently derived: 127.76 + overall tolerance .5 + clearance .8 + walls 6.
    assert part.bounding_box().size.X == pytest.approx(135.06)
    assert part.bounding_box().size.Z == pytest.approx(12)
    assert part.volume == pytest.approx(135.06 * 92.78 * 12 - 129.06 * 86.78 * 9.5)
    drawing = ezdxf.readfile(tmp_path / 'carrier.dxf')
    assert drawing.header['$INSUNITS'] == 4  # millimetres
    assert set(e.dxf.layer for e in drawing.modelspace()) == {'CUT'}
    assert (tmp_path / 'carrier.stl').stat().st_size > 100
    check = cli('check.py', '--json', 'geometry', tmp_path / 'carrier.step', '--model', model)
    assert check.returncode == 0, check.stderr
    snapshot = cli('snapshot.py', tmp_path / 'carrier.step', '--out', tmp_path / 'carrier.png')
    assert snapshot.returncode == 0, snapshot.stderr
    with Image.open(tmp_path / 'carrier.png') as img:
        assert img.width > 1000 and img.height > 500


def test_geometry_overrides_match_exported_source_parameters(tmp_path):
    model = tmp_path / 'height_model.py'
    model.write_text('from build123d import Box\nheight_mm=4.0\n'
                     'def build(): return Box(5,5,height_mm)\n'
                     'def checks(): return [{"bbox_z":{"min":height_mm,"max":height_mm}}]\n')
    run = cli('gen.py', model, '--outdir', tmp_path, '--param', 'height_mm=6', '--no-stl')
    assert run.returncode == 0, run.stderr
    bad = cli('check.py', 'geometry', tmp_path / 'height.step', '--model', model)
    assert bad.returncode == 1
    good = cli('check.py', 'geometry', tmp_path / 'height.step', '--model', model,
               '--param', 'height_mm=6')
    assert good.returncode == 0, good.stderr


def test_top_face_counterbore_and_selectors():
    with bd.BuildPart() as builder:
        bd.Box(60, 60, 10)
        top = builder.faces().sort_by(bd.Axis.Z)[-1]
        with bd.Locations(top):
            with bd.Locations((20, 20)):
                bd.CounterBoreHole(radius=3.3, counter_bore_radius=5.5, counter_bore_depth=6.5)
    rows = _common.cylinder_census(builder.part)
    head = next(r for r in rows if r['diameter_mm'] == 11)
    assert head['span_min_mm'] == pytest.approx(-1.5)
    assert head['span_max_mm'] == pytest.approx(5)
    with bd.BuildPart() as styled:
        bd.Box(80, 60, 10)
        bd.chamfer(styled.edges().group_by(bd.Axis.Z)[-1], length=4)
        bd.fillet(styled.edges().filter_by(bd.Axis.Z), radius=5)
    assert styled.part.is_valid


def test_cage_model_grid_sketch_and_current_api(tmp_path):
    import re
    text = (SKILL_ROOT / 'references' / 'build123d-patterns.md').read_text()
    code = re.findall(r'```python\n(.*?)```', text, re.S)[1]
    model = tmp_path / 'cage_model.py'
    model.write_text(code)
    run = cli('gen.py', model, '--outdir', tmp_path, '--no-stl')
    assert run.returncode == 0, run.stderr
    part = bd.import_step(tmp_path / 'cage.step')
    rows = _common.cylinder_census(part)
    rods = [r for r in rows if r['diameter_mm'] == 6.4]
    assert len(rods) == 4
    assert {tuple(r['at_mm']) for r in rods} == {(15,15), (-15,15), (15,-15), (-15,-15)}
    with bd.BuildPart() as bracket:
        with bd.BuildSketch():
            bd.Rectangle(40, 20)
            with bd.Locations((15, 0)):
                bd.Circle(4, mode=bd.Mode.SUBTRACT)
        bd.extrude(amount=6)
    assert bracket.part.is_valid
    with bd.BuildPart() as grid:
        bd.Box(40, 30, 5)
        with bd.GridLocations(9, 9, 3, 2):
            bd.Hole(1.5)
    assert len(_common.cylinder_census(grid.part)) == 6


def test_bbox_gauge_does_not_round_away_limit_violation():
    part = bd.Box(1, 1, 10.00001)
    checks = _common.normalise_checks([{'bbox_z': {'max': 10}}])
    assert not _common.evaluate_checks(part, checks)[0]['pass']
