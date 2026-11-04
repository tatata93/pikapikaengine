"""Insert original explanation without replacing existing lesson content."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
p=ROOT/'docs/learn/index.html'
raw=p.read_bytes();text=raw.decode('utf8')
needle='実WorldのBの由来と外部sqrt/compilerへの接続は、後続の統合条件です。</p>'
assert text.count(needle)==1 and 'id="world-flight-guard"' not in text
addition='<figure id="world-flight-guard"><img src="diagrams/world-static-mesh-flight-guard.svg" width="1120" height="800" alt="所有した全原本から必要な組を検査し、誤差と丸めと予算を監査する。全組が成功した場合だけ全物体の候補を返し、元Worldは進めない。"><figcaption>原著の設計概念図。実測軌道・性能・ゲーム接触応答を示す図ではありません。</figcaption></figure><p><a href="../WORLD_STATIC_MESH_FLIGHT_GUARD.md">全Worldの非接触候補を調べるNative照会</a>を実装・検証中です。各物体の誤差Bを実伝播から結び、全mesh・平面・球の必要な組を調べます。全時間の証拠、未照会の末尾、計算枠と保持枠を区別し、全組が成功した場合だけ全物体の候補を返します。実機の命令とビルド設定の監査も別に必要です。現在の公開機能の受入とは区別し、Worldの時間進行・衝突応答や新ブラウザ数値APIの完成には含めません。</p>'
text=text.replace(needle,needle+addition)
assert text.replace(addition,'').encode('utf8')==raw
p.write_bytes(text.encode('utf8'))
for path,paragraph in {
 'docs/RESEARCH.md':'2026-11-05 World全組flight guardを実装・検証中。actual core.cppのx64平方根をSSE2へ固定し、source固有strict設定・構成identity・実object/linked callerと実compile commandの外部監査を分ける。Microsoft x64 intrinsic一覧、Intel SDM Vol2BのSQRTSD節、Intel FP Reference Sheet v2.13の両頁、GCC13のC++ excess precision節を実読した。一次資料の範囲は reports/world-static-mesh-flight-guard-primary-sources.json。仕様の実読・構成identityを実機監査成功の代用にしない。原著SVGと教材を追加、新外部実装/画像/font/有料serviceやlicense選択なし。旧W1/W2/SDKの有限回帰を実行し、新World guardの数学・命令・全体受入は別に確定する。',
 'docs/legal/REFERENCES.md':'2026-11-05 World全組flight guard：Microsoft x64 intrinsic一覧のSSE2分類、Intel SDM Vol2B（253667-060US）のSQRTSD節（PDF index639–640）、Intel FP Reference Sheet v2.13の両頁（Sqrt、MXCSR、IEEE丸め）、GCC13 changesのC++ excess precision節を実読。完全URLと実読範囲は reports/world-static-mesh-flight-guard-primary-sources.json。本文/図/table/codeの転載なし。仕様・要求flag・runtimeの構成identityと、actual object/linked call path/compile commandの監査は別証拠。任意stdlib/全CPUや全NaNpayloadの保証へ拡張しない。',
 'docs/legal/ASSETS.md':'2026-11-05 docs/learn/diagrams/world-static-mesh-flight-guard.svg：本repoで原著制作した1120×800のvector概念図。所有原本・全必要pair・誤差/丸め・予約・全候補を説明する。実測軌道/性能/接触応答の図ではなく、外部画像/font/商用作品素材の流用なし。教材追加文とガイドも原著、既存sample素材保持、本体license未選定。'
}.items():
 q=ROOT/path;before=q.read_bytes();nl=b'\r\n' if b'\r\n' in before else b'\n'
 assert paragraph.encode('utf8') not in before
 q.write_bytes(before+nl+nl+paragraph.encode('utf8')+nl)
q=ROOT/'docs/WORLD_STATIC_MESH_FLIGHT_NATIVE_CONTRACT.md';raw=q.read_bytes();nl=b'\r\n' if b'\r\n' in raw else b'\n'
note='追記（2026-11-05）：以下は実装前に固定した契約案の履歴。現在は新Native核・型・source固有strict設定・実機監査ツール・有限試験を実装して検証中で、公開受入前である。下記の「未実装」は契約策定時の状態を記録する。現在の説明は [実装ガイド](WORLD_STATIC_MESH_FLIGHT_GUARD.md)、実行原本は reports/world-static-mesh-flight-guard-checks/ と binding-development/ を参照。'.encode('utf8')
assert note not in raw
first,rest=raw.split(nl,1);q.write_bytes(first+nl+nl+note+nl+rest)
print('Original lesson insertion and research/legal history appended; acceptance remains pending.')
