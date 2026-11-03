# 派生meshのNode段階計測

2026-11-04 JST。ローカル受入済み、公開確認は[検証記録](../reports/2026-11-04-derived-profile.md)に記載する。[性能調査の計画](DERIVED_MESH_PERFORMANCE_PLAN.md)を小単位に進める最初のツール。C++/WASMのアルゴリズムや精度条件は変更せず、Node上のSDK呼出しと描画用データ生成を観測する。実GPU、Native、実時間animationの性能受入は別である。

## 計測する境界

`tools/derived-profile.mjs`の`createDerivedMeshProfiler(runtime,{now})`は、渡されたruntimeと同じC++ moduleへ、別の`SimulationRuntime`とforwarding proxyから照会する。元のruntime/method/exportを書き換えない。`prepare(input,settings)`は`{result,error,timing,clockError}`を返す。

| 値 | 観測範囲 |
|---|---|
| elapsedMs | instrumented prepareの呼出し全体 |
| f64Exchange | inputF64: 交換値の検査・copy・HEAP転送 |
| u32Exchange | inputU32: index検査・copy・HEAP転送 |
| cppQuery | C ABI呼出し全体。C++交換検査・prepare・snapshot commitを含む |
| cppGetter | record getterのC ABI呼出し。packetを出力領域へcopyする費用を含む |
| outputCopy | JS output(): 出力領域からArrayをcopyする費用 |
| unassignedMs | 上記以外。入力構築、DTO decode/validation、wrapper/時計等の観測費用を含む未分類残差 |

getterKindsは位置/triangle/interleaved/auditの4種類の呼出し件数。全体completedならN/T/T/T、outputCopyは1+N+3Tとなる。失敗時はgeometry getterを実行せず、診断audit prefixの件数と区別する。

各段階は同じinstrumented呼出しの互いに重ならない区間だが、wrapperと時計の読出し自体が実行時間を変える。別にuninstrumented baselineを測り、両方の全試行を残す。両者の差を「純粋なJS時間」「時計の補正値」と解釈しない。cppQueryも純粋kernelだけの時間ではない。小入力や少数試行の順位を一般化しない。

## 失敗と所有

正常なモデル失敗はresultにそのまま残り、原APIの例外はerrorに保持する。時計のthrow・非finite・後退などが起きてもモデル処理を継続し、timingをnullにする。clockErrorを別に返すので、元の例外と時計の問題を混同しない。時計が無効な試行を高速な成功やhost拒否へ分類しない。

計測対象のC++ moduleは元runtimeと共有するため、派生snapshotは通常のqueryと同様に更新される。以前の所有DTOは保持される。専用runtimeでの測定を推奨し、共有moduleの同時操作や再入可能な計測を前提にしない。時計は副作用を持たず、同じmoduleの別runtimeや別profilerを呼ばないこと。同一profilerへの再入は拒否するが、共有moduleをlockする仕組みではない。元のWorld clockや他kernelの独立snapshotを、この派生照会が変更するものではない。

## CLI

```powershell
node scripts/profile-derived-mesh.mjs --output build/derived-profile-local --quick
node scripts/profile-derived-mesh.mjs --output build/derived-profile-full --repeats 3 --warmup 1
```

出力はrepoのbuild直下derived-profile*に限定し、各呼出しで新しいrunディレクトリを作る。既存の証拠を上書きしない。symlink・未知/重複引数や範囲外設定を拒否し、全260query・10MiBの上限を設ける。標準は10case×(初回1+warmup1+計測3)×baseline/instrumentedの100query、quickは8case。最初のcase呼出し・warmup・計測を全て記録する。「最初」はこの順次実行のcase内の最初であり、OS cacheやCPU/V8がcoldという意味ではない。

小さい実Source/FK/LBSの帯、非軸の既知法線、shearを含むgridを扱う。期待する退化・品質未確定・品質不足と、SDK容量を超えるhost例外を、正常時間の集計へ混ぜない。正常への復帰も別に確認する。

baselineとinstrumentedの全DTOを型/signed zero/Float32/区間端点も含めて比較し、全出力bitsのhashを各試行で保持する。全入力と原本を保存し、不変を照合する。大容量の出力は全件を検査・hashした上で先頭/末尾のpreviewだけ保存する。previewを描画可能な部分bufferや全出力の保存と読み替えない。原本FK/LBS、tokenの構造検査と所有copyは別の時間で、NodeからGPU uploadを測ったとはしない。

中央値、nearest-rank p95、最大値は観測した有限sampleの要約で、母集団の保証やfpsではない。Node/OS/CPU・SDK/関連source hash・実command・全raw timing・期待失敗・再現用入力を対応付ける。公開CIの速さを利用者の環境の速さへ換算しない。

外部profiler/package/SDKは追加しない。標準Nodeのperf_hooks/crypto/OS/file APIと既存の原著SDKを使う。全runtime配布通知と本体license未選定を維持する。最終試験数と実計測・公開結果は検証記録で確定する。
