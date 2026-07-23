# Sources and verification record

Research completed **2026-07-23** with `parallel-cli search` and
`parallel-cli extract`, then checked against an isolated installation of
`simpy==4.1.2`. Versioned documentation is preferred over the `latest` build,
which showed a 4.1.2 development revision during verification.

## Release, packaging, and source

- [SimPy on PyPI](https://pypi.org/project/simpy/) — **4.1.2**, released
  **2026-05-24**; `Requires-Python >=3.8`; classifiers list Python 3.8-3.14,
  CPython, and PyPy; MIT; no runtime dependencies. Verified 2026-07-23.
- [GitLab source project](https://gitlab.com/team-simpy/simpy/) — canonical
  repository, MIT license, tagged source, tests, and documentation. Accessed
  2026-07-23.
- [GitLab tag 4.1.2](https://gitlab.com/team-simpy/simpy/-/tags/4.1.2) —
  protected/verified tag, commit `f43816490c6f76f336ad6e457d3cab9f386894af`,
  dated **2026-05-24**.
- [Tagged CHANGES.rst](https://gitlab.com/team-simpy/simpy/-/blob/4.1.2/CHANGES.rst)
  — 4.1.2 entry dated **2026-05-23**: Python 3.13/3.14 support,
  modern-interpreter test/doc fixes, `ConditionValue` explicitly unhashable,
  lint/type cleanup.
- [Tagged pyproject.toml](https://gitlab.com/team-simpy/simpy/-/blob/4.1.2/pyproject.toml)
  — Python requirement/classifiers, no dependencies, setuptools build, pytest,
  mypy, and ruff configuration. Dated 2026-05-23; accessed 2026-07-23.
- [Tagged tox.ini](https://gitlab.com/team-simpy/simpy/-/blob/4.1.2/tox.ini) and
  [tagged tests](https://gitlab.com/team-simpy/simpy/-/tree/4.1.2/tests) —
  upstream test matrix and behavior tests. Accessed 2026-07-23.
- [Tagged `simpy/core.py`](https://gitlab.com/team-simpy/simpy/-/blob/4.1.2/src/simpy/core.py)
  — authoritative `Environment.run()`, `step()`, queue tuple, and
  `StopSimulation` implementation. Accessed 2026-07-23.

PyPI file hashes observed 2026-07-23:

- wheel `simpy-4.1.2-py3-none-any.whl` SHA-256
  `43071f84b6512c9b4fcb33ef057f240ccb1d1f3b263f9b4f9229d072e310b372`;
- sdist `simpy-4.1.2.tar.gz` SHA-256
  `76ef36b71e0436ba94e55febc001c78879e493a323f045bbcfbb0b216e9b1fbc`.

Use the pinned package command in `SKILL.md`; hashes are recorded for provenance,
not embedded into `uv pip install` syntax.

## Official SimPy 4.1.2 documentation

### Entry points

- [4.1.2 documentation contents](https://simpy.readthedocs.io/en/4.1.2/contents.html)
- [4.1.2 tutorial](https://simpy.readthedocs.io/en/4.1.2/simpy_intro/index.html)
- [4.1.2 topical guides](https://simpy.readthedocs.io/en/4.1.2/topical_guides/index.html)
- [4.1.2 examples](https://simpy.readthedocs.io/en/4.1.2/examples/index.html)
- [4.1.2 API reference](https://simpy.readthedocs.io/en/4.1.2/api_reference/index.html)
- [history/change log](https://simpy.readthedocs.io/en/4.1.2/about/history.html)
- [license](https://simpy.readthedocs.io/en/4.1.2/about/license.html)

All accessed 2026-07-23. The examples index covers condition events, interrupts,
Resource, PreemptiveResource, Container, Store, shared events, and process waiting.

### Core topical guides

- [SimPy basics](https://simpy.readthedocs.io/en/4.1.2/topical_guides/simpy_basics.html)
- [Environments](https://simpy.readthedocs.io/en/4.1.2/topical_guides/environments.html)
- [Events](https://simpy.readthedocs.io/en/4.1.2/topical_guides/events.html)
- [Process Interaction](https://simpy.readthedocs.io/en/4.1.2/topical_guides/process_interaction.html)
- [Shared Resources](https://simpy.readthedocs.io/en/4.1.2/topical_guides/resources.html)
- [Monitoring](https://simpy.readthedocs.io/en/4.1.2/topical_guides/monitoring.html)
- [Time and Scheduling](https://simpy.readthedocs.io/en/4.1.2/topical_guides/time_and_scheduling.html)
- [Real-time simulations](https://simpy.readthedocs.io/en/4.1.2/topical_guides/real-time-simulations.html)

All accessed 2026-07-23.

### API pages

- [`simpy.core`](https://simpy.readthedocs.io/en/4.1.2/api_reference/simpy.core.html)
  — `Environment`, `run`, `schedule`, `peek`, `step`, `EmptySchedule`.
- [`simpy.events`](https://simpy.readthedocs.io/en/4.1.2/api_reference/simpy.events.html)
  — `Event`, `Timeout`, `Process`, `Condition`, `AnyOf`, `AllOf`, priorities.
- [`simpy.exceptions`](https://simpy.readthedocs.io/en/4.1.2/api_reference/simpy.exceptions.html)
  — `Interrupt`.
- [`simpy.resources`](https://simpy.readthedocs.io/en/4.1.2/api_reference/simpy.resources.html)
  — Resource/Priority/Preemptive, Container, Store/Filter/Priority, base events.
- [`simpy.rt`](https://simpy.readthedocs.io/en/4.1.2/api_reference/simpy.rt.html)
  — `RealtimeEnvironment`.
- [`simpy.util`](https://simpy.readthedocs.io/en/4.1.2/api_reference/simpy.util.html)
  — helper processes.

All accessed 2026-07-23.

## Source-level semantic finding

The 4.1.2 Environments topical guide informally says Event-based `run()` returns
when the Event has been processed. The 4.1.2 API docstring says "triggered."
Tagged `core.py` is decisive:

- `run(until=event)` appends `StopSimulation.callback`;
- `step()` sets callbacks to `None`, executes them, catches `StopSimulation`,
  restores callbacks remaining after the stopping callback, and reschedules that
  Event at priority `-1`.

Therefore the target value can be returned while `target.processed` is still false,
until one more step processes the rescheduled empty-callback Event. This was
reproduced under the exact PyPI 4.1.2 wheel on Python 3.13 and is covered by
`tests/test_scripts.py`.

Numeric `run(until=time)` creates an urgent internal stop Event, so normal Events at
that exact time are excluded. This was verified from both tagged source and runtime
tests.

## Primary simulation-method sources

These sources describe simulation-study design and output analysis. They are not
SimPy API documentation.

- Averill M. Law, ["Statistical Analysis of Simulation Output Data"](https://informs-sim.org/wsc20papers/134.pdf),
  *Proceedings of the 2020 Winter Simulation Conference*, 2020. Defines
  terminating/nonterminating analyses; independent replications;
  replication/deletion; warm-up/run length; Student-t intervals; and warns against
  naive single-run IID intervals. Accessed 2026-07-23.
- Pierre L'Ecuyer, ["Random Number Generation with Multiple Streams for Sequential and Parallel Computing"](https://informs-sim.org/wsc15papers/003.pdf),
  *Proceedings of the 2015 Winter Simulation Conference*, 2015,
  DOI `10.1109/WSC.2015.7408151`. Covers streams/substreams, one stream per random
  source, replication separation, common random numbers, testing, and exact
  reproducibility. Accessed 2026-07-23.
- Robert G. Sargent, ["Verification and Validation of Simulation Models"](https://www.informs-sim.org/wsc10papers/016.pdf),
  *Proceedings of the 2010 Winter Simulation Conference*, 2010. Defines model
  verification, conceptual/data/operational validity, intended-purpose/domain
  framing, sensitivity analysis, and validation evidence. Accessed 2026-07-23.
- Stewart Robinson, ["Conceptual Modelling for Simulation Part I: Definition and Requirements"](https://doi.org/10.1057/palgrave.jors.2602368),
  *Journal of the Operational Research Society* 59, 278-290, 2008. Identifies
  validity, credibility, utility, feasibility, and simplest-adequate-model
  requirements. Publisher page accessed 2026-07-23.
- Lee W. Schruben, ["Detecting Initialization Bias in Simulation Output"](https://doi.org/10.1287/opre.30.3.569),
  *Operations Research* 30(3), 569-590, **June 1982**. Original initialization-bias
  testing method. Metadata/abstract verified via
  [IDEAS/RePEc](https://ideas.repec.org/a/inm/oropre/v30y1982i3p569-590.html)
  on 2026-07-23.
- Stewart Robinson, ["A Statistical Process Control Approach to Selecting a Warm-up Period for a Discrete-event Simulation"](https://ideas.repec.org/a/eee/ejores/v176y2007i1p332-346.html),
  *European Journal of Operational Research* 176(1), 332-346, **January 2007**.
  Accessed 2026-07-23.
- Kathryn Hoad, Stewart Robinson, Ruth Davies,
  ["Automated Selection of the Number of Replications for a Discrete-event Simulation"](https://doi.org/10.1057/jors.2009.121),
  *Journal of the Operational Research Society* 61(11), 1632-1644,
  **November 2010**. Replication-count/precision methodology; metadata verified
  2026-07-23.
- Thomas Monks et al.,
  ["Strengthening the Reporting of Empirical Simulation Studies: Introducing the STRESS Guidelines"](https://doi.org/10.1080/17477778.2018.1442155),
  *Journal of Simulation*, 2018/2019 publication record. Reporting checklists for
  objectives, logic, data, experimentation, implementation, and code access.
  [EQUATOR record](https://www.equator-network.org/reporting-guidelines/strengthening-the-reporting-of-empirical-simulation-studies-introducing-the-stress-guidelines/)
  last updated 2021-11-19; both accessed 2026-07-23.
- Averill M. Law and W. David Kelton,
  ["Confidence Intervals for Steady-State Simulations: I. A Survey of Fixed Sample Size Procedures"](https://doi.org/10.1287/opre.32.6.1221),
  *Operations Research* 32(6), 1221-1239, **December 1984**. Surveys replication,
  batch means, autoregressive, spectral, and regenerative fixed-run methods and
  cautions that adequate run length is model-dependent. Accessed 2026-07-23.

## Research queries used

Parallel searches/extractions covered:

- latest SimPy stable version, Python support, PyPI files, GitLab tags/changelog;
- Environment/Event/Process/Timeout/Condition and scheduling;
- all Resource, Container, and Store variants;
- interrupts, monitoring, stepping, real-time, examples, API, and testing config;
- independent replications, confidence intervals, warm-up/transient bias,
  random streams, conceptual modeling, V&V, sensitivity, and reproducibility.

No Parallel JSON artifacts were written into the repository.
