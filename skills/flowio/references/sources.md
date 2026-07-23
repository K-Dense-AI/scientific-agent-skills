# Authoritative Sources

This skill was refreshed on **2026-07-23** against the sources below. Examples
target the current stable package release at that date: **FlowIO 1.4.0**,
published **2025-05-09**.

When upstream behavior and this skill differ, prefer the tagged upstream source
and official API documentation, then update this skill and increment its
version.

## Package and Release

- [FlowIO on PyPI](https://pypi.org/project/FlowIO/) — stable version, release
  date, supported Python classifiers, dependency metadata, and project links.
- [FlowIO 1.4.0 release notes](https://github.com/whitews/FlowIO/releases/tag/1.4.0)
  — Python 3.13 support, `as_array()`, constructor rename, convenience
  attributes, NumPy dependency, public `fcs_keywords`, `Path` support, and
  writer/timestep changes.
- [All FlowIO releases](https://github.com/whitews/FlowIO/releases) — migration
  and bug-fix history.
- [FlowIO 1.4.0 tagged source](https://github.com/whitews/FlowIO/tree/1.4.0) —
  immutable implementation baseline used to verify edge behavior.
- [FlowIO 1.4.0 package metadata](https://github.com/whitews/FlowIO/blob/1.4.0/pyproject.toml)
  — supported Python versions and NumPy dependency.

## Official Documentation and User Guide

- [FlowIO documentation](https://flowio.readthedocs.io/en/latest/) — official
  entry point and installation overview.
- [FlowIO tutorial](https://flowio.readthedocs.io/en/latest/notebooks/flowio_tutorial.html)
  — official 1.4.0 user guide covering FCS segments, metadata, event values,
  export, keyword lists, multiple datasets, creation, and exceptions.
- [FlowIO API](https://flowio.readthedocs.io/en/latest/api.html) — generated
  signatures and public API reference.
- [FlowData 1.4.0 source](https://github.com/whitews/FlowIO/blob/1.4.0/src/flowio/flowdata.py)
  — metadata normalization, offset behavior, event parsing, preprocessing, and
  `write_fcs()`.
- [`create_fcs` 1.4.0 source](https://github.com/whitews/FlowIO/blob/1.4.0/src/flowio/create_fcs.py)
  — writer signature, validation, metadata rules, output representation, and
  float precision.
- [`read_multiple_data_sets` 1.4.0 source](https://github.com/whitews/FlowIO/blob/1.4.0/src/flowio/utils.py)
  — relative `$NEXTDATA` traversal and invalid-offset handling.
- [FlowIO exceptions 1.4.0 source](https://github.com/whitews/FlowIO/blob/1.4.0/src/flowio/exceptions.py)
  — warning and exception hierarchy.

## Flow Cytometry Standard

- Spidlen J, et al. [Data File Standard for Flow Cytometry, version FCS
  3.1](https://pubmed.ncbi.nlm.nih.gov/19937951/). *Cytometry Part A*.
  2010;77A(1):97-100.
  [doi:10.1002/cyto.a.20825](https://doi.org/10.1002/cyto.a.20825)
- Bray C, Spidlen J, Brinkman RR. [FCS 3.1 Implementation
  Guidance](https://pubmed.ncbi.nlm.nih.gov/22278913/). *Cytometry Part A*.
  2012;81(6):523-526.
  [doi:10.1002/cyto.a.22018](https://doi.org/10.1002/cyto.a.22018)
- [Free full text of the FCS 3.1 implementation
  guidance](https://pmc.ncbi.nlm.nih.gov/articles/PMC3676281/) — spillover,
  display, and compatibility guidance.

FlowIO reads FCS 2.0/3.0/3.1 and writes FCS 3.1. The standard publications are
needed when byte offsets, keywords, spillover metadata, or representation
details affect scientific interpretation.

## Higher-Level Analysis Boundary

- [FlowKit project](https://github.com/whitews/FlowKit) — related package for
  compensation, transformations, gating, GatingML, and FlowJo workspace
  support.
- [FlowKit documentation](https://flowkit.readthedocs.io/en/latest/) — use when
  a task moves beyond low-level FCS I/O.

## Verification Notes

During this refresh:

- PyPI, the latest GitHub release endpoint, and official documentation all
  identified 1.4.0 as the stable release.
- Runtime signatures were checked in an isolated `flowio==1.4.0` environment.
- Read/write behavior was round-tripped with a generated FCS 3.1 file.
- Runtime edge tests covered null-channel storage, literal `$` removal from
  TEXT values, caller-owned handle closure, and PnG/`timestep` loss during
  `write_fcs()`.
- The tagged implementation was used where generated API prose omitted details,
  especially metadata normalization and writer behavior.
- No FlowIO-specific Context7 documentation entry was available; official
  Read the Docs, tagged source, PyPI, and GitHub releases were used instead.
- Big-endian writer portability remains unverified. The 1.4.0 writer declares
  little-endian output while using Python's native-endian `array('f')` bytes;
  validate exports on big-endian hardware rather than assuming portability.
