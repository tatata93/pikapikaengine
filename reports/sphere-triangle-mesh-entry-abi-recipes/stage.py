"""Stage only this reviewed milestone, excluding a still-developing aggregator."""
from pathlib import Path
import subprocess
root=Path(__file__).resolve().parents[2]
files=['.github/workflows/verify.yml','CMakeLists.txt','core/include/pikapika/simulation_api.h','core/src/simulation_api.cpp','scripts/build-simulation.mjs','scripts/verify-sphere-triangle-mesh-entry-native-sdk.py','scripts/verify-sphere-triangle-mesh-entry-wasm-wire.mjs','tests/sphere_triangle_mesh_entry_sdk_tests.cpp','tools/sphere_triangle_mesh_entry_sdk_probe.cpp','assets/pikapika-simulation.wasm','assets/pikapika-simulation.mjs','assets/pikapika-simulation.build.json','docs/PLAN.md','docs/RESEARCH.md','docs/SPHERE_TRIANGLE_MESH_ENTRY_ABI.md','docs/SPHERE_TRIANGLE_MESH_ENTRY_SDK_PLAN.md','docs/SPHERE_TRIANGLE_MESH_ENTRY_JS_PLAN.md','docs/learn/index.html','docs/learn/buoyancy.html','docs/legal/ASSETS.md','docs/legal/DEPENDENCIES.md','docs/legal/REFERENCES.md','docs/learn/diagrams/sphere-triangle-mesh-entry-exchange.svg','index.html','reports/2026-11-04-sphere-triangle-mesh-entry-abi.md']
files += [p.relative_to(root).as_posix() for p in (root/'tools').glob('*.html')]
for path in (root/'reports').glob('sphere-triangle-mesh-entry-abi*'):
    files.extend([path.relative_to(root).as_posix()] if path.is_file() else [p.relative_to(root).as_posix() for p in path.rglob('*') if p.is_file()])
files=sorted(set(files)-{'reports/sphere-triangle-mesh-entry-abi-recipes/public-summary.py'})
assert all((root/p).is_file() for p in files)
subprocess.run(['git','add','--',*files],cwd=root,check=True)
print('Staged reviewed paths:',len(files))
