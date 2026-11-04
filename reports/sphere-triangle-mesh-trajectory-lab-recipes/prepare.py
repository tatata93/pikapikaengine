"""Add authored lesson links, leaving generated import maps to the web builder."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
path=root/'docs/learn/index.html'
text=path.read_text(encoding='utf-8')
old='手動trajectory編集UIは次段です。'
new='<a href="../../tools/sphere-triangle-mesh-trajectory-lab.html">線分・面・予算を編集する実WASMラボ</a>では、非接触の証明葉・点貫通witness・未認証と全評価の診断を閲覧し、完全JSONを保存できます。'
assert text.count(old)==1
text=text.replace(old,new).replace('共有SDKへ接続し、手動trajectory UI・ゲーム接触は後続','共有SDKと手動trajectory UIへ接続し、ゲーム接触は後続')
path.write_text(text,encoding='utf-8')
source=(root/'reports/sphere-triangle-mesh-trajectory-js-recipes/public.py').read_text(encoding='utf-8')
source=source.replace('sphere-triangle-mesh-trajectory-js-public-','sphere-triangle-mesh-trajectory-lab-public-')
source=source.replace('    assert len(paths)==len(set(paths))', '''    paths += ['tools/sphere-triangle-mesh-trajectory-lab.html','tools/sphere-triangle-mesh-trajectory-lab.mjs','tests/sphere-triangle-mesh-trajectory-lab.test.mjs','docs/SPHERE_TRIANGLE_MESH_TRAJECTORY_LAB.md','docs/SPHERE_TRIANGLE_MESH_TRAJECTORY_LAB_PLAN.md','docs/learn/diagrams/sphere-triangle-mesh-trajectory-lab.svg','scripts/build-web.mjs']
    assert len(paths)==len(set(paths))''')
target=root/'reports/sphere-triangle-mesh-trajectory-lab-recipes/public.py';assert not target.exists()
target.write_text(source,encoding='utf-8')
