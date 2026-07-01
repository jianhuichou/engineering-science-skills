# Science and Engineering Skills

This repository contains the prompt, skill, agent, and MCP server assets for a
Claude Science style scientific computing assistant extended for engineering
disciplines. The contents are mostly runtime-facing configuration and
documentation: skills teach the assistant how to perform domain workflows,
agents define specialized profiles, and MCP servers expose scientific and
engineering data and tools.

## Source

The base prompt and life-science skills in this repository are sourced from the
Claude Science product. The public product page is available for context:
https://claude.com/product/claude-science.

The engineering skill packages, specialized agent profiles, and engineering MCP
servers are extensions to that base.

## Repository Layout

| Path | Purpose |
| --- | --- |
| `SYSTEM_PROMPT.md` | Base system prompt and operating rules for the scientific computing agent. |
| `skills/` | Skill packages. Each skill is centered on a `SKILL.md` file, with optional helper code, references, requirements, and provider metadata. |
| `agents/` | Agent profile metadata and prompts for specialized roles such as onboarding, transcript review, bookmarking, and the general science agent. |
| `mcp-servers/` | Bundled MCP servers and widgets used by the agent for external scientific data and chemistry workflows. |

## Skill Catalog

The `skills/` directory includes workflows for several broad areas:

### Life sciences and biomedical
- Biomolecular modeling and design: `alphafold2`, `boltz`, `chai1`,
  `openfold3`, `esmfold2`, `fair-esm2`, `diffdock`, `proteinmpnn`,
  `ligandmpnn`, `solublempnn`, `evo2`, and `borzoi`.
- Scientific analysis and reporting: `literature-review`, `pdf-explore`,
  `figure-style`, `figure-composer`, `paper-narrative`, and
  `indication-dossier`.
- Single-cell and omics workflows: `scgpt` and `scvi-tools`.
- Runtime and environment operations: `remote-compute-modal`,
  `remote-compute-ssh`, `compute-env-setup`, `managed-model-endpoints`, and
  `using-model-endpoint`.
- Product and customization workflows: `customize`, `skill-creator`,
  `product-self-knowledge`, and `self-awareness`.

### Civil engineering
- `structural-analysis` — FEM/FEA workflows (PyNite, CalculiX, OpenSees),
  load case setup, result extraction, and safety factor reporting.
- `geotechnical-analysis` — soil classification (USCS), bearing capacity
  (Terzaghi/Meyerhof), slope stability (Bishop simplified), and settlement.
- `building-codes` — ASCE 7 load combinations and seismic hazard (USGS API),
  AISC 360, ACI 318, IBC, and Eurocode cross-referencing.
- `hydraulics-hydrology` — Manning's equation, rational method, NOAA Atlas 14
  rainfall data, USGS streamflow retrieval, and HEC-RAS result parsing.

### Mechanical engineering
- `cfd-simulation` — OpenFOAM case setup, SU2 compressible flow, convergence
  monitoring, and post-processing with PyVista.
- `heat-transfer` — conduction resistance networks, convection correlations,
  fin efficiency, heat exchanger design (LMTD, NTU-effectiveness), and
  transient 2-D finite differences.
- `mechanical-design` — tolerance stack-up, fatigue life (S-N, Miner's rule,
  modified Goodman), shaft design, gear loads, and DFM rules.
- `vibration-dynamics` — modal analysis (eigenvalue), FFT spectral analysis,
  STFT spectrogram, response spectrum, and rotating machine fault frequencies.

### Electrical engineering
- `circuit-analysis` — symbolic analysis (lcapy), SPICE simulation (PySpice),
  MNA, filter design, op-amp circuits, and two-port parameters.
- `signal-processing` — filtering, Welch PSD, STFT, window functions,
  resampling, SNR/THD estimation, and peak detection.
- `power-systems` — pandapower load flow, short-circuit (IEC 60909 style),
  OPF, PyPSA multi-period planning, and protection coordination.
- `electromagnetics` — transmission line analysis, S-parameters (scikit-rf),
  antenna fundamentals, impedance matching, and MEEP FDTD.
- `embedded-systems` — register map parsing, bit-field manipulation,
  UART/SPI/I2C decoding, interrupt latency, RTOS schedulability, and
  linker map analysis.

### Physical and engineering science
- `materials-characterization` — XRD simulation and peak fitting (pymatgen),
  Scherrer crystallite size, SEM grain analysis (scikit-image), EDS elemental
  identification, and Materials Project data retrieval.
- `thermodynamics-phase` — CoolProp fluid properties, Rankine cycle analysis,
  VLE calculations (thermo), psychrometrics, and NIST WebBook retrieval.
- `experimental-design` — full factorial, fractional factorial, central
  composite, and Latin hypercube sampling (pyDOE2); GUM uncertainty
  propagation; linear calibration; one-way ANOVA.
- `units-dimensional-analysis` — Pint unit-safe calculations, dimensionless
  number library (Re, Nu, Pr, Gr, Ra, Ma, Fr, St, We, Bi, Fo), and
  Buckingham Pi theorem.

Most skills start with YAML front matter:

```yaml
---
name: example-skill
description: When and why this skill should be loaded.
license: Apache-2.0
---
```

The body of `SKILL.md` should give the operational procedure, expected inputs,
failure modes, validation steps, and any tool-specific constraints needed for
reliable execution.

## Agents

Agent profiles live under `agents/<name>/metadata.yaml`.

- `operon` is the general-purpose scientific computing agent covering both
  life sciences and engineering disciplines.
- `structural-engineer` is a focused agent for civil/structural analysis,
  geotechnical, building codes, and hydraulics tasks.
- `ee-analyst` is a focused agent for electrical engineering: circuits,
  signal processing, power systems, electromagnetics, and embedded systems.
- `mech-designer` is a focused agent for mechanical/thermal-fluid tasks:
  CFD, heat transfer, mechanical design, vibration, thermodynamics, and
  materials characterization.
- `onboarding` supports first-run user onboarding.
- `reviewer` audits another agent transcript for unsupported claims,
  fabrication, or plan deviation.
- `bookmarker` selects transcript spans worth preserving as navigation
  breadcrumbs.

These files are configuration assets, not standalone applications. Keep prompt
changes tightly scoped and preserve any eval or benchmark notes near the prompt
they justify.

## MCP Servers

The `mcp-servers/` directory contains bundled MCP integrations:

- `bio-tools` vendors multiple Python packages for biological and biomedical
  data retrieval. `run_server.py` launches a named stdio server from
  `mcp-servers/bio-tools/lib/`.
- `ketcher-chemistry` contains a chemistry MCP server and widget assets for
  structure editing and chemistry workflows.
- `engineering-data-tools` provides engineering data retrieval tools:
  USGS seismic hazard parameters (ASCE 7), USGS streamflow gauges (NWIS),
  NIST WebBook thermophysical properties, Materials Project crystal structure
  data, and NOAA Atlas 14 precipitation frequency data.
- `spice-tools` wraps ngspice/PySpice for SPICE netlist simulation and
  netlist parsing. Returns node voltages and analysis output as JSON.
- `pandapower-tools` wraps pandapower for load flow analysis (Newton-Raphson),
  short-circuit fault calculations, and IEEE test network access.

### Engineering data tools — required environment variables

| Tool | Variable | Source |
|---|---|---|
| `get_materials_project_properties` | `MP_API_KEY` | https://materialsproject.org/api |
| `get_nist_fluid_properties` | none | Public NIST WebBook |
| `get_seismic_hazard` | none | Public USGS earthquake.usgs.gov |
| `get_usgs_streamflow` | none | Public USGS waterservices.usgs.gov |

The MCP code is runtime infrastructure. When changing it, prefer narrow edits
and verify both the server entry point and the shape of returned tool data.

## Working With This Repo

Useful inspection commands:

```bash
# List all skills
find skills -maxdepth 2 -name SKILL.md | sort

# List agent profiles
find agents -maxdepth 2 -name metadata.yaml | sort

# Show launchable bio-tools MCP servers
find mcp-servers/bio-tools/lib -maxdepth 2 -name server.py \
  | sed 's#^mcp-servers/bio-tools/lib/##; s#/server.py$##' \
  | sort
```

Before editing a skill or prompt:

1. Read the relevant `SKILL.md` or `metadata.yaml` completely.
2. Preserve existing safety, artifact, provenance, and validation rules unless
   the change explicitly updates them.
3. Keep examples executable and aligned with the current runtime surface.
4. Add or update references next to the skill when a workflow depends on
   external documentation or non-obvious operational knowledge.

## Maintenance Notes

- Use ASCII in new files unless the surrounding file already requires a wider
  character set.
- Avoid broad rewrites of prompts or generated MCP bundles without a concrete
  regression target.
- Treat bundled third-party services, model weights, and APIs as dependencies:
  document licenses, terms, privacy implications, and data movement in the
  relevant skill metadata when applicable.
- If a skill ships helper code such as `kernel.py`, keep the markdown
  instructions and helper APIs in sync.
