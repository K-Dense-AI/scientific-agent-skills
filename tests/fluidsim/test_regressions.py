"""Regression checks for real FluidSim formats and bounded plans."""
from __future__ import annotations

from copy import deepcopy
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SKILL_ROOT = Path(__file__).resolve().parents[2] / 'skills' / 'fluidsim'
sys.path.insert(0, str(SKILL_ROOT / 'scripts'))
import _schema
from _common import ToolError
from _profiles import PROFILES
import budget_summary
import grid_resource_estimator
import restart_compatibility
import simulation_dry_run


class PlanningRegressions(unittest.TestCase):
    def test_solver_specific_output_and_initialization_rejected(self):
        config = _schema.example_config()
        config['solver'] = 'ns3d'
        config['parameters']['oper'].update(nz=32, Lz=6.283185307179586)
        config['parameters']['init_fields'] = {'type': 'jet'}
        result = _schema.validate_config(config)
        codes = {x['code'] for x in result['errors']}
        self.assertIn('unsupported_solver_output', codes)
        self.assertIn('unknown_initialization', codes)

    def test_records_are_not_capped_to_declared_file_count(self):
        config = _schema.example_config()
        config['resources']['max_output_files'] = 10
        config['parameters']['output']['periods_save']['phys_fields'] = 0.0001
        result = grid_resource_estimator.estimate(config, precision_bytes=8, workspace_factor=8, safety_factor=1.5, compression_ratio=1)
        self.assertEqual(result['estimates']['state_snapshots'], 1002)
        self.assertFalse(result['ok'])
        self.assertGreater(result['estimates']['storage_bytes'], 1000 * result['estimates']['state_snapshot_bytes'])

    def test_non_square_spectral_shape_reduces_x(self):
        config = _schema.example_config()
        config['parameters']['oper'].update(nx=16, ny=64)
        result = grid_resource_estimator.estimate(config, precision_bytes=8, workspace_factor=8, safety_factor=1.5, compression_ratio=1)
        self.assertEqual(result['grid']['spectral_shape_estimate'], [64, 9])

    def test_unmodeled_outputs_are_not_reported_as_a_resource_fit(self):
        config = _schema.example_config()
        config['parameters']['output']['periods_save']['increments'] = 0.01
        result = grid_resource_estimator.estimate(config, precision_bytes=8, workspace_factor=8, safety_factor=1.5, compression_ratio=1)
        self.assertFalse(result['ok'])
        self.assertEqual(result['assumptions']['unmodeled_enabled_outputs'], ['increments'])

    def test_invalid_scalars_have_controlled_errors(self):
        for path, value in [('nu_2', 10**400), ('nu_2', float('inf'))]:
            config = _schema.example_config()
            config['parameters'][path] = value
            with self.assertRaises(ToolError):
                _schema.validate_config(config)
        config = _schema.example_config()
        config['parameters']['time_stepping']['type_time_scheme'] = []
        with self.assertRaises(ToolError):
            _schema.validate_config(config)

    def test_in_script_initialization_cannot_generate_an_empty_experiment(self):
        config = _schema.example_config()
        config['parameters']['init_fields'] = {'type': 'in_script'}
        with self.assertRaisesRegex(ToolError, 'separately implemented'):
            simulation_dry_run.render_script(config)

    def test_time_and_correlation_bounds(self):
        config = _schema.example_config()
        config['parameters']['time_stepping'].update(USE_T_END=False)
        self.assertFalse(_schema.validate_config(config)['ok'])
        config = _schema.example_config()
        config['parameters']['time_stepping']['max_elapsed'] = '00:06:00'
        self.assertFalse(_schema.validate_config(config)['ok'])
        config = _schema.example_config()
        config['parameters']['forcing'].update(enable=True, type='tcrandom', forcing_rate=0, tcrandom={'time_correlation':'based_on_forcing_rate'})
        self.assertFalse(_schema.validate_config(config)['ok'])


class ScalarRegressions(unittest.TestCase):
    def test_real_semicolon_records_keep_all_budget_terms(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'spatial_means.txt'
            p.write_text('####\ntime = 0\nE = 2 ; Z = 3\nepsK = 1 ; epsK_hypo = 0.5 ; epsK_tot = 1.5\nPK1 = nan ; PK2 = inf ; PK_tot = 1e309\n')
            r = budget_summary.summarize_scalar_file(p, max_records=100)
        self.assertEqual(r['metrics']['Z']['last'], 3)
        self.assertEqual(r['metrics']['epsK_tot']['mean'], 1.5)
        self.assertEqual(r['metrics']['PK_tot']['nonfinite_count'], 1)
        self.assertIsNone(r['metrics']['PK1']['mean'])


class Hdf5Regressions(unittest.TestCase):
    def setUp(self):
        try:
            import h5py
            import numpy
        except ImportError:
            self.skipTest('requires h5py and NumPy')
        self.h5py = h5py
        self.np = numpy
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def checkpoint(self, name, time, *, shape=(32,32), variable='rot'):
        path = self.root/name
        with self.h5py.File(path, 'w') as f:
            state = f.create_group('state_phys')
            state.attrs.update(time=time, it=1)
            state.create_dataset(variable, shape=shape, dtype='f8')
            info=f.create_group('info_simul')
            info.create_group('solver').attrs['module_name']='fluidsim.solvers.ns2d.solver'
            p=info.create_group('params')
            p.create_group('oper').attrs.update(_schema.example_config()['parameters']['oper'])
        return path

    def test_checkpoint_selection_uses_metadata_time(self):
        early=self.checkpoint('state_phys_t999.000.nc', 0.01)
        late=self.checkpoint('state_phys_t001.000.nc', 0.02)
        self.assertEqual(restart_compatibility._find_state_file(self.root), late)

    def test_missing_grid_state_or_wrong_shape_blocks_restart(self):
        path=self.checkpoint('state_phys_t000.010.nc', 0.01, shape=(16,16))
        source=restart_compatibility.load_hdf5_state(path,digest_limit=1000000)
        target=_schema.example_config()
        target['parameters']['init_fields']={'type':'from_file','from_file':{'path':path.name}}
        target['provenance']['restart']={'path':path.name,'sha256':source['provenance']['state_sha256'],'source_fluidsim':'0.9.0'}
        self.assertFalse(restart_compatibility.compare(source,target)['ok'])
        source['state']['dataset_metadata']['rot']['shape']=[32,32]
        self.assertTrue(restart_compatibility.compare(source,target)['ok'])
        del source['parameters']['oper']['nx']
        self.assertFalse(restart_compatibility.compare(source,target)['ok'])

    def test_restart_rejects_external_metadata_without_opening_target(self):
        path=self.root/'state_phys_t000.000.nc'
        with self.h5py.File(path,'w') as f:
            f['state_phys']=self.h5py.ExternalLink('absent.h5','/state_phys')
        with self.assertRaisesRegex(ToolError,'external links'):
            restart_compatibility.load_hdf5_state(path,digest_limit=0)

    def test_spectral_times_external_link_is_not_followed(self):
        path=self.root/'spectra2D.h5'
        with self.h5py.File(path,'w') as f:
            f['times']=self.h5py.ExternalLink('absent.h5','/times')
            f.create_dataset('spectrum2D_E', data=self.np.arange(8).reshape(1,8))
        result=budget_summary.summarize_spectral_file(path,max_datasets=10,max_values=4)
        self.assertTrue(result['hdf5_readable'])
        self.assertIsNone(result['time_range'])
        self.assertEqual(result['external_links_not_followed'],1)

    def test_virtual_spectral_storage_rejected(self):
        path=self.root/'spectra2D.h5'
        layout=self.h5py.VirtualLayout(shape=(1,8),dtype='f8')
        layout[:]=self.h5py.VirtualSource('absent.h5','data',shape=(1,8))
        with self.h5py.File(path,'w') as f: f.create_virtual_dataset('spectrum2D_E',layout)
        with self.assertRaisesRegex(ToolError,'virtual'):
            budget_summary.summarize_spectral_file(path,max_datasets=10,max_values=4)


class ReleasedApiRegressions(unittest.TestCase):
    def test_profiles_match_released_solver_defaults(self):
        try:
            import fluidsim
            import fluidfft
        except ImportError:
            self.skipTest('requires FluidSim FFT stack')
        for key, profile in PROFILES.items():
            with self.subTest(solver=key):
                cls=importlib.import_module(_schema.SOLVER_IMPORTS[key]).Simul
                p=cls.create_default_params()
                self.assertEqual(profile['initializations'], list(p.init_fields.available_types))
                self.assertEqual(profile['forcing'], list(p.forcing.available_types))
                self.assertEqual(profile['outputs'], list(p.output.periods_save._make_dict_tree()))
                self.assertEqual(profile['required_state'], list(cls.InfoSolver().classes.State.keys_phys_needed))

    def test_analytical_decay_output_restart_and_forcing(self):
        try:
            import fluidsim
            import fluidfft
        except ImportError:
            self.skipTest('requires FluidSim FFT stack')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            env={**os.environ, 'PYTHONDONTWRITEBYTECODE':'1', 'OMP_NUM_THREADS':'1', 'MPLBACKEND':'Agg'}
            fixture=Path(__file__).parent/'fixtures'/'analytical_smoke.py'
            result=subprocess.run([sys.executable,str(fixture),str(root),str(SKILL_ROOT/'scripts')],env=env,capture_output=True,text=True,timeout=45)
            self.assertEqual(result.returncode,0,result.stdout[-2000:]+result.stderr[-2000:])
            # Execute the generated, checksum-verified restart from another cwd.
            restarted=subprocess.run([sys.executable,str(root/'restart.py'),'--execute','--acknowledge-config-id','replace-with-study-config-id'],cwd=root.parent,env=env,capture_output=True,text=True,timeout=30)
            self.assertEqual(restarted.returncode,0,restarted.stdout[-2000:]+restarted.stderr[-2000:])
