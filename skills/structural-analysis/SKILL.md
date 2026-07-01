---
name: structural-analysis
description: >
  Finite-element and structural analysis workflows for civil and mechanical
  structures. Covers model setup, load case definition, solver execution
  (OpenSees, PyNite, CalculiX), result extraction, safety factor evaluation,
  and reporting. Load this skill when a task involves FEM/FEA, beam/frame
  analysis, stress/deflection computation, or structural code checks.
license: Apache-2.0
category: civil-engineering
metadata:
  third_party:
    - kind: library
      name: OpenSees
      provider: UC Berkeley
      license: BSD-2-Clause
      info_url: https://opensees.berkeley.edu/
    - kind: library
      name: PyNite
      provider: Craig Baker
      license: MIT
      info_url: https://github.com/JWock82/PyNite
    - kind: library
      name: CalculiX
      provider: Guido Dhondt and Klaus Wittig
      license: GPL-2.0
      info_url: http://www.calculix.de/
---

# Structural Analysis

Structural analysis translates a geometry, material, loading, and support
description into internal forces, deformations, and code-check ratios. The
two principal tools available here are **PyNite** (pure-Python 3-D FEA for
beams, frames, and trusses — good for quick parametric studies) and
**CalculiX** (full finite-element solver with shell/solid elements and
non-linear capability, driven from `.inp` files). **OpenSees** is the choice
for non-linear seismic analysis.

## Choosing the right tool

| Task | Tool |
|---|---|
| Beam/frame analysis, quick parametric study | PyNite |
| Shell, solid, or contact elements; non-linear static/dynamic | CalculiX |
| Seismic pushover, fiber section, OpenSees Python API | openseespy |
| Symbolic/closed-form checks alongside numerical results | sympy + scipy |

## PyNite workflow

```python
from PyNite import FEModel3D

mdl = FEModel3D()

# Nodes (name, X, Y, Z)
mdl.add_node("A", 0, 0, 0)
mdl.add_node("B", 5, 0, 0)   # 5 m span

# Member (name, i_node, j_node, E, G, Iy, Iz, J, A)
E = 200e9   # Pa, steel
G = 80e9
mdl.add_member("M1", "A", "B", E, G, Iy=8.196e-5, Iz=2.14e-4, J=7e-7, A=9.59e-3)

# Supports
mdl.def_support("A", True, True, True, True, True, True)   # fixed
mdl.def_support("B", True, True, True, False, False, False) # pin

# Load combination and loading
mdl.add_load_combo("1.2D+1.6L", {"D": 1.2, "L": 1.6})
mdl.add_member_dist_load("M1", "Fy", -20e3, -20e3, case="D")  # N/m downward

mdl.analyze()

# Results
d_max = mdl.members["M1"].max_deflection("dy")
M_max = mdl.members["M1"].max_moment("Mz", combo="1.2D+1.6L")
print(f"Max deflection: {d_max*1000:.2f} mm")
print(f"Max moment:     {M_max/1e3:.1f} kN-m")
```

### Key result accessors

```python
m = mdl.members["M1"]
m.max_deflection("dy")            # peak transverse deflection (m)
m.max_shear("Fy", combo="...")    # peak shear (N)
m.max_moment("Mz", combo="...")   # peak bending moment (N-m)
m.max_axial()                      # peak axial force (N)
```

### Common errors

| Symptom | Cause / fix |
|---|---|
| `SingularMatrix` / solver failure | Mechanism in model — check every node has all 6 DOFs constrained or connected; add at least one support per direction |
| Unexpected zero moments | Wrong member orientation or `Iy`/`Iz` swapped — use `mdl.members["M1"].plot_moment_diagram()` to inspect |
| `KeyError` on combo name | Combo must be defined before it is referenced in result calls |

## CalculiX workflow

CalculiX jobs run as `.inp` text files. Drive them from Python by writing
the file, calling `ccx`, and parsing the `.frd` (binary result) or `.dat`
(text summary) output.

```python
import subprocess, pathlib

inp = """
*HEADING
Simple plate in tension
*NODE
1, 0.0, 0.0, 0.0
2, 1.0, 0.0, 0.0
3, 1.0, 1.0, 0.0
4, 0.0, 1.0, 0.0
*ELEMENT, TYPE=S4R, ELSET=PLATE
1, 1, 2, 3, 4
*MATERIAL, NAME=STEEL
*ELASTIC
210000., 0.3
*SOLID SECTION, ELSET=PLATE, MATERIAL=STEEL
0.01
*BOUNDARY
1, 1, 2
2, 2, 2
*STEP
*STATIC
*CLOAD
3, 1, 10000.
4, 1, 10000.
*NODE PRINT, NSET=NALL
U
*EL PRINT, ELSET=PLATE
S
*END STEP
"""

p = pathlib.Path("/tmp/plate")
p.mkdir(exist_ok=True)
(p / "plate.inp").write_text(inp)
result = subprocess.run(["ccx", "plate"], cwd=p, capture_output=True, text=True)
dat = (p / "plate.dat").read_text()
```

For field output (stress/strain/displacement over the mesh), use
`ccx2paraview` to convert `.frd` to `.vtu`, then read with PyVista:

```python
import pyvista as pv
mesh = pv.read("/tmp/plate/plate.vtu")
smax = mesh.point_data["S"][..., 0].max()   # S11 max principal stress
```

## OpenSees (seismic / non-linear)

```python
import openseespy.opensees as ops

ops.wipe()
ops.model("basic", "-ndm", 2, "-ndf", 3)

ops.node(1, 0.0, 0.0); ops.node(2, 0.0, 3.0)
ops.fix(1, 1, 1, 1)

E, A, I = 200e9, 9.59e-3, 2.14e-4
ops.geomTransf("Linear", 1)
ops.element("elasticBeamColumn", 1, 1, 2, A, E, I, 1)

ops.timeSeries("Constant", 1)
ops.pattern("Plain", 1, 1)
ops.load(2, 50e3, 0, 0)

ops.constraints("Plain"); ops.numberer("RCM")
ops.system("BandGeneral"); ops.algorithm("Linear")
ops.integrator("LoadControl", 1.0)
ops.analysis("Static"); ops.analyze(1)

disp = ops.nodeDisp(2, 1)
print(f"Lateral displacement: {disp*1000:.2f} mm")
```

## Safety factor and code check pattern

After extracting demand values compare them against capacity computed from
section properties and the governing standard:

```python
# Example: AISC 360 beam flexure check (simplified)
Mp = Fy * Zx          # plastic moment capacity (N-m), Fy in Pa, Zx in m^3
phi = 0.9             # AISC resistance factor
DCR = M_demand / (phi * Mp)
print(f"DCR = {DCR:.3f}  ({'PASS' if DCR <= 1.0 else 'FAIL'})")
```

Always retrieve section properties from a database or published table rather
than typing them from memory. `sectionproperties` (Python) can compute
arbitrary cross-sections:

```python
from sectionproperties.pre.library import rectangular_section
from sectionproperties.analysis import Section

geom = rectangular_section(d=200, b=100).create_mesh([5])
sec = Section(geom); sec.calculate_geometric_properties()
Ixx = sec.get_ixx_c()   # second moment of area (mm^4)
```

## Reporting outputs

Save key results as artifacts:

1. A summary table (pandas DataFrame to `.csv`) with member demands,
   capacities, and DCR for every member and load combination.
2. Deflection/moment diagrams as `.png`.
3. The input model file (`.inp` / `.tcl`) as a reproducibility artifact.

Structure files exported as `.stl` render in the 3-D viewer.

## Validation checklist

Before reporting results, verify:
- Reactions sum to applied loads (equilibrium check).
- Deflections are in the expected direction and order of magnitude
  (hand-estimate `delta = PL^3/48EI` for a simply-supported beam as a
  sanity bound).
- DCR values are dimensionally consistent (all forces in N, lengths in m,
  or consistently in kN and mm — never mixed).
- Load combination factors match the governing standard (ASCE 7, EN 1990,
  or project specification). State the standard and edition in every report.
