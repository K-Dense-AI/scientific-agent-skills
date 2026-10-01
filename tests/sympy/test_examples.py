"""Native mathematical regression checks for maintained SymPy workflows."""
from pathlib import Path
import importlib.util
import math

import pytest

s = pytest.importorskip('sympy')
SKILL_ROOT = Path(__file__).resolve().parents[2] / 'skills' / 'sympy'


def test_exact_inputs_and_precision():
    assert s.gamma(s.Rational(1, 2)) == s.sqrt(s.pi)
    assert s.Rational('0.1') * 10 == 1
    assert s.Rational(0.1) != s.Rational(1, 10)
    assert abs((s.sqrt(2).evalf(60)**2 - 2)) < s.Float('1e-58')


def test_assumptions_and_branch_sensitive_identities():
    x = s.Symbol('x')
    r = s.Symbol('r', real=True)
    p, q = s.symbols('p q', positive=True)
    assert x.is_positive is None
    assert s.sqrt(x**2) != x
    assert s.sqrt(r**2) == s.Abs(r)
    assert s.expand_log(s.log(p*q)) == s.log(p) + s.log(q)
    assert s.log(-1*-1) != s.log(-1) + s.log(-1)


def test_cancellation_retains_excluded_domain_separately():
    x = s.Symbol('x')
    original = (x**2 + 2*x + 1)/(x**2 + x)
    reduced = s.cancel(original)
    assert s.simplify(original - reduced) == 0
    assert original.subs(x, -1) is s.nan
    assert reduced.subs(x, -1) == 0
    assert s.limit(original, x, -1) == 0


def test_calculus_order_and_finite_differences():
    x, y = s.symbols('x y')
    assert s.integrate(x*y, (y, 0, x), (x, 0, 1)) == s.Rational(1, 8)
    f = s.Function('f')
    assert f(x).diff(x).as_finite_difference() == f(x+s.Rational(1, 2)) - f(x-s.Rational(1, 2))
    assert s.integrate(x*s.exp(-x**2), (x, 0, s.oo)) == s.Rational(1, 2)


def test_solver_domains_unknown_and_infinite_sets():
    x = s.Symbol('x', positive=True)
    assert s.solveset(x**2-1, x, domain=s.S.Reals) == s.FiniteSet(-1, 1)
    assert s.solveset(x**2+1, x, domain=s.S.Reals) is s.S.EmptySet
    z = s.Symbol('z')
    assert isinstance(s.solveset(s.cos(z)-z, z, domain=s.S.Reals), s.ConditionSet)
    roots = s.solveset(s.exp(z)-3, z, domain=s.S.Complexes)
    assert roots.contains(s.log(3)+2*s.pi*s.I) is s.S.true


def test_polynomial_roots_dictionary_may_be_incomplete():
    x = s.Symbol('x')
    p = s.Poly(x**5 - x - 1, x)
    assert s.roots(p) == {}
    exact_roots = p.all_roots()
    assert len(exact_roots) == p.degree()
    assert all(abs(p.as_expr().subs(x, r.evalf(40)).evalf(30)) < s.Float('1e-30') for r in exact_roots)


def test_nsolve_is_local_and_residual_is_checked():
    x = s.Symbol('x')
    expr = x**2 - 2
    positive = s.nsolve(expr, x, 1, prec=50)
    negative = s.nsolve(expr, x, -1, prec=50)
    assert positive > 0 > negative
    assert abs(expr.subs(x, positive)) < s.Float('1e-45')
    assert abs(expr.subs(x, negative)) < s.Float('1e-45')


def test_parametric_and_inconsistent_linear_systems():
    x, y, z = s.symbols('x y z')
    a, b = s.Matrix([[1, 2, 3]]), s.Matrix([6])
    sol = next(iter(s.linsolve((a, b), (x, y, z))))
    assert a*s.Matrix(sol) == b
    assert sol[1:] == (y, z)
    assert s.linsolve([x+y-1, x+y-2], (x, y)) is s.S.EmptySet


def test_ode_residual_and_initial_condition():
    x = s.Symbol('x')
    f = s.Function('f')
    ode = f(x).diff(x)-f(x)
    sol = s.dsolve(ode, f(x), ics={f(0): 1})
    assert s.checkodesol(ode, sol) == (True, 0)
    assert sol.rhs.subs(x, 0) == 1


def test_matrix_mutation_and_construction():
    m = s.Matrix([[1, 2], [3, 4]]).row_insert(1, s.Matrix([[5, 6]]))
    m = m.col_insert(1, s.Matrix([7, 8, 9]))
    assert m.row_del(0) is None
    assert m.col_del(1) is None
    assert m == s.Matrix([[5, 6], [3, 4]])


def test_condensed_complex_svd_uses_hermitian_transpose():
    m = s.Matrix([[1, s.I], [0, 0], [0, 0]])
    u, sigma, v = m.singular_value_decomposition()
    assert (u*sigma*v.H-m).applyfunc(s.simplify) == s.zeros(3, 2)
    assert (u*sigma*v.T-m).applyfunc(s.simplify) != s.zeros(3, 2)
    assert u.shape == (3, 1) and v.shape == (2, 1)


def test_condition_number_uses_singular_values():
    np = pytest.importorskip('numpy')
    m = s.Matrix([[1, 2], [3, 4]])
    assert float(m.condition_number()) == pytest.approx(np.linalg.cond(np.array(m).astype(float)))
    assert m.condition_number() > 1


def test_analytic_matrix_functions_differ_from_elementwise():
    m = s.Matrix([[0, 1], [-1, 0]])
    t = s.Symbol('t')
    sinm = m.analytic_func(s.sin(t), t)
    cosm = m.analytic_func(s.cos(t), t)
    assert (sinm*sinm + cosm*cosm - s.eye(2)).applyfunc(s.simplify) == s.zeros(2)
    assert sinm != m.applyfunc(s.sin)


def test_lu_permutation_and_multiple_rhs():
    a = s.Matrix([[0, 2], [3, 4]])
    l, u, swaps = a.LUdecomposition()
    assert a.permuteFwd(swaps) == l*u
    b = s.Matrix([[5, 7], [6, 8]])
    assert a*a.LUsolve(b) == b


def test_projection_is_hermitian_and_idempotent():
    a = s.Matrix([[1, 0], [0, s.I], [1, 1]])
    p = a*(a.H*a).inv()*a.H
    assert p*p == p and p.H == p and p*a == a


def test_discrete_probability_uses_symbolic_equality():
    from sympy.stats import Bernoulli, Binomial, P
    b = Bernoulli('B', s.Rational(1, 2))
    x = Binomial('X', 10, s.Rational(1, 2))
    assert P(s.Eq(b, 1)) == s.Rational(1, 2)
    assert P(s.Eq(x, 5)) == s.Rational(63, 256)
    assert P(x == 5) == 0


def test_independent_normal_probabilities():
    from sympy.stats import Normal, P, covariance
    x, y = Normal('X', 0, 1), Normal('Y', 0, 1)
    assert covariance(x, y) == 0
    assert P(x > 0)*P(y > 0) == s.Rational(1, 4)


def test_number_theory_group_and_powerset():
    from sympy.combinatorics import Permutation, PermutationGroup
    assert s.igcd(60, 48, 36) == 12
    assert s.mod_inverse(3, 7) == 5 and s.totient(10) == 4
    p = Permutation(0, 1, 2, size=4)
    assert p(3) == 3
    assert PermutationGroup(p).is_cyclic is True
    assert len(s.FiniteSet(1, 2, 3).powerset()) == 8


def test_lagrange_pendulum_equation():
    from sympy.physics.mechanics import dynamicsymbols, LagrangesMethod
    q = dynamicsymbols('q')
    m, g, l = s.symbols('m g l', positive=True)
    lagrangian = m*(l*q.diff())**2/2 - m*g*l*(1-s.cos(q))
    lm = LagrangesMethod(lagrangian, [q])
    lm.form_lagranges_equations()
    assert s.simplify(lm.rhs()[1] + g*s.sin(q)/l) == 0


def test_kane_oscillator_rhs_and_linearization():
    from sympy.physics.mechanics import dynamicsymbols, ReferenceFrame, Point, Particle, KanesMethod
    q, u = dynamicsymbols('q u')
    m, k = s.symbols('m k', positive=True)
    n = ReferenceFrame('N')
    origin = Point('O'); origin.set_vel(n, 0)
    p = origin.locatenew('P', q*n.x); p.set_vel(n, u*n.x)
    km = KanesMethod(n, q_ind=[q], u_ind=[u], kd_eqs=[u-q.diff()])
    km.kanes_equations([Particle('particle', p, m)], [(p, -k*q*n.x)])
    assert km.rhs() == s.Matrix([u, -k*q/m])
    a, b, inputs = km.linearize(A_and_B=True, op_point={q: 0, u: 0})
    assert a == s.Matrix([[0, 1], [-k/m, 0]])
    assert b.cols == 0 and inputs.rows == 0


def test_inertia_and_joint_axis_api():
    from sympy.physics.mechanics import RigidBody, inertia, Point, ReferenceFrame, PinJoint, PrismaticJoint
    n, p = ReferenceFrame('N'), Point('P')
    body = RigidBody('body', p, n, 2, (inertia(n, 1, 2, 3), p))
    assert body.central_inertia.to_matrix(n) == s.diag(1, 2, 3)
    fixed, rot, slide = RigidBody('fixed'), RigidBody('rot'), RigidBody('slide')
    pin = PinJoint('pin', fixed, rot, joint_axis=fixed.frame.z)
    slider = PrismaticJoint('slider', fixed, slide, joint_axis=fixed.frame.z)
    assert pin.joint_axis == fixed.frame.z == slider.joint_axis


def test_quantum_operator_application_and_bit_order():
    from sympy.physics.quantum import qapply
    from sympy.physics.quantum.sho1d import RaisingOp, SHOKet
    from sympy.physics.quantum.gate import X
    from sympy.physics.quantum.qubit import Qubit
    assert qapply(RaisingOp('a')*SHOKet(1)) == s.sqrt(2)*SHOKet(2)
    assert qapply(X(0)*Qubit('01')) == Qubit('00')


def test_unit_conversion_dimensional_checks_and_custom_scale():
    from sympy.physics.units import Quantity, convert_to, meter, second, newton, kilogram
    from sympy.physics.units.systems.si import SI
    from sympy.physics.units.util import check_dimensions
    q = Quantity('sympy_skill_test_length')
    q.set_global_relative_scale_factor(s.Rational(5, 2), meter)
    assert convert_to(q, meter) == s.Rational(5, 2)*meter
    assert convert_to(10*kilogram*5*meter/(2*second)**2, newton) == s.Rational(25, 2)*newton
    assert str(SI.get_dimensional_expr(meter/second)) == 'length/time'
    with pytest.raises(ValueError):
        check_dimensions(meter+second)


def test_beam_reactions_and_deflection():
    from sympy.physics.continuum_mechanics.beam import Beam
    e, inertia = s.symbols('E I', positive=True)
    b = Beam(10, e, inertia)
    r1, r2 = b.apply_support(0, 'pin'), b.apply_support(10, 'roller')
    b.apply_load(-1000, 5, -1)
    b.solve_for_reaction_loads(r1, r2)
    assert b.reaction_loads == {r1: 500, r2: 500}
    assert b.deflection().subs(b.variable, 0) == b.deflection().subs(b.variable, 10) == 0
    assert s.simplify(b.deflection().subs(b.variable, 5) + s.Rational(62500, 3)/(e*inertia)) == 0


def test_truss_and_cable_static_equilibrium():
    from sympy.physics.continuum_mechanics.truss import Truss
    from sympy.physics.continuum_mechanics.cable import Cable
    truss = Truss()
    truss.add_node(('A', 0, 0), ('B', 4, 0), ('C', 2, 3))
    truss.add_member(('AB', 'A', 'B'), ('BC', 'B', 'C'), ('AC', 'A', 'C'))
    truss.apply_support(('A', 'pinned'), ('B', 'roller'))
    truss.apply_load(('C', 1000, 270)); truss.solve()
    assert sum(v for k, v in truss.reaction_loads.items() if str(k).endswith('_y')) == 1000
    cable = Cable(('A', 0, 10), ('B', 10, 10))
    cable.apply_load(-1, ('W', 5, 5, 1000, 270)); cable.solve()
    assert set(cable.tension.values()) == {500*s.sqrt(2)}
    assert sum(v for k, v in cable.reaction_loads.items() if str(k).endswith('_x')) == 0
    assert sum(v for k, v in cable.reaction_loads.items() if str(k).endswith('_y')) == 1000


def test_control_rewrite_transfer_function_equivalence():
    from sympy.physics.control import StateSpace, TransferFunction
    z = s.Symbol('s')
    tf = TransferFunction(z+1, z*z+2*z+1, z)
    ss = tf.rewrite(StateSpace)
    restored = ss.rewrite(TransferFunction)[0][0]
    assert s.cancel(tf.to_expr()-restored.to_expr()) == 0


def test_muscle_pathway_activation_and_gamma_tensor():
    from sympy.physics.mechanics import Point, ReferenceFrame, LinearPathway, dynamicsymbols
    from sympy.physics.biomechanics import MusculotendonDeGroote2016, FirstOrderActivationDeGroote2016
    from sympy.physics.hep.gamma_matrices import GammaMatrix, LorentzIndex
    from sympy.tensor.tensor import tensor_indices
    from sympy.physics.matrices import mgamma
    n, a, b = ReferenceFrame('N'), Point('a'), Point('b')
    length = dynamicsymbols('length', positive=True)
    b.set_pos(a, length*n.x)
    model = MusculotendonDeGroote2016('muscle', LinearPathway(a, b), FirstOrderActivationDeGroote2016('act'))
    assert s.simplify(model.pathway.length-length) == 0
    assert model.x.rows == 1
    mu = tensor_indices('mu', LorentzIndex)
    assert GammaMatrix(mu).get_indices() == [mu]
    assert mgamma(0)**2 == s.eye(4) and mgamma(1)**2 == -s.eye(4)


def test_generated_python_is_importable_and_matches_symbolic(tmp_path):
    x = s.Symbol('x')
    expr = s.sin(x)**2
    module_path = tmp_path/'generated.py'
    module_path.write_text('import math\ndef f(x):\n    return '+s.pycode(expr)+'\n')
    spec = importlib.util.spec_from_file_location('generated_sympy_example', module_path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    assert module.f(0.3) == pytest.approx(float(expr.evalf(subs={x: 0.3})))


def test_lambdify_shapes_backends_and_common_subexpressions():
    np = pytest.importorskip('numpy')
    x, y = s.symbols('x y')
    f = s.lambdify(x, [x**2, x**3], 'numpy')
    outputs = f(np.array([1, 2]))
    assert isinstance(outputs, list) and len(outputs) == 2
    np.testing.assert_array_equal(outputs[1], [1, 8])
    expr = s.sin(x+y)**2 + s.cos(x+y)**2 + s.sin(x+y)
    replacements, reduced = s.cse(expr)
    restored = reduced[0]
    for symbol, value in reversed(replacements):
        restored = restored.xreplace({symbol: value})
    assert s.simplify(restored-expr) == 0


def test_latex_parser_strict_and_symbol_assumptions():
    pytest.importorskip('antlr4')
    from sympy.parsing.latex import parse_latex
    from sympy.parsing.sympy_parser import parse_expr
    x, y = s.symbols('x y')
    assert parse_latex(r'\frac{x^2}{y}', strict=True) == x**2/y
    with pytest.raises(Exception):
        parse_latex('x -', strict=True)
    xr = s.Symbol('x', real=True)
    assert parse_expr('x**2 + 1', local_dict={'x': xr}).free_symbols == {xr}
