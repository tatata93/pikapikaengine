"""Prepare documentation linkage and an exact-source public byte recipe."""
from hashlib import sha256
from pathlib import Path
root=Path(__file__).resolve().parents[2]
p=root/'docs/learn/index.html';s=p.read_text(encoding='utf-8')
assert 'SPHERE_TRIANGLE_MESH_ENTRY_ABI.md' not in s
start=s.index('../../docs/SPHERE_TRIANGLE_MESH_ENTRY.md');end=s.index('</a>',start)+4
s=s[:end]+'・<a href="../../docs/SPHERE_TRIANGLE_MESH_ENTRY_ABI.md">entry窓の有界交換（実装・検証中）</a>'+s[end:]
p.write_text(s,encoding='utf-8',newline='\n')
svg=(root/'docs/learn/diagrams/sphere-triangle-mesh-entry-exchange.svg').read_bytes()
records={
 'docs/RESEARCH.md':'2026-11-04 entry-windowの独立stage/C ABIを実装・検証中。既受入Native核と全診断を保持し、24入力・最大64F64内の全packet・host拒否原子性を設計した。交換expected encoderとFraction数学参照を別に受け入れる。新外部資料実読/solver/依存/素材/有料serviceなし。本体license未選定。公開GNU/Pagesと再生成SDKのruntime/通知監査は実行後に確定する。',
 'docs/legal/DEPENDENCIES.md':'2026-11-04 entry C ABI接続: 元の自作Native核を固定Emscripten6.0.13で共有SDKへ追加予定。新外部package/solverなし。新86exports/61 source-headerと配布bytes/runtime部品差分/7通知hash/memoryは再生成後の実測監査で確定する。旧80exportsの受入を新値へ流用しない。本体license未選定。',
 'docs/legal/REFERENCES.md':'2026-11-04 entry C ABIの原著packet mapと独立encoder/厳密bit照合を追加中。Nativeの距離・連続性証拠は既存実装/独立Fraction参照を継承し、新外部文献本文や図/コードを転載しない。metadata encoderを新しい数学solverや実機械軌道の証明と呼ばない。APIメモリ検査/純粋核メモリ検査/配布監査は別記録。',
 'docs/legal/ASSETS.md':f'2026-11-04 原著entry交換図 docs/learn/diagrams/sphere-triangle-mesh-entry-exchange.svg: {len(svg)}B SHA256 {sha256(svg).hexdigest()}。専用stage/候補record/有界getter、全initial/partition/tail診断と失敗原子性、独立expected/Native/WASM照合を独自SVGで説明する概念図。数字は設計容量で性能の測定ではない。外部画像/font/model/文献図の転載なし。実ブラウザ配置目視は別に記録する。'
}
for p,s in records.items():
    with (root/p).open('a',encoding='utf-8',newline='\n') as out:out.write('\n'+s+'\n')
source=(root/'reports/sphere-triangle-mesh-entry-recipes/public.py').read_text(encoding='utf-8').replace('sphere-triangle-mesh-entry-public','sphere-triangle-mesh-entry-abi-public')
needle="    assert len(paths)==len(set(paths))"
assert source.count(needle)==1
extra=['scripts/verify-sphere-triangle-mesh-entry-native-sdk.py','scripts/verify-sphere-triangle-mesh-entry-wasm-wire.mjs','tests/sphere_triangle_mesh_entry_sdk_tests.cpp','tools/sphere_triangle_mesh_entry_sdk_probe.cpp','docs/SPHERE_TRIANGLE_MESH_ENTRY_ABI.md','docs/SPHERE_TRIANGLE_MESH_ENTRY_SDK_PLAN.md','docs/learn/diagrams/sphere-triangle-mesh-entry-exchange.svg']
source=source.replace(needle,'    paths += '+repr(extra)+'\n'+needle)
target=root/'reports/sphere-triangle-mesh-entry-abi-recipes/public.py';assert not target.exists()
target.write_text(source,encoding='utf-8',newline='\n')
