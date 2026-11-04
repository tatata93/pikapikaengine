"""Create this Native milestone's public check and lesson links."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
source=(root/'reports/sphere-triangle-mesh-trajectory-lab-recipes/public.py').read_text(encoding='utf-8')
source=source.replace('sphere-triangle-mesh-trajectory-lab-public-','sphere-triangle-mesh-entry-public-')
source=source.replace('    assert len(paths)==len(set(paths))', '''    paths += ['core/include/pikapika/sphere_triangle_mesh_entry.hpp','core/src/sphere_triangle_mesh_entry.cpp','tests/sphere_triangle_mesh_entry_tests.cpp','tests/sphere_triangle_mesh_entry_fixture.hpp','scripts/verify-sphere-triangle-mesh-entry.py','tests/sphere_triangle_mesh_entry_reference_tests.py','docs/SPHERE_TRIANGLE_MESH_ENTRY.md','docs/SPHERE_TRIANGLE_MESH_ENTRY_PLAN.md','docs/learn/diagrams/sphere-triangle-mesh-entry.svg']
    assert len(paths)==len(set(paths))''')
target=root/'reports/sphere-triangle-mesh-entry-recipes/public.py';assert not target.exists();target.write_text(source,encoding='utf-8')
path=root/'docs/learn/index.html';text=path.read_text(encoding='utf-8')
old='定義pathの証明を運動方程式の真解・TOI・一般World CCDの完成とはしません。'
assert text.count(old)==1
new='定義pathの証明を運動方程式の真解・TOI・一般World CCDの完成とはしません。次のNative段は<a href="../../docs/SPHERE_TRIANGLE_MESH_ENTRY.md">安全prefixと負の点証拠からentry windowを囲む核</a>です。未知区間が狭いだけでは受理せず、共有SDKへの接続は別に検証します。'
path.write_text(text.replace(old,new),encoding='utf-8')
