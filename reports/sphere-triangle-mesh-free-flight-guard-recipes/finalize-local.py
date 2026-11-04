"""Record measured local guard acceptance; never infer pending public results."""
from pathlib import Path
import json,re
root=Path(__file__).resolve().parents[2];prefix='sphere-triangle-mesh-free-flight-guard'
proof=json.loads((root/f'reports/{prefix}-local-verification.json').read_text(encoding='utf-8'))
assert proof['status']=='PASS' and (proof['nativeGroups'],proof['fixtures'],proof['supplementalFixtures'],proof['node'],proof['ctest'])==(114,100,4,631,40)
resume='丸め自由伝播guardをNativeローカル受入。既存W1のBをprivate bridgeで再使用し、上向きr+Bの全域separatedとHでの完全candidateをread-onlyで監査。実dynamics.cppもstrict/contractionoffへ統一。専用114群/40CTest/631Node skip0、固定100=18認証44未認証38不正＋別固定4=binade3認証/膨張entry1未認証、12self/50負例/両cohort label-order独立が成功。旧20W1全report/World53907Bが前後byte一致、旧SDK保存20例4520数値bits24負零一致。旧entry62model3host全105056bits3239負零と原入力4728bits108負零/90負例、旧held79全JSON/63負例もfresh成功。324保護原本/25HTML正規化保持。SDK86exports/62source-header/30TUs、WASM719396B/glue58933B/runtime91/7通知、Webbbeba69b26e28cdb/51modules25entries。実ローカルゲーム2撃破/boostclip1/停止・22全照会完了3常駐/error0。公開Linux/ASan-UBSan/GNU前後bit/Pages/配信は未確認。[実装ガイド](SPHERE_TRIANGLE_MESH_FREE_FLIGHT_GUARD.md)・[検証記録](../reports/2026-11-04-sphere-triangle-mesh-free-flight-guard.md)。World進行/全pair順序/衝撃摩擦支持/流体損傷/専門モデル/IK制御/高精度撮像は未完。'
p=root/'docs/PLAN.md';text=p.read_text(encoding='utf-8');text,n=re.subn(r'^再開位置:.*$','再開位置: '+resume,text,count=1,flags=re.M);assert n==1;p.write_text(text.rstrip()+'\n\n追記: '+resume+'\n',encoding='utf-8',newline='\n')
p=root/'docs/SPHERE_TRIANGLE_MESH_FREE_FLIGHT_GUARD_PLAN.md';text=p.read_text(encoding='utf-8');old='状態: **未実装のNative次段計画**。';assert old in text;text=text.replace(old,'状態: **Nativeローカル受入済み・公開検証待ち**。[実装ガイド](SPHERE_TRIANGLE_MESH_FREE_FLIGHT_GUARD.md)・[実行記録](../reports/2026-11-04-sphere-triangle-mesh-free-flight-guard.md)を参照。以下は元の受入設計と境界。',1);p.write_text(text,encoding='utf-8',newline='\n')
p=root/'docs/RESEARCH.md';p.write_text(p.read_text(encoding='utf-8').rstrip()+'\n\n自由伝播guardローカル受入: Native114群/固定100と別固定4、Fraction12self/50負例、40CTest631Node skip0成功。元100に試験都合の変更をせず、中心binade3とcoarseTol.1での膨張entry反例を補足として分離。実dynamics.cppもstrict/no-contractionへ統一し、旧20Native全report/state byteと既存SDK保存20例4520数値/24負零が前後一致。再build WASM719396Bへ変化、86exports/62source-header/runtime91/7通知を正式provenanceで確認。新外部文献実読/依存追加を主張せず、公開GNU/メモリ検査は別判定とする。\n',encoding='utf-8',newline='\n')
report='''# 丸め自由伝播と静的meshの非接触guard — Native受入

2026-11-04。元bodyを各binary64 durationで一度だけ進めた並進位置と、元F/m+gの厳密曲線の差を既存W1の上界Bで囲むNative-only照会を追加した。上向きr+Bで全域非接触を証明し、Hでの完全candidate（回転・角運動量を含む）をコピー上で検査する。元World/荷重/時計を進めない。公開CI/Pagesは確認待ち。

## 実行した範囲

専用114群、40CTest、631Node（skip0）、syntax/Web buildが成功。元100完全入力は18認証・44未認証・38入力拒否。別固定4は実body中心が2^39直前/同値/直後の3安全例と、明示coarse timeTolerance=.1の膨張球entryをouter未認証へ保つ1例。後者の元球の全経路最小gapは厳密に2^-20>0で、既定tol1e−7の元例が窓未成立であることも保持した。元100の全input/結果JSON3186419Bは初回と最終でbyte一致。

独立Fractionの12self/50負例（-O拒否含む）と両cohortのラベル/順序非依存が成功。整数商とbit組立でRN/ties-evenを再現し、元F/mと丸めた加速度、全durationのULP recurrence、上向き半径、Hのendpoint、全nested保持荷重証拠を監査した。主100は57tube/54endpoint/54inflated、171nominalA bits/162候補位置bits/108公開velocity+L bits、nested2080audit/862leaf/2556lastMesh成分。固定100 fingerprintは `c14d0e37cd5fe3d85d30ec0a408d46608ecefabb8b55513e31e51dbfe6ed2d37`、別4は `a23779088fc9d7ce9bf388456b055795ccf3c5ea85fdab3b11df50ea7a604d80`。

FMA/再結合で別値になる域内反例も含む。実propagate_free側のdynamics.cppがNative既定precise/GNU既定contraction許容に依存しないよう、Native strict/no-fast/contractionoff/frounding、SDK no-fast/contractionoffへ統一した。旧数式/演算順は無変更。有限endpointの観測だけを全durationの根拠にしない。

## 既存W1とSDKの保全

continuous_world.cppはprivate header includeと末尾bridgeだけを追加し、それらを除く全byteが変更前sourceと一致。`flight()`やWorld本文の数式を複製/変更していない。旧20Nativeの全input/settings/CcdReport/Worldbeforeafter53907Bが厳密flags変更後もbyte一致し、14success/6failure/5複数eventと全pointer/rollbackを確認した。

旧SDKの保存20例は14success/5model拒否/1host拒否、全保存field4520数値bits/24負零が変更前と一致。元input/SDK profile/body/report/clockをすべて含む。Native既定16384contactsとSDK8192capは別profileとして明記し、duration0のhost拒否をモデル結果へ混ぜない。

固定Emscripten6.0.13で正式再buildし、86exports/62source-header/30TU。最終WASM719396B SHA5542502ee73b62c0ca8de9f3d1fc01139bfacfd4ff83922b5568f4a0acfd03c3、glue58933Bは元と同byte。runtime91/7license通知は原本のまま。旧719410B→bridge追加だけの中間719356B→実伝播strictの最終719396Bを区別し、中間はbuild stdout/hash観測であって全artifact byte archiveとは呼ばない。新Native guardをSDKへexportした変更ではない。

324旧原本を全byte保全し、25生成HTMLはimportmap/build query/CRLFだけを正規化して原本保持を検査した。Web bbeba69b26e28cdb/51modules25entries。fresh旧entry所有62model+3hostは全105056モデル数値/3239負零・原入力4728数値/108負零/90負例に一致。旧held79は全JSONbyte一致と独立16self/63負例も再実行し成功。旧W1既存corridorのNative/WASM比較も成功した。より以前の専門核は保護原本・今回の全631Node/40CTestと公開済み検証を組み合わせて継承する。

実ローカルゲームは再生成SDKで出撃・射撃2撃破・boostclip1・一時停止を確認。22照会は全checked/validated/completed、3resident mesh/error0。これは新guardのゲーム接触適用とは別の既存SDK回帰。原著図を全体表示して文字/配置を目視した。画像は表示証拠で、数値証拠の代用ではない。

## 記録と失敗履歴

[ローカル機械集計](sphere-triangle-mesh-free-flight-guard-local-verification.json)が全command/exit/source前後hash/原stdout-stderr/fixture/SDK provenanceを監査。[最終ログ](sphere-triangle-mesh-free-flight-guard-checks/run-20261104-final)、[改修前](sphere-triangle-mesh-free-flight-guard-checks/run-20261104-before)、[再現recipe](sphere-triangle-mesh-free-flight-guard-recipes/check.py)、[ブラウザ証拠](sphere-triangle-mesh-free-flight-guard-browser)を参照。

初回Native112群/100入力は成功し、その後元100を変えずbinade/膨張windowの2群・補足4を追加して最終114群となった。参照の準備段階では旧fingerprint encoderが新boolに未対応（run003）、bytes.hex変換漏れ（run004）、静止例のexactDifference=0置換が有効な包含だったため誤った拒否要求（run006）で停止した。指紋処理と負例の対象だけを訂正し、Native/物理入力/閾値を緩めていない。run003の準備stderrは別raw未捕捉と明記し、全試行metadata/原ログと欠落注記を[archive](sphere-triangle-mesh-free-flight-guard-reference-attempts/freeze.json)へ保持した。最終root検証は全ソース凍結後に別実行。

## 境界

全durationの証明は同じ初期状態から一度進める並進分岐。Hの完全6DOF候補を別に確認し、姿勢/速度の連続真解精度、全内部durationでの完全6DOF成功、繰返しsubstepや累積clock誤差は証明していない。実allocation/内部例外のfault注入も対象外。

他のWorld body/planeとの順序、同時接触/manifold、反発/摩擦/支持、衝撃後の再照会/残時間、tick全体のatomic commitと一回の荷重消費は後続。candidateや膨張windowをpoint impulseへ落とさない。SDK/JSへの照会公開、流体・損傷・車両/航空/鉄道・IK/制御・高精度撮像も引き続き未完。新外部依存/転載素材/有料serviceなし、本体license未選定。
'''
(root/'reports/2026-11-04-sphere-triangle-mesh-free-flight-guard.md').write_text(report,encoding='utf-8',newline='\n')
print('Local guard receipt written; public acceptance remains pending.')
