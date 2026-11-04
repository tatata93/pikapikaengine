"""Publish a receipt only after independently captured public acceptance."""
from pathlib import Path
import json,re
root=Path(__file__).resolve().parents[2]
prefix='sphere-triangle-mesh-free-flight-guard'
proof=json.loads((root/f'reports/{prefix}-public-verification.json').read_text(encoding='utf-8'))
assert proof['status']=='PASS' and proof['commit']=='bd7c1f7f0828aa9dfb67678550c45794b26781d7'
resume='丸め自由伝播guard bd7c1f7を公開受入。Native114群/40CTest/631Node skip0、固定100＋別固定4、独立12self/50負例がWindows/Linuxで成功。GNU旧W1全report/World前後byte比較、既存SDK保存20例bit比較、新核のASan/UBSanとRelease/sanitized両cohort byte比較も成功。43公開ファイル1779473Bがfeature blobに一致。SDK86exports/62source-header/30TU、WASM719396B、Webbbeba69b26e28cdb。公開ゲーム2撃破/boostclip1/停止、51全照会完了3常駐/error0。警告40は既存36に旧Worldを別targetで再コンパイルした同一診断4件が加わったもの。次は[保持荷重と自由伝播guardの共有SDK接続](SPHERE_TRIANGLE_MESH_FLIGHT_SDK_PLAN.md)：両modeの全所有診断とcandidateを有界C ABIへ運び、Native/WASM全bitと独立数学参照を検証する。計画は未実装で、現在の新guardはNative-only。[検証記録](../reports/2026-11-04-sphere-triangle-mesh-free-flight-guard.md)。World進行/全pair順序/衝撃摩擦支持/流体損傷/専門モデル/IK制御/高精度撮像は未完。'
p=root/'docs/PLAN.md';text=p.read_text(encoding='utf-8');text,n=re.subn(r'^再開位置:.*$','再開位置: '+resume,text,count=1,flags=re.M);assert n==1
p.write_text(text.rstrip()+'\n\n公開受入追記: '+resume+'\n',encoding='utf-8',newline='\n')
p=root/'docs/SPHERE_TRIANGLE_MESH_FREE_FLIGHT_GUARD_PLAN.md';text=p.read_text(encoding='utf-8');old='Nativeローカル受入済み・公開検証待ち';assert old in text;p.write_text(text.replace(old,'Native公開受入済み（bd7c1f7）',1),encoding='utf-8',newline='\n')
p=root/'docs/RESEARCH.md';p.write_text(p.read_text(encoding='utf-8').rstrip()+'\n\n自由伝播guard公開受入: Engine run41796183673/job126460730559、Pages41796182644の全job/step成功。GNU旧World前後20例byte比較・SDK保存20例bit比較・独立Fraction100＋4・12self50負例・新核全依存ASan/UBSanと両fixture byte一致を確認。公開43原本/SDK/gameファイル1779473Bをfeature blobへ一致確認。実公開ゲーム51照会/2撃破/boost/停止と原著図の上下を保存。40警告のうち追加4は旧World同一診断の別target再コンパイルであり、無警告とは報告しない。次段は未実装の両mode SDK接続計画に全field所有・host/model境界・原子的拒否とメモリ実測を定義した。外部依存/料金/転載素材の追加なし。\n',encoding='utf-8',newline='\n')
p=root/f'reports/2026-11-04-{prefix}.md';text=p.read_text(encoding='utf-8');assert '公開CI/Pagesは確認待ち。' in text
text=text.replace('公開CI/Pagesは確認待ち。','コード `bd7c1f7` の公開CI/Pagesと配信を確認済み。',1)
text+='''
## 公開受入と次段

Engine [41796183673](https://github.com/tatata93/pikapikaengine/actions/runs/41796183673)（job126460730559）、Pages [41796182644](https://github.com/tatata93/pikapikaengine/actions/runs/41796182644)の全job/step成功。40CTest/631Node skip0に加え、GNUの変更前後W1全JSON比較、旧SDK保存20例のbit比較、新核114群/固定100＋補足4とFraction12self/50負例が成功した。新guardと依存する実dynamics/interval/mesh/held/Worldを別ASan/UBSan executableへ計装し、Release/sanitizedの両fixture JSON byte比較と独立参照が成功。新4翻訳単位のstrict/Werrorも成功した。Windows sanitizerやallocation fault注入の実施は意味しない。

警告は40件。前節の既存36件に、旧Worldを変更前probeおよび新guard sanitizerへ別途コンパイルした際の既存Query::result初期化診断4件が加わった。旧診断のCounterにこの4件を足したものと一致し、新しいguard翻訳単位の警告ではない。[公開機械監査](sphere-triangle-mesh-free-flight-guard-public-verification.json)と行番号付きjob excerptを保存した。excerptは全原ログのarchiveではない。

公開43ファイル計1779473Bが正確なfeature Git blobと一致。実公開ゲームはbuild bbeba69b26e28cdb/719396B WASMを使用し、2撃破・ブースト（clip1記録）・停止、51照会すべてchecked/validated/completed、3resident mesh/error0を確認した。停止時の速度表示は0で、観測していない速度を報告しない。図の上部と下端、ゲーム画面および表示JSONを[ブラウザ証拠](sphere-triangle-mesh-free-flight-guard-browser)へ保存した。新guardがゲームの接触処理へ適用された証拠とはしない。

次の最小受入は[両mode共有SDK計画](../docs/SPHERE_TRIANGLE_MESH_FLIGHT_SDK_PLAN.md)。現在の86exportsへ実装を追加する前に、元入力と膨張半径・全Work/partition・成功時candidate・host拒否とモデル結果の境界を固定し、Native/WASM全bitと独立参照を確認する。予定の6exports/92は未実装であり、現在の配布能力と区別する。

[ゲーム](https://tatata93.github.io/pikapikaengine/?v=bd7c1f7)・[原理解説](https://tatata93.github.io/pikapikaengine/docs/learn/index.html?v=bd7c1f7#accelerated)
'''
p.write_text(text,encoding='utf-8',newline='\n')
print('Public guard receipt and next bounded SDK milestone recorded.')
