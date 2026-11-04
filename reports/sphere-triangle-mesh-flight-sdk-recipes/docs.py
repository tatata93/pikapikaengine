"""Add original bounded-transport teaching material without changing a solver."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
p=root/'docs/learn/index.html';text=p.read_text(encoding='utf-8')
anchor='<h3>線分経路の途中を、区間ごとに証明する</h3>'
assert text.count(anchor)==1 and 'diagrams/sphere-triangle-mesh-flight-sdk.svg' not in text
addition='<h3>計算の診断を、欠けずに運ぶ</h3><p>保持荷重の曲線と、丸めた実伝播の非接触guardは別の照会です。入力の準備と確定した結果をmodeごとに分け、元半径・膨張半径・候補状態を別に保存します。計算の失敗や未照会のtailも、成功に置き換えず返します。</p><figure><img src="diagrams/sphere-triangle-mesh-flight-sdk.svg" width="1060" height="700" alt="保持荷重と自由伝播guardが別の入力stageと確定recordを持ち、全診断を64値以内で分割交換する。host拒否とモデル失敗を区別しWorldは更新しない。"><figcaption>原著の交換手順図。件数・速度・メモリ使用量の実測図ではありません。</figcaption></figure><p class="small"><a href="../SPHERE_TRIANGLE_MESH_FLIGHT_ABI.md">保持荷重と自由伝播guardの有界C ABI</a>で、全source・audit・被覆・失敗診断と成功時candidateを交換する仕組みを説明します。実装・公開の受入結果はガイドから参照してください。所有JavaScript API、手動UIとWorldの接触応答は後続です。</p>'
p.write_text(text.replace(anchor,addition+anchor),encoding='utf-8',newline='\n')
for path,paragraph in [
 ('docs/RESEARCH.md','保持荷重/自由伝播guardのraw SDK接続を実装中。既存の原著Native核・全診断を6つのmode付きC ABIで運び、純79/100/別4の完全入力からhost/model分類・全packet bit比較・実WASM由来の独立Fraction監査を分ける。新数学solverや外部文献の実読を主張せず、原本を保持して転送する実装の検証を追加する。'),
 ('docs/legal/REFERENCES.md','2026-11-04 flight SDK: 出典は本repo原著のheld-load/free-flight-guard/interval/mesh核と既存ABI。6入口の有界交換・原著SVG/解説/検証コードを追加。新外部資料の転載や、未読資料を調査済みとする記載はない。'),
 ('docs/legal/ASSETS.md','2026-11-04 `docs/learn/diagrams/sphere-triangle-mesh-flight-sdk.svg`: この開発で記述した原著SVG。独立mode/stage/record・有界packetとhost/model失敗の説明図。実測値やゲームassetではなく、外部画像/商用作品の素材は使用しない。本体license未選定。'),
 ('docs/legal/DEPENDENCIES.md','2026-11-04 flight SDK: 既存原著held-load/free-flight-guard核を固定Emscripten6.0.13の主SDKへ追加する。新外部package/solver/有料serviceは追加しない。6exports追加予定92、実source/artifact/runtime/member/通知とflagsは再build後に監査する。計測できないheap使用量/stack高水位をHEAP容量で代用しない。本体license未選定。')]:
 p=root/path;p.write_text(p.read_text(encoding='utf-8').rstrip()+'\n\n'+paragraph+'\n',encoding='utf-8',newline='\n')
print('Original flight SDK guide/diagram and research/rights records linked.')
