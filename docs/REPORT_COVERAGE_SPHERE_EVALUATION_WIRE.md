# 球間距離のEvaluationを保存する

2026-11-06。`accelerated_sphere_box_coverage::Evaluation`全9項目のconst取得をNative有限受入。取得範囲は79record型456項目＋別variant1型、coverage内24record110項目／残り5record32項目。Native実結果は`reports/diagnostic-wire-coverage-sphere-evaluation-verification.json`を参照。GNU・公開は別受入であり、Native成功から推定しない。

| 元の項目 | 取得する内容 |
| --- | --- |
| first_coordinates、second_coordinates、delta | それぞれ3軸すべてのIntervalと元の順序 |
| raw_squared_distance、nonnegative_squared_distance | 元の二つの区間を個別に保存 |
| root | value、refinements、refinement_limitedを全保存 |
| distance、threshold、gap | 保存済みの元の各区間 |

取得時に距離や平方根を再計算しない。raw二乗距離をclampしたり、distanceをroot.valueへ置き換えたりしない。人工データはroot.valueとdistanceを8件すべてで異ならせ、4種類のUInt32計数と両方のboolを全8組合せで比較する。これは実モデルが不整合値を生成・受理したことの認証ではない。

Intervalは既存のpublic constructorで正当に構築する。NaN／反転区間はそのconstructorが拒否し、零は下端-0／上端+0へ正規化する。private領域の改変やNaN区間の偽造は行わない。元のraw Inputに保存可能なNaN payloadと、構築済みIntervalの保存契約を区別する。

初回単体では人工8Evaluation、全7,943byte SHA256 `27c788911afda064a0533dc13e365f4608bb06f91c8072f8f49cb284c054694d`、256typed leaf（F64 240／負零20、U32 8、bool8）、120Intervalと24個の3軸配列がRelease／Debugで一致した。1,252callback境界、停止／例外2,504件、再入拒否2,504件、4丸めmodeも新対象の単体で確認した。

変更検査は全scalar／key byte4,328件（typed payload1,960byte）、root順序・個数3件、field値交換412件、object順序136件、固定軸配列の順序・個数120件、合計4,999件を検出。同値となるfield交換20件は拒否件数へ含めず、同値軸交換は0件である。

製品2data TU＋harness1＋Intervalの試験用1TUで構築する。数値model libraryを製品へ加えない。GNUの通常・真Debug・全4TU O1 ASan／UBSanは別受入である。初回単体は`reports/diagnostic-wire-recipes/run-20261106-coverage-sphere-evaluation-early-001/verification.json`、変更検査は同`coverage-sphere-evaluation-controls-001/`、全Nativeはfresh `build/wfdcse2`と`coverage-sphere-evaluation-native-001/`で別に実行する。

最上位World Report、C API pump、今回取得のWASM／ゲーム接続は後続。[次はCell3項目とWork7項目](REPORT_COVERAGE_SPHERE_CELL_WORK_WIRE_PLAN.md)。
