# Skinning共通SDKの実装範囲と次の受入

2026-11-03。共通SDKへの位置skinning接続と操作ラボを実装し、ローカルの実WASM検証を完了した。現在の生成物は63exports、WASM583708B、glue49388B。公開CI/Pagesの最終結果は根本の最新reportsで確定する。原本binding codecやNative CLI往復は未実装で、照会結果JSONの保存をその完成と扱わない。

## 有界な最初の照会

Native核の65536頂点/262144 influenceと、C ABIの49152 double入力を区別する。実装したSDKは一照会2048頂点・128bone・8192 influenceまでを明示上限とし、勝手なbatch分割や頂点の省略をしない。SettingsはNativeの最大128/65536/262144まで交換でき、さらに小さい予算はそのままC++へ渡す。大meshを扱う次段は、全入力検査と失敗時の全体保持を保った別のchunk契約として設計する。

追加4exportsは `pp_sim_skin_bind` / `pp_sim_skin_bind_record` / `pp_sim_skin_deform` / `pp_sim_skin_deform_record`。API版1/output64と既存のinput/output領域を保持し、motion/world/光学recordへ干渉しない。global resetは両skin recordも消す。正確なlayoutは `core/include/pikapika/simulation_api.h` を契約原本とする。

bind header8は `[restCount,maxBones,maxVertices,maxInfluences,maxCondition,maxInverseResidual,0,0]`、rest17はIDとmat4。全原本を送ってC++ `skinning::bind` を呼ぶ。joint getter(kind0)はID/rest16/inverse16（33値）、diagnostic getter(kind1)はID/condition有無・値/residual有無・値/pivot flag（6値）。failureのdiagnostic prefixとcompleted jointsを分け、未完成jointsを公開しない。

deform headerは12値（joint/pose/vertex/influence数、Settings5値、予約0を3値）。joint33値×128、pose17値×128、vertexのposition3とinfluence数の4値×2048、influenceのID/weight2値×8192で最大30988 double。49152内に収まる。jointとposeは別々のID列を送って、callerの重複や欠損をJSのMap化で隠さない。

summary8は `[status,hasResult,itemCount,diagnosticCount,weightResidualCount,0,0,0]`。deform getterはkind0 position3、kind1 diagnostic6、kind2 weight残差1。返値は全copy snapshotで、NaN sentinelを使わずoptional flagsを保持する。不正count/ID/整数Settings/非有限値/予約値/getterは以前のrecordとoutputを保持する。受理した有限モデルの失敗は新しいno-result recordとなり、古い位置を返さない。

## JSと実操作ラボ

`SimulationRuntime.bindSkin(rest,settings)` と `deformSkin({joints,pose,vertices},settings)` は原本を転送し、C++結果をコピーする。JSにはinverse/LBS/FKの代替計算を置かない。返値は `{status,joints,positions,diagnostics,weightResiduals}`。bindのjoints、deformのpositionsはcompleted時のみ配列、それ以外はnull。diagnosticのcondition/residualは有無をnullで保存する。設定名は `maximumBones` / `maximumVertices` / `maximumInfluences` / `maximumCondition` / `maximumInverseResidual`。

操作入口は [`tools/skinning-lab.html`](../tools/skinning-lab.html)。2骨・6頂点の帯、非一様scaleと回転、巨大translation相殺、正weightのunderflowを照会できる。XY/XZの原本/変形位置と入力・inverse bind・診断を表示する。時刻とauthor weightを変更すると古い結果を消し、明示した計算操作で更新する。確認用の入力/結果JSON出力であり、bindingアセットの保存読込形式ではない。本文/SVGはfile://で読めるが実ESM/WASM操作はHTTP/HTTPSを必要とする。

## 完了したローカル検証

- Native全体651群/CTest28、Node全体322/322・skip0が成功。SDK新規Node11試験と、既存motion/optics/World等を含む関連36試験も成功。公開CI/Pagesはローカル全回帰と分け、根本の最終照合で確定する。
- 65 Native fixtureは60件の実C++モデル結果と5件の明示的なhost交換拒否へ分類。後者はzero/unsafe IDと整数Settings予算3件で、C++モデル成功と数えない。128 oracleの実bind/deformと失敗後retryを含む5288出力数値のbinary64 bitsが一致した。
- 既存の独立Fraction checkerを変更せず再利用し、fixture304点＋oracle4480点/実行の点精度比較とbit比較を別々に確認した。signed zeroを保つJSON、全binary64 hex、完全入力/結果を保存した。
- actual128bone/2048vertex/8192influenceの同時上限と1超過、Native設定域、巨大weight/2段階underflow、shear、imported inverse、相殺回帰、欠損/重複、raw exchange/getter破損、copied snapshot、両record/World clock保持、reset/復帰を確認した。

再生は `scripts/verify-skinning-wasm.mjs`。ignored `build/skinning-sdk-js/` にreport/outputs/replay JSONとCSV、provenance、再現commandsを保持する。一般入力の誤差包含、Float32変換、GPU skinning、法線/接触/材料損傷の完成とはしない。

## 次の最小受入

その次にstable scene ID/mesh fingerprint/bone IDを持つbinding原本とNativeCLI/JSON/portable往復を追加し、小さな自作メッシュで法線/三角形/Float32検査と描画へつなぐ。現在のmesh v1は頂点配列indexであり、topology変更時のID維持を暗黙に保証しない。
