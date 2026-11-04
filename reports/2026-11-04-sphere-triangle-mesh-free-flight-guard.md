# 丸め自由伝播と静的meshの非接触guard — Native受入

2026-11-04。元bodyを各binary64 durationで一度だけ進めた並進位置と、元F/m+gの厳密曲線の差を既存W1の上界Bで囲むNative-only照会を追加した。上向きr+Bで全域非接触を証明し、Hでの完全candidate（回転・角運動量を含む）をコピー上で検査する。元World/荷重/時計を進めない。コード `bd7c1f7` の公開CI/Pagesと配信を確認済み。

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

## 公開受入と次段

Engine [41796183673](https://github.com/tatata93/pikapikaengine/actions/runs/41796183673)（job126460730559）、Pages [41796182644](https://github.com/tatata93/pikapikaengine/actions/runs/41796182644)の全job/step成功。40CTest/631Node skip0に加え、GNUの変更前後W1全JSON比較、旧SDK保存20例のbit比較、新核114群/固定100＋補足4とFraction12self/50負例が成功した。新guardと依存する実dynamics/interval/mesh/held/Worldを別ASan/UBSan executableへ計装し、Release/sanitizedの両fixture JSON byte比較と独立参照が成功。新4翻訳単位のstrict/Werrorも成功した。Windows sanitizerやallocation fault注入の実施は意味しない。

警告は40件。前節の既存36件に、旧Worldを変更前probeおよび新guard sanitizerへ別途コンパイルした際の既存Query::result初期化診断4件が加わった。旧診断のCounterにこの4件を足したものと一致し、新しいguard翻訳単位の警告ではない。[公開機械監査](sphere-triangle-mesh-free-flight-guard-public-verification.json)と行番号付きjob excerptを保存した。excerptは全原ログのarchiveではない。

公開43ファイル計1779473Bが正確なfeature Git blobと一致。実公開ゲームはbuild bbeba69b26e28cdb/719396B WASMを使用し、2撃破・ブースト（clip1記録）・停止、51照会すべてchecked/validated/completed、3resident mesh/error0を確認した。停止時の速度表示は0で、観測していない速度を報告しない。図の上部と下端、ゲーム画面および表示JSONを[ブラウザ証拠](sphere-triangle-mesh-free-flight-guard-browser)へ保存した。新guardがゲームの接触処理へ適用された証拠とはしない。

次の最小受入は[両mode共有SDK計画](../docs/SPHERE_TRIANGLE_MESH_FLIGHT_SDK_PLAN.md)。現在の86exportsへ実装を追加する前に、元入力と膨張半径・全Work/partition・成功時candidate・host拒否とモデル結果の境界を固定し、Native/WASM全bitと独立参照を確認する。予定の6exports/92は未実装であり、現在の配布能力と区別する。

[ゲーム](https://tatata93.github.io/pikapikaengine/?v=bd7c1f7)・[原理解説](https://tatata93.github.io/pikapikaengine/docs/learn/index.html?v=bd7c1f7#accelerated)
