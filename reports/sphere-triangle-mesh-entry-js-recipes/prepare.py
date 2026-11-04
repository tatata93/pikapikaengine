"""Prepare original docs and an exact-source public byte recipe."""
from pathlib import Path
from hashlib import sha256
root=Path(__file__).resolve().parents[2]
p=root/'docs/learn/index.html';s=p.read_text(encoding='utf-8');assert 'SPHERE_TRIANGLE_MESH_ENTRY_JS.md' not in s
at=s.index('../../docs/SPHERE_TRIANGLE_MESH_ENTRY_ABI.md');end=s.index('</a>',at)+4
s=s[:end]+'・<a href="../../docs/SPHERE_TRIANGLE_MESH_ENTRY_JS.md">entry窓の所有JavaScript API（検証中）</a>'+s[end:]
p.write_text(s,encoding='utf-8',newline='\n')
svg=(root/'docs/learn/diagrams/sphere-triangle-mesh-entry-owned.svg').read_bytes()
entries={
 'docs/RESEARCH.md':'2026-11-04 entry-windowの所有JavaScript decoderを実装・検証中。既存86-export raw C ABIの全fieldと元入力をcopyし、metadataと所有を検査する。JSで幾何やsqrtを代替せず、実WASMモデルDTOのbit一致と出自付きmixed65 Fraction/90負例を別受入にする。Native/C ABI/SDK artifacts/7通知/gameは保持し、新外部資料実読/solver/依存/有料service/本体license選定なし。',
 'docs/legal/DEPENDENCIES.md':'2026-11-04 entry所有JS: 独自moduleと既存simulation runtimeの最小method/importだけを追加する予定。固定Emscripten6.0.13の86exports61source-header/WASM719410B/glue58933B、runtime91/7通知を変更せず、bit不変を受入で監査する。新package/solver/素材/課金なし。本体license未選定。',
 'docs/legal/REFERENCES.md':'2026-11-04 entry所有decoderと全DTO独立照合を追加中。旧原著trajectory wrapperの所有方式を参照し、Nativeの全field/−0と初期証拠/partition/tailを維持する。metadata整合検査と数学的包含の独立Fractionを区別する。新外部コード/文献図本文の転載なし。',
 'docs/legal/ASSETS.md':f'2026-11-04 原著entry所有図 docs/learn/diagrams/sphere-triangle-mesh-entry-owned.svg: {len(svg)}B SHA256 {sha256(svg).hexdigest()}。全6capability先行確認、一度captureした入力、所有DTOと全診断/−0、shared scratchと旧snapshotの分離を独自SVGで説明。容量数字は性能実測値ではなく図は数学包含の証明でもない。外部画像/font/model/文献図の流用なし、実ブラウザ目視は別記録。'
}
for p,s in entries.items():
    with (root/p).open('a',encoding='utf-8',newline='\n') as f:f.write('\n'+s+'\n')
public=(root/'reports/sphere-triangle-mesh-entry-abi-recipes/public.py').read_text(encoding='utf-8').replace('sphere-triangle-mesh-entry-abi-public','sphere-triangle-mesh-entry-js-public')
needle='    assert len(paths)==len(set(paths))';assert public.count(needle)==1
extra=['engine/sphere-triangle-mesh-entry.mjs','tests/sphere_triangle_mesh_entry_sdk.test.mjs','scripts/verify-sphere-triangle-mesh-entry-sdk.mjs','docs/SPHERE_TRIANGLE_MESH_ENTRY_JS.md','docs/SPHERE_TRIANGLE_MESH_ENTRY_JS_PLAN.md','docs/learn/diagrams/sphere-triangle-mesh-entry-owned.svg','reports/sphere-triangle-mesh-entry-js-browser/index.html']
# JS_PLAN already belongs to the previous81 list.
extra.remove('docs/SPHERE_TRIANGLE_MESH_ENTRY_JS_PLAN.md')
public=public.replace(needle,'    paths += '+repr(extra)+'\n'+needle)
target=root/'reports/sphere-triangle-mesh-entry-js-recipes/public.py';assert not target.exists();target.write_text(public,encoding='utf-8',newline='\n')
