"""Tiny serial integration fixture; paths supplied by the isolated test process."""
import os
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
os.environ['FLUIDSIM_PATH'] = str(root/'runs')
os.environ['MPLBACKEND'] = 'Agg'
import numpy as np
from fluidsim.solvers.ns2d.solver import Simul
from fluidsim import load_sim_for_plot, load_state_phys_file, load_for_restart

scripts = Path(sys.argv[2])
sys.path.insert(0, str(scripts))
from _schema import example_config, normalized_copy
from budget_summary import summarize_scalar_file
from restart_compatibility import load_hdf5_state, compare
from simulation_dry_run import render_script

p = Simul.create_default_params()
p.oper.nx = p.oper.ny = 16
p.oper.Lx = p.oper.Ly = 2*np.pi
p.oper.type_fft = 'fft2d.with_pyfftw'
p.nu_2 = 0.01
p.time_stepping.USE_CFL = False
p.time_stepping.deltat0 = p.time_stepping.deltat_max = 0.001
p.time_stepping.t_end = 0.004
p.time_stepping.max_elapsed = '00:01:00'
p.init_fields.type = 'in_script'
p.output.sub_directory = 'analytical'
p.output.ONLINE_PLOT_OK = False
for name in p.output.periods_save._key_attribs:
    setattr(p.output.periods_save, name, 0.)
for name in ('phys_fields','spatial_means','spectra','spect_energy_budg'):
    setattr(p.output.periods_save, name, 0.001)
sim = Simul(p)
rot = np.sin(sim.oper.X)*np.sin(sim.oper.Y)
sim.state.init_statespect_from(rot_fft=sim.oper.fft(rot))
sim.state.statephys_from_statespect()
sim.time_stepping.start()
expected = rot*np.exp(-2*p.nu_2*sim.time_stepping.t)
np.testing.assert_allclose(sim.state.state_phys.get_var('rot'), expected, atol=1e-12)
run = Path(sim.output.path_run)
loaded = load_state_phys_file(run, hide_stdout=True)
np.testing.assert_allclose(loaded.state.state_phys.get_var('rot'), expected, atol=1e-12)
analysis = load_sim_for_plot(run, hide_stdout=True)
analysis.output.spatial_means.plot()
analysis.output.spectra.plot1d(tmin=0, tmax=0.004, coef_compensate=0)
analysis.output.phys_fields.plot(time=0.004)
analysis.output.spect_energy_budg.plot(tmin=0, tmax=0.004)
summary = summarize_scalar_file(run/'spatial_means.txt', max_records=100)
native = analysis.output.spatial_means.load()
for key in ('E', 'Z', 'epsK_tot', 'epsZ_tot'):
    assert abs(summary['metrics'][key]['mean'] - np.mean(native[key])) < 1e-12
state = run/'state_phys_t0.004.nc'
metadata = load_hdf5_state(state, digest_limit=10**7)
config = example_config()
config['parameters']['oper'].update(nx=16, ny=16)
relative = state.relative_to(root).as_posix()
config['parameters']['init_fields'] = {'type':'from_file', 'from_file': {'path': relative}}
config['parameters']['output']['HAS_TO_SAVE'] = False
config['parameters']['time_stepping'].update(USE_CFL=False, deltat0=0.001, deltat_max=0.001, t_end=0.006)
config['parameters']['nu_2'] = 0.01
config['provenance']['restart'] = {'path':relative, 'sha256':metadata['provenance']['state_sha256'], 'source_fluidsim':'0.9.0'}
assert compare(metadata, normalized_copy(config))['ok']
(root/'restart.py').write_text(render_script(config))
params, cls = load_for_restart(run)
params.output.HAS_TO_SAVE = False
params.time_stepping.t_end = 0.006
restarted = cls(params)
restarted.time_stepping.start()
np.testing.assert_allclose(restarted.state.state_phys.get_var('rot'), rot*np.exp(-2*p.nu_2*restarted.time_stepping.t), atol=1e-12)

# Verify the released time-correlated forcing state is stored and restorable.
p = Simul.create_default_params()
p.oper.nx = p.oper.ny = 16
p.oper.type_fft = 'fft2d.with_pyfftw'
p.time_stepping.USE_CFL = False
p.time_stepping.deltat0 = p.time_stepping.deltat_max = 0.001
p.time_stepping.t_end = 0.002
p.time_stepping.max_elapsed = '00:01:00'
p.init_fields.type = 'noise'
p.init_fields.noise.velo_max = 0.01
p.forcing.enable = True
p.forcing.type = 'tcrandom'
p.forcing.nkmin_forcing = 1
p.forcing.nkmax_forcing = 2
p.output.ONLINE_PLOT_OK = False
p.output.sub_directory = 'forced'
for name in p.output.periods_save._key_attribs:
    setattr(p.output.periods_save, name, 0.)
p.output.periods_save.phys_fields = 0.001
np.random.seed(123)
forced = Simul(p)
forced.time_stepping.start()
forced_state = Path(forced.output.path_run)/'state_phys_t0.002.nc'
assert load_hdf5_state(forced_state, digest_limit=10**7)['state']['forcing_state_complete']
restored = load_state_phys_file(forced.output.path_run, hide_stdout=True)
np.testing.assert_allclose(restored.forcing.forcing_maker.forcing0, forced.forcing.forcing_maker.forcing0)
np.testing.assert_allclose(restored.forcing.forcing_maker.forcing1, forced.forcing.forcing_maker.forcing1)
print('[OK] Analytical decay, output, restart, plots and forcing state')
