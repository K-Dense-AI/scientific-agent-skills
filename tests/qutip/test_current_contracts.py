"""Known-solution checks for the maintained QuTiP solver and extension contracts."""
from pathlib import Path
import sys

import numpy as np
import pytest

q = pytest.importorskip('qutip')
SKILL_ROOT = Path(__file__).resolve().parents[2] / 'skills' / 'qutip'
sys.path.insert(0, str(SKILL_ROOT / 'scripts'))
import solver_config_planner
import two_level_simulation


def test_coherence_rate_and_disabled_output_normalization():
    parser = two_level_simulation.build_parser()
    config = two_level_simulation.SimulationConfig.from_namespace(parser.parse_args([
        '--initial-state', 'plus', '--omega', '0', '--decay-rate', '0',
        '--dephasing-rate', '0.3', '--t-final', '2', '--time-points', '41',
    ]))
    report = two_level_simulation.run_simulation(config, q)
    np.testing.assert_allclose(report['expectations']['sigma_x'],
                               np.exp(-0.3 * report['times']), atol=2e-7)
    assert report['solver']['options_requested']['normalize_output'] is False


def test_stochastic_planner_options_execute_and_preserve_unmonitored_channels():
    parser = solver_config_planner.build_parser()
    for channels in (0, 1):
        plan = solver_config_planner.create_plan(parser.parse_args([
            '--model', 'diffusive', '--initial-state', 'ket',
            '--collapse-channels', str(channels), '--t-final', '0.2',
            '--time-points', '21', '--trajectories', '4', '--seed', '7',
        ]))
        config = plan['call_configuration'].copy()
        grid = config.pop('tlist')
        t = np.linspace(grid['start'], grid['stop'], grid['points'])
        config['e_ops'] = [q.sigmaz()]
        config['sc_ops'] = [0.1 * q.sigmaz()]
        if channels:
            config['c_ops'] = [np.sqrt(0.2) * q.sigmam()]
        solver = getattr(q, plan['recommended_solver'])
        result = solver(0.5*q.sigmaz(), q.basis(2, 0), t, **config)
        assert np.isfinite(result.average_expect[0]).all()
        if channels:
            assert plan['recommended_solver'] == 'smesolve'
            assert result.average_expect[0][-1] < 0.99
        else:
            np.testing.assert_allclose(result.average_expect[0], 1, atol=1e-6, rtol=0)


def test_retained_runs_and_seed_replay_keep_mean_representation_explicit():
    args = dict(H=0.5*q.sigmaz(), state=q.basis(2,0), tlist=[0,1,2],
                c_ops=[np.sqrt(0.4)*q.sigmam()], e_ops=[q.sigmaz()], ntraj=12)
    stored = q.mcsolve(**args, seeds=7, options={'keep_runs_results':True,
                      'store_states':True, 'progress_bar':''})
    replay = q.mcsolve(**args, seeds=stored.seeds, options={'progress_bar':''})
    assert np.asarray(stored.expect[0]).shape == (12,3)
    assert np.asarray(stored.average_expect[0]).shape == (3,)
    np.testing.assert_array_equal(stored.average_expect[0], replay.average_expect[0])
    np.testing.assert_allclose(np.mean(stored.runs_expect[0],axis=0),
                               stored.average_expect[0])
    assert stored.average_states[-1].isoper
    assert stored.runs_states[0][-1].isket


def test_pythonic_pulse_integrates_known_area_and_step_samples():
    def envelope(t, amplitude, center, width):
        return amplitude*np.exp(-0.5*((t-center)/width)**2)
    amp, width, center = 3., .1, 1.
    H = q.QobjEvo([[q.sigmax()/2, envelope]],
                 args={'amplitude':amp,'center':center,'width':width})
    r = q.sesolve(H,q.basis(2,0),[0,2],e_ops=[q.sigmaz()],
                  options={'max_step':width/5,'atol':1e-11,'rtol':1e-9})
    np.testing.assert_allclose(r.expect[0][-1],
                              np.cos(amp*width*np.sqrt(2*np.pi)),atol=2e-8)
    step = q.QobjEvo([[q.sigmax(),np.array([1.,2.,3.])]],
                    tlist=[0,1,2],order=0)
    assert step(.75)[0,1] == 1
    assert step(1.25)[0,1] == 2


def test_public_channel_conversions_preserve_amplitude_damping():
    p=.25
    K=[q.Qobj([[1,0],[0,np.sqrt(1-p)]]),q.Qobj([[0,np.sqrt(p)],[0,0]])]
    channel=q.kraus_to_super(K)
    choi=q.to_choi(channel)
    roundtrip=q.kraus_to_super(q.to_kraus(choi))
    assert channel.iscptp and choi.iscptp
    np.testing.assert_allclose(q.to_super(choi).full(),channel.full(),atol=1e-12)
    np.testing.assert_allclose(roundtrip.full(),channel.full(),atol=1e-12)
    final=q.vector_to_operator(channel*q.operator_to_vector(q.basis(2,1).proj()))
    np.testing.assert_allclose(final.diag(),[p,1-p],atol=1e-12)
    plus=(q.basis(2,0)+q.basis(2,1)).unit()
    assert q.fidelity(q.basis(2,0),plus) == pytest.approx(1/np.sqrt(2))


def test_stationary_correlation_and_spectrum_match_lorentzian():
    down,up,omega=.2,.05,1.
    damping=(down+up)/2
    occupation=up/(down+up)
    H=.5*omega*q.sigmaz()
    cops=[np.sqrt(down)*q.sigmam(),np.sqrt(up)*q.sigmap()]
    rho=q.steadystate(H,cops)
    assert rho[0,0] == pytest.approx(occupation)
    tau=np.linspace(0,4,41)
    corr=q.correlation_2op_1t(H,rho,tau,cops,q.sigmap(),q.sigmam(),
                            options={'atol':1e-11,'rtol':1e-9})
    np.testing.assert_allclose(corr,occupation*np.exp((1j*omega-damping)*tau),atol=2e-8)
    w=np.linspace(-2,2,51)
    spectrum=q.spectrum(H,w,cops,q.sigmap(),q.sigmam())
    np.testing.assert_allclose(spectrum,2*occupation*damping/(damping**2+(w-omega)**2),atol=1e-10)


def test_floquet_storage_and_heom_continuation_are_correct_representations():
    H=.5*q.sigmaz()
    basis=q.FloquetBasis(H,1.,options={'atol':1e-11,'rtol':1e-9})
    def spectrum(w):return .02*np.ones_like(w)
    r=q.fmmesolve(basis,q.basis(2,0),[0,.1],c_ops=[q.sigmax()],
                  spectra_cb=[spectrum],options={'store_floquet_states':True,
                                                'store_states':True,'progress_bar':''})
    assert len(r.floquet_states)==2
    np.testing.assert_allclose(r.states[-1].full(),
                              basis.from_floquet_basis(r.floquet_states[-1],.1).full(),atol=1e-10)
    from qutip.solver.heom import DrudeLorentzBath, HEOMSolver
    bath=DrudeLorentzBath(q.sigmaz(),lam=.01,gamma=1,T=1,Nk=1)
    solver=HEOMSolver(H,bath,max_depth=1,options={'store_ados':True,'progress_bar':''})
    a=solver.run(q.basis(2,0).proj(),[0,.1])
    assert hasattr(a.final_ado_state,'extract')
    b=solver.run(a.final_ado_state,[.1,.2])
    full=solver.run(q.basis(2,0).proj(),[0,.2])
    np.testing.assert_allclose(b.states[-1].full(),full.states[-1].full(),atol=1e-10)
    no_ados=HEOMSolver(H,bath,max_depth=1,options={'progress_bar':''}).run(q.basis(2,0).proj(),[0,.1])
    assert no_ados.final_ado_state is None


def test_nonmarkov_rate_has_physical_known_population():
    t=np.linspace(0,5,51)
    def rate(t):return .1*np.sin(t)
    # The exact time-local generator tests positivity independent of MC variance.
    dissipator=q.lindblad_dissipator(q.sigmam())
    r=q.mesolve(q.QobjEvo([[dissipator,rate]]),q.basis(2,0).proj(),t,
                e_ops=[q.basis(2,0).proj()],options={'atol':1e-11,'rtol':1e-9})
    known=np.exp(-.1*(1-np.cos(t)))
    np.testing.assert_allclose(r.expect[0],known,atol=2e-8)
    assert np.min(known)>=0 and np.max(known)<=1
    mc=q.nm_mcsolve(0*q.sigmaz(),q.basis(2,0),t,[(q.sigmam(),rate)],
                    e_ops=[q.basis(2,0).proj()],ntraj=100,seeds=71,
                    options={'progress_bar':''})
    assert abs(mc.average_expect[0][-1]-known[-1]) < .15


def test_qip_bell_state_and_qtrl_angular_control_replay():
    pytest.importorskip('qutip_qip')
    from qutip_qip.circuit import QubitCircuit
    circuit=QubitCircuit(2)
    circuit.add_gate('SNOT',targets=0)
    circuit.add_gate('CNOT',controls=0,targets=1)
    actual=circuit.run(q.tensor(q.basis(2,0),q.basis(2,0)))
    target=(q.tensor(q.basis(2,0),q.basis(2,0))+q.tensor(q.basis(2,1),q.basis(2,1))).unit()
    assert q.fidelity(actual,target)==pytest.approx(1.)
    pytest.importorskip('qutip_qtrl')
    from qutip_qtrl import pulseoptim
    opt=pulseoptim.optimize_pulse_unitary(0*q.sigmaz(),[q.sigmax()/2],q.qeye(2),
          -1j*q.sigmax(),num_tslots=4,evo_time=np.pi,amp_lbound=-2,amp_ubound=2,
          init_pulse_type='ZERO',pulse_offset=.7,max_iter=20,max_wall_time=5,
          fid_err_targ=1e-9)
    U=q.qeye(2)
    for amp, dt in zip(opt.final_amps[:,0],np.diff(opt.time)):
        U=(-1j*dt*amp*q.sigmax()/2).expm()*U
    np.testing.assert_allclose(U.full(),opt.evo_full_final.full(),atol=1e-10)
    assert abs(((-1j*q.sigmax()).dag()*U).tr()/2)>1-1e-7


def test_optional_jax_cpu_evolution_gradient_matches_analytic_rotation():
    jax=pytest.importorskip('jax')
    pytest.importorskip('qutip_jax')
    import jax.numpy as jnp
    import diffrax
    with jax.enable_x64(), jax.default_device(jax.devices('cpu')[0]):
        with q.CoreOptions(default_dtype='jax',numpy_backend=jnp):
            H=.5*q.sigmax()
            psi=q.basis(2,0)
            z=q.sigmaz()
            def response(omega):
                result=q.sesolve(omega*H,psi,[0,.2],e_ops=[z],options={
                    'method':'diffrax','normalize_output':False,
                    'stepsize_controller':diffrax.PIDController(atol=1e-10,rtol=1e-9),
                })
                return jnp.real(result.expect[0][-1])
            value=float(response(1.3))
            gradient=float(jax.grad(response)(1.3))
    assert value==pytest.approx(np.cos(.26),abs=2e-8)
    assert gradient==pytest.approx(-.2*np.sin(.26),abs=2e-8)


def test_result_audit_rejects_noninteger_or_unsupported_schema():
    import result_audit
    from _common import CliError
    for schema in (None,True,2,'1'):
        with pytest.raises(CliError,match='schema_version'):
            result_audit.audit_document({'schema_version':schema},tolerance=1e-6)


def test_large_coherent_qfunction_peak_and_current_cutoff_argument():
    state=q.coherent(260,13.)
    x=np.array([13.*np.sqrt(2)])
    y=np.array([0.])
    one=q.qfunc(state,x,y,cutoff=170)
    repeated=q.QFunc(x,y,cutoff=170)(state)
    np.testing.assert_allclose(one,1/(2*np.pi),atol=2e-6)
    np.testing.assert_allclose(one,repeated,atol=1e-12)


def test_floquet_planner_puts_tolerances_on_basis_propagator():
    parser=solver_config_planner.build_parser()
    plan=solver_config_planner.create_plan(parser.parse_args([
        '--model','periodic-closed','--period','1','--t-final','1',
    ]))
    config=plan['call_configuration']
    basis=q.FloquetBasis(.5*q.sigmax(),1.,options=config['floquet_basis_options'])
    result=q.fsesolve(basis,q.basis(2,0),[0,.5,1.],e_ops=[q.sigmaz()],
                     options=config['options'])
    np.testing.assert_allclose(result.expect[0],np.cos([0,.5,1]),atol=2e-7)
