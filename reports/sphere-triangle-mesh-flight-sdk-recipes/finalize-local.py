"""Write a measured local receipt; public acceptance remains a separate gate."""
from pathlib import Path
import json,re
root=Path(__file__).resolve().parents[2];prefix='sphere-triangle-mesh-flight-sdk'
proof=json.loads((root/f'reports/{prefix}-local-verification.json').read_text(encoding='utf-8'))
assert proof['status']=='PASS'
actual=json.loads((root/f'reports/{prefix}-checks/run-20261104-final-002/wasm-independent/report.json').read_text())
assert (actual['fixtureCount'],actual['accepted'],actual['hostRejected'],actual['numericBits'],actual['negativeZeroBits'])==(183,173,10,415506,5738)
resume='保持荷重/丸め自由伝播guardのraw C ABIをローカル受入。mode別stage/recordと全21kind/6入口を追加し、92exports/67source-header/32TUへ正式SDK再build。WASM800982B/glue61661B/runtime91/7通知、Web26d4da108a67b9d9/51modules25entries。Native200ABI群/41CTest/631Node skip0成功。固定183入力=held74+guard95+補足4の173実モデル/10host拒否、全415506packet数値bits5738負零/decoded272814bits5424負零、Node全415689bits5738負零と独立Fraction/16改ざん拒否が成功。主元入力のhost拒否をNative結果で補填しない。333原本/25生成HTML保全、旧20W1全Native byte/SDK4520bits24負零と旧entry所有照合も成功。実ローカルゲーム2撃破/boostclip1/158kmh/停止・22照会全完了3常駐/error0。HEAP容量64MiB保持は観測したがused heap/stack高水位/実growth/fault注入は未計測。公開GNU/ASan-UBSan/Pages/配信は未確認。[ガイド](SPHERE_TRIANGLE_MESH_FLIGHT_ABI.md)・[記録](../reports/2026-11-04-sphere-triangle-mesh-flight-sdk.md)。次は[所有JS API](SPHERE_TRIANGLE_MESH_FLIGHT_JS_PLAN.md)。World進行/接触応答/流体損傷/専門モデル/IK制御/高精度撮像は未完。'
p=root/'docs/PLAN.md';text=p.read_text(encoding='utf-8');text,n=re.subn(r'^再開位置:.*$','再開位置: '+resume,text,count=1,flags=re.M);assert n==1;p.write_text(text.rstrip()+'\n\nraw flight SDKローカル受入追記: '+resume+'\n',encoding='utf-8',newline='\n')
p=root/'docs/SPHERE_TRIANGLE_MESH_FLIGHT_ABI.md';text=p.read_text(encoding='utf-8');old='実装・検証中。受入結果は検証記録で確定する。';assert old in text;p.write_text(text.replace(old,'ローカル受入済み、公開検証待ち。[実行記録](../reports/2026-11-04-sphere-triangle-mesh-flight-sdk.md)を参照。',1),encoding='utf-8',newline='\n')
p=root/'docs/SPHERE_TRIANGLE_MESH_FLIGHT_SDK_PLAN.md';text=p.read_text(encoding='utf-8');old='**未実装の次段計画**。';assert old in text;p.write_text(text.replace(old,'**raw C ABI/WASM交換はローカル受入済み、公開検証待ち**。[ガイド](SPHERE_TRIANGLE_MESH_FLIGHT_ABI.md)を参照。以下は元の設計と未実装のJS/計測項目を含む。',1),encoding='utf-8',newline='\n')
p=root/'docs/SPHERE_TRIANGLE_MESH_FLIGHT_JS_PLAN.md';text=p.read_text(encoding='utf-8');text=text.replace('raw C ABIのローカル統合は進行中で、まだ正式な全wire/独立参照/公開受入完了とはしない。','raw C ABIのローカル全wire/独立参照は成功し、公開受入は確認待ち。本JS計画は未実装である。',1);p.write_text(text,encoding='utf-8',newline='\n')
for path,paragraph in [('docs/RESEARCH.md','raw flight SDKローカル受入: 新92exports/67source-header/32TUを正式再buildし、173実モデルと10host拒否の出自を分離。全wire/decoded数学診断・原入力fingerprint・16改ざんと-O拒否を確認した。HEAP64MiB容量と12915view再取得の観測を、allocator使用量・stack高水位・実growthの測定と取り違えない。初回synthetic参照のhelper名誤りと、prebuilt baseline実行中の未使用APIheader編集を原記録に残す。公開GNU/メモリ検査は別受入。'),('docs/legal/DEPENDENCIES.md','raw flight SDK正式ローカル配布監査: 92exports/67source-header/32翻訳単位、WASM800982B/glue61661B。Emscripten6.0.13固定、runtime91memberと既存7通知は変更前とraw一致。新package/外部solver/有料serviceなし、本体license未選定。')]:
 p=root/path;p.write_text(p.read_text(encoding='utf-8').rstrip()+'\n\n'+paragraph+'\n',encoding='utf-8',newline='\n')
report='''# 保持荷重と丸め自由伝播guardのraw共有SDK — ローカル受入

2026-11-04。別modeの保持荷重と丸め自由伝播guardを6つの有界C ABIへ接続し、正式WASMへ追加した。Native200ABI検証群・41CTest・631Node（skip0）と独立参照が成功。公開CI/Pagesは確認待ち。ゲームやWorldの接触応答へ新queryを適用する段階ではない。

## 実際の交換と独立検証

固定79保持荷重＋100guard＋別補足4の完全入力を183行として送った。実際のモデル結果はheld74/guard95/補足4の173行、host拒否は各5/5/0の10行。拒否された行にNative数学結果を埋めて全WASM検証と数えない。Native交換の415506数値bits/5738負零、復号後DTOの272814数値bits/5424負零を比較。Nodeはmode metadata183を含め415689数値bits/5738負零を比較した。10397record、全21kind・source・nested・endpoint・candidate・lastMesh全row/候補を確認。可変messageだけは明示的にwireから除外する。

実WASMから復号した173モデルだけをFraction参照へ渡し、原F/m・二次曲線・全closed被覆・Work・独立RN/ties-even/B・実candidateを再確認した。独立完全入力fingerprintは全183 `4149030bf7278b5a91db1f2739c55491c82f57fc733254ee384153867f19ca54`、実受理173は `684f0262a9ee5c00dcc6f6559d9fcf28be66ef4e6b3e3acf5ff34dde174d1beb`。原reportの各mathematics.fixtures=0はper-fixture verifierが更新しないaggregate初期値で、実監査件数74/95/4は別に集計した。16コピー改ざん拒否とPython-O拒否、Node15操作controlを保存した。synthetic codec6群は実wireとは別の自己試験である。

256audit/128葉・区画/127frontier/64source・保守ID/64lastMesh row・448候補の末尾まで読み、範囲外getterの出力保持も確認。これら独立上限を同時の最悪メモリ達成と数えない。Native追加群は同/別mode・旧entry・World/時計・global reset・static/整数負零・全finite/reserved・不正body capture・成功candidate only・実unsupported FP環境を確認した。実unsupported環境はNativeの実験でありWASMへ移した観測ではない。

## 互換性・正式配布物・実ブラウザ

333旧原本をraw保全し、25生成HTMLはimportmap/build query/CRLFだけ正規化して保持した。旧API本文は新header include/同TU private実装includeとresetの追加loopだけを除けば元と同byte。旧86入口は保持し、新6入口を追加して92。67 source/header hashes・32TUを固定Emscripten6.0.13で安定ソースから再build。WASM800982B SHA `a7db41c64d2f9112ec5ee033371c391dddcb42ad23dcef713347c129a4ed015d`、glue61661B SHA `d4bedfdc9dcc1a60ee816e34c43afbe51623835ca5af65b0e6f4f5937484de55`。runtime91memberと7通知は元のまま。ライセンスは未選定、新外部依存/課金なし。

旧20Native W1の全report/World JSONは変更前後byte一致、既存SDK保存20例4520数値bits24負零も一致。旧entry所有APIの全105056モデル数値bits3239負零、原入力4728bits108負零・90負例もfresh成功。純held79/guard100/補足4の再生成JSONは以前の固定全入力/出力とbyte一致した。

実ローカルゲームはWeb26d4da108a67b9d9/800982B WASMで出撃・2撃破・boostclip1・158km/h表示・停止を確認。22照会すべてchecked/validated/completed、3resident mesh/error0。これは既存ゲーム/SDKの互換性で、新guardのゲーム接触使用を意味しない。原著SVGを全体表示して文字/配置を確認した。[ブラウザ記録](sphere-triangle-mesh-flight-sdk-browser)は表示証拠で数値証拠の代用ではない。

## 残件と失敗履歴

HEAPは前/最大観測/後すべて67108864B、buffer交換0、12915回view再取得を観測。allocator used bytesとstack高水位は現exportに計器がなく未計測、growthも実際には未発生。容量を使用量や最悪case余裕へ読み替えず、計器導入と実growth・allocation fault注入は残件とする。全入力組合せのメモリ上界や60fpsを主張しない。

synthetic初回run001は参照stats helper名の誤りで5PASS/1ERRORとなり、helper参照先のみ訂正して最終run004の6群/ソース前後一致が成功。原stdout/stderr・欠測注記は[attempt archive](sphere-triangle-mesh-flight-sdk-reference-attempts/freeze.json)へ保持した。Native/モデル入力/閾値を緩めていない。prebuilt baselineの最初の実行中に、未使用のsimulation_api.hだけが新API追記で変わった。元authoredStable:falseを保持し、コンパイルを伴わない既存実行ファイルでの比較と明示した。[baseline scope](sphere-triangle-mesh-flight-sdk-checks/run-20261104-before/baseline-scope.json)を参照。最終コンパイル/交換は凍結ソースで別に確認した。

[ローカル機械集計](sphere-triangle-mesh-flight-sdk-local-verification.json)・[再現recipe](sphere-triangle-mesh-flight-sdk-recipes/check.py)・[最終rawログ](sphere-triangle-mesh-flight-sdk-checks/run-20261104-final)。公開GNU・API sanitizer・配信は未確認。既存の純核sanitizer成功を新APIの計装実行と混同しない。

次は[所有JS API](../docs/SPHERE_TRIANGLE_MESH_FLIGHT_JS_PLAN.md)。raw6入口を全て検出してから書き込み、全fieldを一度captureし、全21kindを所有copy/監査する。手動UI・World advance/接触順序/衝撃摩擦支持・残時間/tick commit、流体損傷・専門モデル/IK制御/高精度撮像は引き続き未完。
'''
report+='\n初回の全交換/回帰成功後、未使用flight_same_vector定義1行を削除して最終002のNative build・200群・全交換/独立参照・41CTest/631Nodeを再実行した。正式SDKも再buildし、WASM/glueの全bytesが初回と同一であることを確認。compiled private-header hashを含むmanifestの変化によりWeb buildは055e57b764eb7731から26d4da108a67b9d9へ変わり、最終ビルドでも実ゲームを再確認した。初回の21照会/193kmhと最終22照会/158kmhは別観測として原ブラウザ記録を保持する。\n'
(root/f'reports/2026-11-04-{prefix}.md').write_text(report,encoding='utf-8',newline='\n')
print('Local raw flight SDK receipt recorded; public acceptance is pending.')
