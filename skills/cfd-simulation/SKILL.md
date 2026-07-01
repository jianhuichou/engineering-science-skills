---
name: cfd-simulation
description: >
  Computational fluid dynamics (CFD) workflows using OpenFOAM, SU2, or
  Python-based solvers. Covers mesh generation, boundary condition setup,
  solver configuration, convergence monitoring, and post-processing with
  PyVista/Matplotlib. Load this skill for internal/external flow, heat
  transfer CFD, aerodynamics, or HVAC analysis tasks.
license: Apache-2.0
category: mechanical-engineering
metadata:
  third_party:
    - kind: library
      name: OpenFOAM
      provider: The OpenFOAM Foundation
      license: GPL-3.0
      info_url: https://openfoam.org/
    - kind: library
      name: SU2
      provider: SU2 Foundation
      license: LGPL-2.1
      info_url: https://su2code.github.io/
---

# CFD Simulation

## Workflow overview

A CFD job has four stages regardless of solver: geometry/mesh, boundary
conditions and physics setup, solver execution, and post-processing.

```
CAD/geometry -> mesh generation -> case setup -> solve -> visualize/extract
   (.stl/.step)   (snappyHexMesh    (0/ constant/ system/  (PyVista / paraview)
                   blockMesh, gmsh)  or SU2 .cfg)
```

## OpenFOAM — structure of a case directory

```
case/
  0/          # initial and boundary condition fields (U, p, k, epsilon, ...)
  constant/   # mesh (polyMesh/) and physical properties (transportProperties, ...)
  system/     # controlDict, fvSchemes, fvSolution, snappyHexMeshDict, ...
```

### Minimal incompressible steady-state case (simpleFoam)

**`system/controlDict`:**
```
application     simpleFoam;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         500;       // iterations
deltaT          1;
writeControl    timeStep;
writeInterval   100;
```

**`0/U` (velocity field):**
```
dimensions      [0 1 -1 0 0 0 0];
internalField   uniform (0 0 0);
boundaryField {
    inlet  { type fixedValue; value uniform (10 0 0); }   // 10 m/s
    outlet { type zeroGradient; }
    walls  { type noSlip; }
}
```

**`0/p` (kinematic pressure):**
```
dimensions      [0 2 -2 0 0 0 0];
internalField   uniform 0;
boundaryField {
    inlet  { type zeroGradient; }
    outlet { type fixedValue; value uniform 0; }
    walls  { type zeroGradient; }
}
```

### Running and monitoring from Python

```python
import subprocess, pathlib, re
import pandas as pd

case = pathlib.Path("/tmp/cfd_case")

def run_openfoam(case_dir, solver="simpleFoam", np=4):
    """Run an OpenFOAM solver and return the residual log."""
    log = case_dir / "log.simpleFoam"
    cmd = ["mpirun", "-np", str(np), solver, "-parallel", "-case", str(case_dir)]
    if np == 1:
        cmd = [solver, "-case", str(case_dir)]
    with open(log, "w") as fh:
        subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT, check=True)
    return log

def parse_residuals(log_path):
    """Parse OpenFOAM residual log into a DataFrame."""
    pattern = re.compile(r"Time = (\d+).*?Ux.*?Initial residual = ([0-9.e+-]+)", re.DOTALL)
    times, res = [], []
    for m in pattern.finditer(log_path.read_text()):
        times.append(int(m.group(1))); res.append(float(m.group(2)))
    return pd.DataFrame({"iteration": times, "Ux_residual": res})
```

### Convergence criterion

Declare convergence when all residuals are below 1e-4 (steady) or 1e-5
(turbulence quantities) for at least 50 consecutive iterations, and when
force/flux monitors have stabilized within 0.1%.

## Post-processing with PyVista

```python
import pyvista as pv

# Read OpenFOAM case (requires PyVista + vtk)
reader = pv.OpenFOAMReader("/tmp/cfd_case/case.foam")
reader.set_active_time_value(reader.time_values[-1])   # last time step
mesh = reader.read()

# Extract internal mesh block
internal = mesh["internalMesh"]

# Velocity magnitude
import numpy as np
U = internal.point_data["U"]
Umag = np.linalg.norm(U, axis=1)
internal["Umag"] = Umag

# Plot
plotter = pv.Plotter(off_screen=True)
plotter.add_mesh(internal, scalars="Umag", cmap="viridis")
plotter.camera_position = "xy"
plotter.screenshot("velocity_field.png", window_size=[1200, 800])
```

## SU2 — compressible aerodynamics

SU2 is configured via a single `.cfg` file:

```python
su2_cfg = """
SOLVER= RANS
KIND_TURB_MODEL= SST
MACH_NUMBER= 0.3
AOA= 5.0
FREESTREAM_PRESSURE= 101325.0
FREESTREAM_TEMPERATURE= 288.15
REF_DIMENSIONALIZATION= DIMENSIONAL
MESH_FILENAME= airfoil.su2
MESH_FORMAT= SU2
CONV_RESIDUAL_MINVAL= -8
MAX_ITER= 500
OUTPUT_FILES= ( RESTART, SURFACE_CSV )
VOLUME_OUTPUT= ( DENSITY, VELOCITY, PRESSURE, TEMPERATURE, PRESSURE_COEFFICIENT )
"""

import pathlib, subprocess
cfg_path = pathlib.Path("/tmp/su2/airfoil.cfg")
cfg_path.write_text(su2_cfg)
subprocess.run(["SU2_CFD", str(cfg_path)], check=True, cwd="/tmp/su2")
```

Parse surface coefficient file:
```python
import pandas as pd
surf = pd.read_csv("/tmp/su2/surface_flow.csv")
CL = surf["Pressure_Coefficient"].mean()   # simplified; integrate properly
```

## Mesh generation with gmsh

```python
import gmsh

gmsh.initialize()
gmsh.model.add("channel")
# Simple 2-D rectangular channel
gmsh.model.geo.addPoint(0, 0, 0, lc=0.1, tag=1)
gmsh.model.geo.addPoint(5, 0, 0, lc=0.1, tag=2)
gmsh.model.geo.addPoint(5, 1, 0, lc=0.1, tag=3)
gmsh.model.geo.addPoint(0, 1, 0, lc=0.1, tag=4)
for i, (a, b) in enumerate([(1,2),(2,3),(3,4),(4,1)], start=1):
    gmsh.model.geo.addLine(a, b, tag=i)
loop = gmsh.model.geo.addCurveLoop([1, 2, 3, 4])
surf = gmsh.model.geo.addPlaneSurface([loop])
gmsh.model.geo.synchronize()
gmsh.model.mesh.generate(2)
gmsh.write("/tmp/channel.msh")
gmsh.finalize()
```

## Key dimensionless numbers

```python
def reynolds(rho, U, L, mu):
    """Re = rho*U*L/mu"""
    return rho * U * L / mu

def mach(U, a):
    """Ma = U/a  (a = speed of sound ~343 m/s at 20 C)"""
    return U / a

def nusselt_dittus_boelter(Re, Pr, heating=True):
    """Nu for turbulent pipe flow (Dittus-Boelter, Re > 10000)"""
    n = 0.4 if heating else 0.3
    return 0.023 * Re**0.8 * Pr**n
```

## Common errors and diagnostics

| Symptom | Cause / fix |
|---|---|
| Diverging residuals from iteration 1 | CFL too large or incompatible BCs; reduce relaxation factors in `fvSolution` |
| `checkMesh` reports non-orthogonality > 70 | Mesh quality issue; increase `nNonOrthogonalCorrectors` or refine mesh |
| Residuals plateau at > 1e-3 | Under-resolved near-wall region; check y+ and refine boundary layer mesh |
| SU2 outputs NaN | Supersonic inflow BCs incompatible with RANS; check Mach and AOA |
| PyVista reads empty mesh | Case not decomposed for parallel or wrong time directory name |
