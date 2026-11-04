"""Prepare documentation links and this milestone's public verification recipe."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
path=root/'docs/learn/index.html'
text=path.read_text(encoding='utf-8')
old='JavaScript所有APIは次段です。'
new='<a href="../../docs/SPHERE_TRIANGLE_MESH_TRAJECTORY_JS.md">JavaScript所有API</a>は全source・audit・leaf・失敗診断をcopyし、<a href="../../reports/sphere-triangle-mesh-trajectory-js-browser/index.html">固定入力の実WASM検証ページ</a>で全DTOを確認できます。手動trajectory編集UIは次段です。'
assert text.count(old)==1
text=text.replace(old,new)
text=text.replace('共有SDK・手動trajectory UI・ゲーム接触には未接続','共有SDKへ接続し、手動trajectory UI・ゲーム接触は後続')
path.write_text(text,encoding='utf-8')
source=(root/'reports/sphere-triangle-mesh-trajectory-abi-recipes/public.py').read_text(encoding='utf-8')
source=source.replace('sphere-triangle-mesh-trajectory-abi-public-','sphere-triangle-mesh-trajectory-js-public-')
source=source.replace('    build_html =', '''    paths += ['engine/sphere-triangle-mesh-trajectory.mjs','tests/sphere_triangle_mesh_trajectory_sdk.test.mjs','scripts/verify-sphere-triangle-mesh-trajectory-sdk.mjs','docs/SPHERE_TRIANGLE_MESH_TRAJECTORY_JS.md','docs/learn/diagrams/sphere-triangle-mesh-trajectory-owned.svg','reports/sphere-triangle-mesh-trajectory-js-browser/index.html']
    assert len(paths)==len(set(paths))
    build_html =''')
target=root/'reports/sphere-triangle-mesh-trajectory-js-recipes/public.py'
assert not target.exists()
target.write_text(source,encoding='utf-8')
